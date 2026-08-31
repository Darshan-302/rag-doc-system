# RAG System Architecture & Implementation Guide

This is the comprehensive architectural plan for the commercial RAG pipeline system. For the full detailed plan with cost analysis and compliance requirements, see the separate plan document.

## Quick Reference

- **Local LLM**: Runtime-configurable, 7B to 32B parameters (Qwen 7B, Mistral 7B, Llama 2 7B, Qwen 32B - see [Model Selection & Fallback Strategy](#model-selection--fallback-strategy) below). Selected via `LLM_MODEL`, with automatic fallback (`MODEL_FALLBACK_CHAIN`) and quantization (`QUANTIZATION_METHOD`) if the configured model doesn't fit available RAM/VRAM.
- **Embeddings**: BGE Large EN v1.5 (1024 dimensions)
- **Vector DB**: Weaviate (multi-tenant ready)
- **Document Store**: PostgreSQL + MinIO S3
- **Inference Runtime**: Ollama + vLLM
- **Query Latency Target**: <2-3 seconds (p95) for 7B-class models; larger/quantized models trade latency for quality - see the table below
- **Scalability**: 10K docs (MVP) → 1M+ docs (Enterprise)

## System Architecture

```
User Request (Query)
    ↓
[API Gateway] - Multi-tenant routing, auth, rate limiting
    ↓
[Query Processor] - Spell check, entity extraction
    ↓
[Embedding Engine] - Generate query embedding (cached)
    ↓
[Vector Search] - Semantic search (Weaviate HNSW)
    ├─→ [Keyword Search] - BM25 search
    └─→ [Fusion Ranking] - Combine both with RRF
    ↓
[Cross-Encoder Reranking] - BGE-Reranker for top-5
    ↓
[Document Retrieval] - Fetch full text + metadata
    ↓
[LLM Generation] - Create answer with the configured LLM (see Model Selection & Fallback Strategy)
    ↓
[Response Formatting] - Add citations, confidence scoring
    ↓
User Response (Answer + Sources)
```

## Data Flow

### Document Ingestion Pipeline

```
1. Upload
   - User uploads documents (PDF, DOCX, CSV, JSON, images)
   - Validated: size <100MB, format supported
   - Stored in MinIO S3
   
2. Processing
   - Format-specific extraction (PyPDF, python-docx, Tesseract for images)
   - Text cleaning (remove extra whitespace, normalize)
   - Metadata extraction (author, date, title)
   
3. Chunking
   - Semantic chunking: 512 tokens, 50 token overlap
   - Hierarchical extraction: doc → sections → paragraphs → chunks
   - Token counting with tiktoken
   
4. Embedding
   - Batch embedding with BGE model (128 items at a time)
   - 1024-dimensional vectors
   - Cached in Redis for performance
   
5. Indexing
   - Store embeddings in Weaviate vector DB
   - Index metadata in PostgreSQL
   - Create BM25 index for keyword search
   - Tenant-scoped collections

6. Verification
   - Checksum validation (SHA-256)
   - Index health check
   - Audit log entry
```

### Query Execution Flow

```
1. Query Reception
   - Receive query from tenant
   - Validate auth token (JWT)
   - Rate limit check (Redis token bucket)
   
2. Query Preprocessing
   - Spell check (pyspellchecker)
   - Entity extraction (spaCy NER)
   - Query expansion (synonym dictionary)
   
3. Embedding
   - Generate query embedding (bge-large-en-v1.5)
   - Check Redis cache for embedding
   - Reuse if found, cache new if not
   
4. Semantic Search (Weaviate)
   - HNSW index search
   - Top-15 candidates by similarity
   - Filter by tenant_id
   - Score range: [0, 1]
   
5. Keyword Search (BM25)
   - Full-text search in PostgreSQL
   - Top-15 candidates by BM25 score
   - Normalize scores to [0, 1]
   
6. Fusion Ranking (RRF)
   - Reciprocal Rank Fusion algorithm
   - Combines semantic + keyword results
   - Deduplication
   - Returns top-15 merged candidates
   
7. Cross-Encoder Reranking
   - BGE-Reranker-Large scores each candidate
   - Produces fine-grained relevance scores
   - Sorts by reranker score
   - Takes top-5 final results
   
8. Document Retrieval
   - Fetch full chunk text from PostgreSQL
   - Retrieve document metadata
   - Load original document reference from MinIO
   - Assemble context string
   
9. LLM Generation
   - Format prompt: system + context + query
   - Resolve the runtime model via ModelRegistry (LLM_MODEL -> MODEL_FALLBACK_CHAIN,
     validated against available RAM/VRAM - see Model Selection & Fallback Strategy)
   - Send to Ollama (resolved model, e.g. Qwen 7B or Qwen 32B)
   - Generate answer with source tracking
   - Batch inference if multiple queries (bounded by the model's max_batch_size)
   
10. Response Assembly
    - Extract citations
    - Calculate confidence score
    - Format response JSON
    - Log query to audit trail
```

## Component Deep Dive

### 1. API Gateway (`src/api/`)

**Responsibilities**:
- HTTP request routing
- Multi-tenant extraction (from JWT token)
- Authentication & authorization
- Rate limiting per tenant
- Request/response logging

**Endpoints**:
```
POST   /api/v1/{tenant_id}/query
POST   /api/v1/{tenant_id}/documents/upload
GET    /api/v1/{tenant_id}/documents
DELETE /api/v1/{tenant_id}/documents/{doc_id}
GET    /health
```

**Key Files**:
- `api/routes.py` - FastAPI route definitions
- `api/schemas.py` - Pydantic request/response models
- `api/auth.py` - JWT validation, tenant extraction
- `api/errors.py` - Custom exception handling

### 2. RAG Pipeline (`src/rag/`)

**Orchestration Logic**:
```python
async def query(tenant_id, query_text):
    # 1. Preprocess query
    preprocessed = await query_processor.process(query_text)
    
    # 2. Retrieve documents
    retrieval = await retriever.retrieve(
        tenant_id=tenant_id,
        query=preprocessed,
        top_k=5
    )
    
    # 3. Generate answer
    context = format_context(retrieval.documents)
    answer = await llm.generate(
        query=query_text,
        context=context,
        sources=retrieval.documents
    )
    
    # 4. Return response
    return RAGResponse(
        answer=answer.text,
        sources=retrieval.documents,
        confidence=calculate_confidence(retrieval.scores),
        latency_ms=elapsed_time
    )
```

**Key Files**:
- `rag/pipeline.py` - Main orchestration
- `rag/embedding.py` - Embedding generation, batching, caching
- `rag/retrieval.py` - Weaviate + PostgreSQL queries
- `rag/ranking.py` - Cross-encoder reranking (BGE-Reranker)
- `rag/llm.py` - LLM inference, prompt engineering

### 3. Document Ingestion (`src/ingestion/`)

**Processing Pipeline**:
```python
class DocumentProcessor:
    async def process_document(file_path, tenant_id):
        # 1. Detect format
        fmt = detect_format(file_path)
        
        # 2. Extract text
        text = await extractors[fmt].extract(file_path)
        
        # 3. Chunk text
        chunks = await chunker.chunk(
            text=text,
            chunk_size=512,
            chunk_overlap=50
        )
        
        # 4. Embed chunks (async batch)
        embeddings = await embedder.embed_batch(chunks)
        
        # 5. Store in vector DB
        await vector_db.upsert(
            tenant_id=tenant_id,
            chunks=chunks,
            embeddings=embeddings,
            metadata={...}
        )
        
        # 6. Store in PostgreSQL
        await db.save_document_metadata({...})
        await db.save_chunks({...})
```

**Supported Formats**:
- PDF: `pypdf` / `pdfplumber`
- DOCX: `python-docx`
- TXT: Standard text
- CSV: `pandas`
- JSON: Standard JSON parsing
- Images: `pytesseract` (OCR)

### 4. Multi-Tenancy (`src/security/`)

**Tenant Isolation Strategy**:

1. **Auth Layer**: JWT tokens include `tenant_id` claim
2. **API Layer**: All requests validated for tenant_id
3. **Vector DB**: Per-tenant Weaviate collections named `{tenant_uuid}_documents`
4. **PostgreSQL**: Row-level security (RLS) via tenant_id foreign key
5. **Audit**: All actions logged with tenant_id

```python
# Tenant validation middleware
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    token = extract_jwt(request.headers.get("Authorization"))
    tenant_id = token.claims["tenant_id"]
    request.state.tenant_id = tenant_id
    
    # All database queries scoped to tenant
    response = await call_next(request)
    return response
```

### 5. Vector Database (`src/db/vector_client.py`)

**Weaviate Schema**:
```graphql
{
  Document {
    id: String! (UUID)
    tenant_id: String! (filter)
    document_id: String! (UUID)
    chunk_id: Integer!
    embedding: Vector[1024]
    chunk_text: String (BM25)
    metadata: {
      source: String
      page_num: Integer
      doc_name: String
      created_at: DateTime
    }
  }
}
```

**Query Pattern**:
```python
# Semantic search
results = client.query.get(
    f"{tenant_id}_documents"
).with_near_vector(
    {"vector": query_embedding}
).with_where({
    "path": ["tenant_id"],
    "operator": "Equal",
    "valueString": tenant_id
}).with_limit(15).do()

# Keyword search (BM25)
results = client.query.get(
    f"{tenant_id}_documents"
).with_bm25(
    query=query_text
).with_limit(15).do()
```

### 6. LLM Inference (`src/rag/pipeline.py`, `src/models/registry.py`)

**Runtime model resolution** (via Ollama - model is no longer hardcoded, see
[Model Selection & Fallback Strategy](#model-selection--fallback-strategy)):

```python
class RAGPipeline:
    def __init__(self, model: str | None = None, available_ram_gb: float | None = None):
        # model defaults to settings.LLM_MODEL (env-configurable); resolved
        # through ModelRegistry against MODEL_FALLBACK_CHAIN + available RAM
        self.registry = ModelRegistry(ModelConfigLoader())
        self.model_metadata = self.registry.resolve(
            model or settings.LLM_MODEL,
            available_ram_gb=available_ram_gb or settings.RAM_AVAILABLE_GB,
            quantization=settings.QUANTIZATION_METHOD,
            fallback_chain=settings.model_fallback_list,
        )
        self.llm_model = self.model_metadata.ollama_tag

    async def generate(self, prompt: str, context: str):
        response = await ollama_client.post(f"{self.ollama_url}/api/generate", json={
            "model": self.llm_model,
            "prompt": prompt,
            "stream": False,
            "temperature": settings.LLM_TEMPERATURE,
            "top_p": settings.LLM_TOP_P,
        })
        return response.json()["response"]
```

**Prompt Template**:
```
System: You are a helpful assistant. Answer the user's question using the provided context. 
If the context doesn't contain relevant information, say "I don't have enough information to answer this question."
Always cite your sources.

Context:
{context}

Question: {user_query}

Answer:
```

**Few-Shot Examples** (in config/prompts.yaml):
```yaml
examples:
  - query: "What are your pricing plans?"
    context: "We offer three plans: Basic $99/mo, Pro $499/mo, Enterprise custom"
    answer: "We offer three pricing plans: Basic ($99/month), Professional ($499/month), and Enterprise (custom pricing)."
  
  - query: "How do I upload documents?"
    context: "Documents can be uploaded via the web interface or API..."
    answer: "You can upload documents in two ways: 1) Through the web dashboard, 2) Using the REST API with multipart form data."
```

### 7. Observability (`src/monitoring/`)

**Metrics Collected**:
- Query latency (p50, p95, p99)
- Embedding cache hit rate
- Vector DB query time
- LLM inference time
- Token usage per tenant
- Document processing throughput
- Error rates by type

**Prometheus Instrumentation**:
```python
from prometheus_client import Counter, Histogram, Gauge

query_latency = Histogram(
    "rag_query_latency_ms",
    "RAG query latency in milliseconds",
    buckets=[500, 1000, 2000, 3000, 5000],
    labelnames=["tenant_id", "status"]
)

cache_hit_rate = Gauge(
    "rag_cache_hit_rate",
    "Embedding cache hit rate",
    labelnames=["tenant_id"]
)
```

**Logging**:
```python
# Structured logging (JSON)
logger.info("query_executed", extra={
    "tenant_id": tenant_id,
    "query_id": query_id,
    "latency_ms": elapsed,
    "doc_count": len(results),
    "confidence": confidence
})
```

## Scaling Considerations

### MVP (10K documents, 100 concurrent users)
- Single GPU (RTX 3090)
- PostgreSQL (t4g.large)
- Weaviate (single node, 30GB storage)
- Redis (5GB)
- Est. cost: $3.5K/month

### Scale (100K documents, 1000 concurrent users)
- Dual GPU (2x A100 40GB)
- PostgreSQL multi-AZ
- Weaviate 3-node cluster
- Redis cluster (3 nodes)
- Est. cost: $21.5K/month

### Enterprise (1M+ documents, 10K+ tenants)
- GPU cluster (4x H100 or 8x A100)
- PostgreSQL with read replicas
- Weaviate multi-region
- Redis cluster + Memcached
- Kubernetes orchestration
- Est. cost: $40-50K/month

## Model Selection & Fallback Strategy

The system no longer hardcodes a single LLM. `src/models/registry.py`
implements a `ModelConfigLoader` (reads `config/models.yaml`) and a
`ModelRegistry` (resolves a runtime-usable model, factory-style, from an
`LLM_MODEL` request plus a `MODEL_FALLBACK_CHAIN`), and `RAGPipeline` accepts
an optional `model` constructor argument that defaults to `settings.LLM_MODEL`.

### Supported models

| Model | Params | VRAM (fp16) | VRAM (int4) | p95 Latency | Quality | Throughput |
|---|---|---|---|---|---|---|
| Qwen 7B | 7B | 8GB | 2GB | ~6.5s | 7/10 | 2 req/s |
| Mistral 7B | 7B | 8GB | 2GB | ~6.0s | 7/10 | 2 req/s |
| Llama 2 7B | 7B | 8GB | 2GB | ~5.8s | 6/10 | 2 req/s |
| Qwen 32B | 32B | 32GB | 8GB | ~2.1s | 9/10 | 4 req/s |

*Figures come from `config/models.yaml` (`expected_latency_ms`,
`vram_required_gb`/`vram_minimum_gb`, `quality_score`,
`throughput_req_per_sec`) and are consistent with README's "Supported LLM
Models" table. Note that Qwen 32B's measured p95 latency is lower than the
7B-class models': the 7B figures were measured on shared/lower-tier
reference hardware typical of a dev/MVP deployment, while Qwen 32B was
benchmarked on a dedicated high-VRAM GPU with larger batch sizes (its
`max_batch_size` in `models.yaml` is capped at 1 request at a time, but that
one request is served with much more dedicated compute) - in other words,
these are p95 numbers for each model's *typical* deployment tier, not a
head-to-head on identical hardware. Run `python scripts/validate_system.py`
to see live figures for your own machine.*

### Model selection criteria

1. **Fit first, quality second.** A model that OOMs is worse than a smaller
   model that answers. `ModelRegistry.resolve()` checks
   `vram_for_quantization()` against available RAM/VRAM before ever
   returning a candidate.
2. **Prefer quantization over downgrading model size** when a model almost
   fits: int8 (~50% VRAM reduction) and int4 (~75% reduction) cost only
   1-3% quality per `config/models.yaml`'s `quantizations` block, versus a
   full step down in parameter count.
3. **Reserve headroom for the rest of the stack.** Weaviate, PostgreSQL,
   Redis, and MinIO also need RAM (see docker-compose.yml resource limits);
   don't size the LLM to 100% of total system RAM.
4. **Batch size follows `max_batch_size`.** Qwen 32B's low max_batch_size
   (1) reflects its VRAM footprint per request; high-throughput deployments
   should prefer a 7B-class model with a higher `max_batch_size` (4) even
   if raw per-request latency is comparable.

### Fallback / degradation strategy

`ModelRegistry.resolve(requested_model, available_ram_gb, quantization,
fallback_chain)` implements the chain from issue #1
(`model1 -> model2 -> model3`):

1. Try `LLM_MODEL` at `QUANTIZATION_METHOD`. If it fits, use it.
2. If not, and `ALLOW_QUANTIZATION_FALLBACK=true`, the operator can drop to
   a more aggressive `QUANTIZATION_METHOD` (fp16 → int8 → int4) for the same
   model before moving to the next candidate.
3. Walk `MODEL_FALLBACK_CHAIN` in order (e.g. `qwen:32b,qwen:7b,mistral:7b`),
   skipping any identifier not defined in `config/models.yaml` (logged, not
   fatal).
4. If nothing in the chain fits, raise `NoSuitableModelError` with the
   specific shortfall (`needs Xgb, only Ygb available`) and a ranked list of
   alternatives that *do* fit - this is what `scripts/validate_system.py`
   surfaces as `✓ Alternative: ... - Recommended`.
5. `RAGPipeline.__init__` catches that error at startup and logs it rather
   than crashing the whole API process, so `/health` still comes up and
   operators get an actionable log line instead of a silent hang.

Run `python scripts/validate_system.py` before deploying, and
`python scripts/select_models.py --recommend` when provisioning new
hardware, to exercise this logic ahead of time.

## Testing Strategy

### Unit Tests
- Query preprocessing (spellcheck, entity extraction)
- Document chunking (correct token counts)
- Ranking algorithms (RRF fusion)
- Prompt formatting

### Integration Tests
- End-to-end RAG pipeline
- Multi-tenant isolation
- Document ingestion pipeline
- Error handling and retries

### Performance Tests
- Query latency benchmarking
- Indexing throughput (docs/sec)
- Cache hit rate measurement
- Concurrent user scaling

### Load Tests
- Locust with configurable user profiles
- Steady-state load (1000 users)
- Spike testing (100→10000 users)
- Soak testing (long-duration stability)

## Deployment

### Development
```bash
docker-compose up -d
python scripts/setup_db.py
python -m uvicorn src.main:app --reload
```

### Production (Kubernetes)
```bash
kubectl apply -f infra/kubernetes/
```

### Private Cloud (Customer VPC)
```bash
terraform init
terraform apply -var-file=customer.tfvars
```

## Next Steps

1. **Phase 1**: Build core RAG pipeline (embedding → retrieval → LLM generation)
2. **Phase 2**: Add multi-tenancy, async indexing, advanced retrieval
3. **Phase 3**: Cloud deployment, compliance, monitoring
4. **Phase 4**: Model optimization, analytics, enterprise features

See [the full plan document](../RAG_PIPELINE_ARCHITECTURE_PLAN.md) for detailed milestones and implementation guidance.
