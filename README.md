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
│   └── chunking_strategies.yaml
├── docs/
│   ├── ARCHITECTURE.md     # Full architecture plan
│   ├── API.md              # API documentation
│   ├── DEPLOYMENT.md       # Deployment guides
│   └── TUNING.md           # Model & retrieval tuning
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
- **HIPAA**: PHI detection, encryption, access logging (for healthcare)
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

Environment variables in `.env`:

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
