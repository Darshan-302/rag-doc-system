# RAG System - Commercial Document Retrieval & Generation Platform

A production-ready, multi-tenant Retrieval-Augmented Generation (RAG) platform for enterprise document retrieval and AI-powered answer generation. Built with local LLMs (27B-34B parameters), vector embeddings, and hybrid search capabilities.

## 🎯 Features

- **Local LLM Inference**: Multiple model support (7B to 34B parameters, no cloud dependency, full privacy)
- **Multi-Format Document Support**: PDF, DOCX, CSV, TXT, JSON, images (with OCR)
- **Semantic + Keyword Search**: Hybrid retrieval with BM25 + vector embeddings
- **Multi-Tenancy**: Complete tenant isolation with JWT-based auth
- **Scalable Architecture**: Supports MVP (10K docs) → Enterprise (1M+ docs)
- **Commercial-Ready**: GDPR, HIPAA, SOC2 compliance framework
- **Fast Retrieval**: <2-3 seconds end-to-end query latency (varies by model)
- **Source Attribution**: Automatic citation of retrieved documents
- **Resource Management**: Automatic memory limits and resource allocation

## 📋 Supported LLM Models

| Model | Size | VRAM | Speed | Quality | Use Case | Quantization |
|-------|------|------|-------|---------|----------|--------------|
| Qwen 7B | 15GB | 8GB | ⚡⚡⚡ | Good | Development, MVP | fp16, int8, int4 |
| Mistral 7B | 15GB | 8GB | ⚡⚡⚡ | Good | Development, MVP | fp16, int8, int4 |
| Llama-2 13B | 26GB | 14GB | ⚡⚡ | Good | Small production | fp16, int8 |
| Qwen 14B | 26GB | 16GB | ⚡⚡ | Excellent | Production | fp16, int8 |
| Qwen 32B | 65GB | 32GB | ⚡ | Superior | Enterprise | fp16, int8, int4 |
| Mistral 34B | 70GB | 40GB | ⚡ | Excellent | Enterprise | fp16, int8 |

**Quantization Benefits** (reduce VRAM requirements):
- int4: 75% reduction in VRAM usage
- int8: 50% reduction in VRAM usage
- fp16: Full precision (no reduction)

### 🧭 Model Selection Guide

Model choice is entirely runtime-configurable (`LLM_MODEL` env var, no code
changes required - see [.env.example](.env.example)), backed by
[config/models.yaml](config/models.yaml) which now carries full metadata
(VRAM at every quantization level, expected latency, throughput, max batch
size) for `mistral`, `qwen`, `qwen_32b`, and `llama2`. At startup, or any
time you want a second opinion, run:

```bash
python scripts/validate_system.py         # checks RAM/disk/GPU/Ollama + your configured model
python scripts/select_models.py --list    # table of every model + whether it fits this machine
python scripts/select_models.py --recommend  # best-quality model that fits, given RAM_AVAILABLE_GB
```

If the configured model doesn't fit, the pipeline automatically walks
`MODEL_FALLBACK_CHAIN` (e.g. `qwen:32b,qwen:7b,mistral:7b`) and picks the
first model that fits in `RAM_AVAILABLE_GB` at `QUANTIZATION_METHOD` - see
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#model-selection--fallback-strategy)
for the full fallback/degradation strategy.

**How to choose:**
1. Start from your available RAM (or GPU VRAM, if you have a dedicated GPU).
2. Pick the largest model whose fp16 VRAM requirement fits comfortably below
   that figure, leaving headroom for Ollama, Weaviate, Postgres, Redis, and
   MinIO running alongside it.
3. If your preferred model doesn't fit in fp16, check `int8` (~50% smaller)
   or `int4` (~75% smaller) before dropping to a smaller model - quality
   impact is small (1-3%, see `quantizations` in `config/models.yaml`).
4. Always set `MODEL_FALLBACK_CHAIN` so a temporary resource shortage
   degrades gracefully instead of crashing.

**Worked examples:**

| Deployment | Recommended model | Config | Why |
|---|---|---|---|
| **16GB RAM** (dev/MVP laptop) | Qwen 7B or Mistral 7B, fp16 | `LLM_MODEL=qwen:7b`<br>`QUANTIZATION_METHOD=fp16` | 8GB VRAM leaves ~8GB for the rest of the stack; fast (~6.5s p95), good quality for MVP work. |
| **32GB RAM** (small production) | Qwen 32B, int4 | `LLM_MODEL=qwen:32b`<br>`QUANTIZATION_METHOD=int4`<br>`MODEL_FALLBACK_CHAIN=qwen:32b,qwen:7b,mistral:7b` | int4 shrinks Qwen 32B to ~8GB VRAM, so you get "superior" quality output with room to spare - the fallback chain drops to Qwen 7B automatically if another process eats the headroom. |
| **48GB+ RAM** (enterprise) | Qwen 32B, fp16 (or int8 for more headroom) | `LLM_MODEL=qwen:32b`<br>`QUANTIZATION_METHOD=fp16`<br>`MODEL_FALLBACK_CHAIN=qwen:32b,qwen:7b,mistral:7b` | Full 32GB fp16 weights fit with room for concurrent requests (`MAX_CONCURRENT_REQUESTS=8`); use `int8` (16GB) instead if you're also running large concurrent embedding workloads. |

## 📋 Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **LLM** | Configurable (7B-34B models) | Choose based on hardware and quality needs |
| **Embeddings** | BGE Large EN v1.5 | 1024-dim, optimized retrieval, 0.3B params |
| **Vector DB** | Weaviate | Native multi-tenancy, hybrid search, self-hostable |
| **Document Store** | PostgreSQL + MinIO | Enterprise-standard, scalable architecture |
| **Cache** | Redis | High-performance query/embedding caching |
| **API** | FastAPI | Modern async Python framework |
| **Task Queue** | Celery + Redis | Async document indexing at scale |
| **Container** | Docker + Kubernetes | Development → Enterprise deployment |

## 🚀 Quick Start

### Prerequisites

**Minimum (Development)**
- Docker & Docker Compose
- 24GB+ RAM (for full stack)
- Storage: 100GB+ for models and data

**Recommended (Production)**
- Docker & Docker Compose
- 48GB+ RAM (for optimal performance)
- GPU: NVIDIA RTX 3090 / A100 / 4090 for LLM inference
- Storage: 500GB+ SSD for models and scaling

**By LLM Model Size**
- **7B Models** (Mistral, Qwen): 16GB RAM minimum
- **14B Models** (Qwen): 24GB RAM minimum
- **32B Models** (Qwen): 48GB RAM recommended
- **34B Models** (Mistral): 48GB+ RAM

**Resource Allocation** (configured in docker-compose.yml)
- Ollama: 32GB limit / 16GB reservation
- Weaviate: 4GB limit / 2GB reservation
- PostgreSQL: 2GB limit / 1GB reservation
- Redis: 2GB limit / 1GB reservation
- MinIO: 2GB limit / 1GB reservation

### 1. Clone & Setup

```bash
# Create environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Verify services are healthy
docker-compose ps
```

### 2. Download Models

**Choose a model based on your available RAM:**

```bash
# For 16GB RAM (Development)
docker exec rag_ollama ollama pull qwen:7b
docker exec rag_ollama ollama pull nomic-embed-text:latest

# For 32GB RAM (Recommended)
docker exec rag_ollama ollama pull qwen:14b
docker exec rag_ollama ollama pull nomic-embed-text:latest

# For 48GB+ RAM (High Quality)
docker exec rag_ollama ollama pull qwen:32b
docker exec rag_ollama ollama pull nomic-embed-text:latest
```

Not sure which model to pick, whether it will fit, or how much disk it
needs? Use the interactive helper instead of guessing:

```bash
# Validate RAM/disk/GPU/Ollama and check whether your configured LLM_MODEL fits
python scripts/validate_system.py

# See every model's fit status on this machine, get a recommendation, and
# download + verify it (validates disk space first, verifies via `ollama list` after)
python scripts/select_models.py --list
python scripts/select_models.py --recommend
python scripts/select_models.py --pull qwen        # or: --pull qwen --dry-run
```

**Model Sizes** (after download):
- 7B models: ~15GB
- 14B models: ~26GB
- 32B models: ~65GB
- Embedding model: ~0.3GB

See **Supported LLM Models** section above for detailed specs.

### 3. Initialize Database

```bash
# Apply migrations
python scripts/setup_db.py

# Create vector DB collections
python scripts/setup_vector_db.py

# Load test data (optional)
python scripts/load_test_data.py
```

### 4. Run API

```bash
# Start API server
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Access API docs: http://localhost:8000/docs
```

### 5. Test Query

```bash
curl -X POST "http://localhost:8000/api/v1/default-tenant/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main features of the product?",
    "top_k": 5
  }'
```

## 📁 Project Structure

```
rag-system/
├── src/
│   ├── api/                # FastAPI routes and schemas
│   ├── rag/                # Core RAG pipeline (retrieval + generation)
│   ├── ingestion/          # Document processing and chunking
│   ├── db/                 # Database models and clients
│   ├── search/             # Query processing and hybrid search
│   ├── security/           # Tenant isolation, auth, compliance
│   ├── monitoring/         # Observability, metrics, logging
│   ├── config.py           # Configuration management
│   └── main.py             # FastAPI application
├── tests/
│   ├── unit/               # Unit tests
│   ├── integration/        # End-to-end tests
│   ├── performance/        # Benchmarking
│   └── fixtures/           # Test data
├── scripts/
│   ├── setup_db.py         # Database initialization
│   ├── setup_vector_db.py  # Weaviate setup
│   ├── load_test_data.py   # Load test fixtures
│   └── benchmark_retrieval.py
├── infra/
│   ├── docker-compose.yml  # Local development
│   ├── docker-compose.prod.yml  # Production stack
│   ├── kubernetes/         # K8s manifests
│   └── terraform/          # AWS infrastructure
├── config/
│   ├── models.yaml         # Model configurations
│   ├── prompts.yaml        # System prompts, few-shot examples
│   ├── chunking_strategies.yaml
│   ├── healthcare_models.yaml   # Healthcare-oriented model config
│   ├── healthcare_prompts.yaml  # Medical-terminology-aware prompts
│   ├── drug_database.yaml       # Synthetic/illustrative drug reference config
│   ├── insurance_models.yaml   # Insurance-optimized model configs
│   ├── insurance_prompts.yaml  # Insurance-specific prompts
│   └── insurance.env.example   # Sample .env for insurance deployments
├── docs/
│   ├── ARCHITECTURE.md     # Full architecture plan
│   ├── API.md              # API documentation
│   ├── DEPLOYMENT.md       # Deployment guides
│   ├── TUNING.md           # Model & retrieval tuning
│   ├── HEALTHCARE_RAG_GUIDE.md    # HIPAA/PHI design notes for healthcare RAG
│   ├── HEALTHCARE_EXAMPLES.md     # Healthcare example queries (synthetic data)
│   ├── INSURANCE_RAG_GUIDE.md   # Insurance RAG setup & compliance
│   └── INSURANCE_EXAMPLES.md    # Insurance example queries/policies
├── data/
│   └── healthcare/         # Synthetic healthcare sample data (see data/healthcare/README.md)
├── pyproject.toml          # Poetry dependencies
└── docker-compose.yml      # Development stack
```

## 🔧 Core Components

### 1. RAG Pipeline (`src/rag/pipeline.py`)
Main orchestration:
- Query → Embedding
- Vector search → Hybrid ranking
- LLM generation → Source attribution

### 2. Document Ingestion (`src/ingestion/`)
Multi-format parsing:
- PDF, DOCX, CSV, JSON, images
- Semantic chunking (512 tokens, 50 token overlap)
- Async batch processing with Celery

### 3. Vector Search (`src/search/`)
Hybrid retrieval:
- Semantic search (Weaviate HNSW)
- BM25 keyword search
- Cross-encoder reranking (top-5)

### 4. LLM Inference (`src/rag/llm.py`)
Answer generation:
- Mistral-34B via Ollama
- Few-shot prompting
- Token batching for throughput

### 5. Multi-Tenancy (`src/security/tenant_isolation.py`)
Complete isolation:
- JWT-based tenant routing
- Per-tenant Weaviate collections
- Separate PostgreSQL schemas
- Audit logging

## 📊 Performance Targets

| Metric | MVP | Scale | Enterprise |
|--------|-----|-------|-----------|
| Documents | 10K | 100K | 1M+ |
| Query Latency (p95) | <5s | <3s | <2s |
| Concurrent Users | 100 | 1000 | 10K+ |
| Uptime SLA | 99% | 99.9% | 99.95% |
| Cost/Query | $0.05 | $0.02 | $0.01 |

## 🔐 Security & Compliance

- **Multi-Tenancy**: Complete data isolation per tenant
- **GDPR**: Right to erasure, data portability, audit trails
- **HIPAA**: PHI detection, encryption, access logging (for healthcare) — see [HEALTHCARE_RAG_GUIDE.md](docs/HEALTHCARE_RAG_GUIDE.md) for detailed design notes and disclaimers
- **SOC2**: Automated backups, encryption, vulnerability scanning
- **Data Residency**: EU/US/APAC region options

## 📈 Deployment Scenarios

### 1. SaaS (Shared Infrastructure)
- Single Ollama instance + GPU cluster
- Per-tenant collections in Weaviate
- ~$3.5K/month (MVP) → $21.5K/month (Scale)

### 2. Private Cloud (Customer VPC)
- Docker Compose in customer AWS account
- Dedicated GPU instance
- License: $2K/month

### 3. On-Premises (Air-Gapped)
- Full Kubernetes in customer data center
- Pre-cached models
- License: $15K+/month

## 🛣️ Development Roadmap

**Phase 1 (Weeks 1-8)**: MVP with single-tenant RAG  
**Phase 2 (Weeks 9-16)**: Multi-tenancy + scale to 100K docs  
**Phase 3 (Weeks 17-24)**: Enterprise features + K8s + compliance  
**Phase 4 (Weeks 25-32)**: Model optimization + multi-language  

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed plan.

## 📚 API Examples

### Query Documents

```bash
POST /api/v1/{tenant_id}/query
{
  "query": "What are your pricing options?",
  "top_k": 5
}

Response:
{
  "answer": "We offer three pricing tiers...",
  "sources": [
    {
      "document_id": "doc-001",
      "document_name": "Pricing Guide",
      "score": 0.92,
      "text": "..."
    }
  ],
  "confidence": 0.87,
  "latency_ms": 2340
}
```

### Upload Documents

```bash
POST /api/v1/{tenant_id}/documents/upload
Content-Type: multipart/form-data

file: policy_document.pdf
document_type: pdf
```

### List Documents

```bash
GET /api/v1/{tenant_id}/documents?skip=0&limit=50
```

### Delete Document

```bash
DELETE /api/v1/{tenant_id}/documents/{document_id}
```

## 🧪 Testing

```bash
# Run unit tests
pytest tests/unit -v

# Run integration tests
pytest tests/integration -v

# Run performance benchmarks
pytest tests/performance -v

# Load test with Locust
locust -f tests/performance/locustfile.py --host=http://localhost:8000
```

## 📊 Monitoring

Services expose Prometheus metrics:

```bash
# View metrics
curl http://localhost:8000/metrics

# Grafana dashboard
http://localhost:3000 (default: admin/admin)
```

Key metrics:
- Query latency (p50, p95, p99)
- Embedding cache hit rate
- Vector DB query time
- LLM inference time
- Token usage per tenant

## 🤝 Contributing

1. Create a feature branch
2. Add tests for new functionality
3. Ensure code passes `black`, `ruff`, `mypy`
4. Submit PR with description

## 📝 Configuration

See [.env.example](.env.example) for the full, commented list of every
environment variable (API, database, Redis, Weaviate, Ollama/model
selection, document processing, retrieval, MinIO, multi-tenancy, rate
limiting, Celery) plus ready-to-uncomment example configs for 16GB/32GB/48GB
deployments. Quick reference:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/rag_db

# Redis
REDIS_URL=redis://localhost:6379

# Weaviate
WEAVIATE_URL=http://localhost:8080

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=mistral:latest
EMBEDDING_MODEL=nomic-embed-text:latest

# S3 / MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# RAG Parameters
CHUNK_SIZE=512
CHUNK_OVERLAP=50
TOP_K_DOCUMENTS=5
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1024
```

## 🆘 Troubleshooting

**Services won't start:**
```bash
docker-compose down -v  # Remove volumes
docker-compose up -d    # Restart
```

**Out of memory:**
- Reduce `EMBEDDING_BATCH_SIZE` in config
- Use smaller LLM (Llama-2-13B instead of 34B)
- Reduce number of concurrent workers

**Slow queries:**
- Check Redis cache hit rate
- Verify Weaviate index status
- Profile with ELK stack logs

## 📖 Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - Full system design
- [API.md](docs/API.md) - API reference
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) - Cloud deployment guides
- [TUNING.md](docs/TUNING.md) - Performance optimization
- [HEALTHCARE_RAG_GUIDE.md](docs/HEALTHCARE_RAG_GUIDE.md) - Healthcare-domain RAG pipeline: HIPAA/PHI handling concepts, security & compliance design notes (see disclaimer in the guide)
- [HEALTHCARE_EXAMPLES.md](docs/HEALTHCARE_EXAMPLES.md) - Example healthcare queries and flows (synthetic sample data only)
- [INSURANCE_RAG_GUIDE.md](docs/INSURANCE_RAG_GUIDE.md) - Insurance industry RAG pipeline: setup, domain-specific features, and compliance (HIPAA, state regulations)
- [INSURANCE_EXAMPLES.md](docs/INSURANCE_EXAMPLES.md) - Example insurance policies, claims workflows, and queries (fictional sample data)
- [FINANCE_RAG_GUIDE.md](docs/FINANCE_RAG_GUIDE.md) - Finance industry RAG pipeline: regulatory compliance, data sources, and compliance design notes
- [FINANCE_EXAMPLES.md](docs/FINANCE_EXAMPLES.md) - Worked finance query examples (regulatory, compliance, risk, trading rules)

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

### MIT License Summary
- ✅ Free for personal and commercial use
- ✅ Can modify and distribute
- ✅ Can use in private projects
- ❌ No warranty or liability
- ❌ Must include license copy

---

**Questions?** Open an issue or contact @Darshan-302
