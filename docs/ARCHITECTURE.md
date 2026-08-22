# RAG System Architecture & Implementation Guide

This is the comprehensive architectural plan for the commercial RAG pipeline system. For the full detailed plan with cost analysis and compliance requirements, see the separate plan document.

## Quick Reference

- **Local LLM**: Mistral-34B or Llama-3-34B (27B-34B parameters)
- **Embeddings**: BGE Large EN v1.5 (1024 dimensions)
- **Vector DB**: Weaviate (multi-tenant ready)
- **Document Store**: PostgreSQL + MinIO S3
- **Inference Runtime**: Ollama + vLLM
- **Query Latency Target**: <2-3 seconds (p95)
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
[LLM Generation] - Create answer with Mistral-34B
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
   - Send to Ollama (Mistral-34B)
   - Generate answer with source tracking
   - Batch inference if multiple queries
   
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

### 6. LLM Inference (`src/rag/llm.py`)

**Mistral-34B Setup** (via Ollama):

```python
class LLMClient:
    def __init__(self, base_url="http://localhost:11434"):
        self.model = "mistral:latest"
        self.base_url = base_url
    
    async def generate(self, prompt: str, context_tokens: List[int]):
        response = await ollama.generate(
            model=self.model,
            prompt=prompt,
            stream=False,
            temperature=0.7,
            top_p=0.9,
            num_predict=1024,
        )
        return response.response
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
