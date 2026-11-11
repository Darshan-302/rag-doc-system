"""FastAPI application entry point."""

import logging
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.api.schemas import (
    DocumentDeleteResponse,
    DocumentInfo,
    DocumentListResponse,
    DocumentUploadResponse,
    DomainInfo,
    DomainListResponse,
    HealthCheck,
    QueryRequest,
    QueryResponse,
)
from src.domains import DomainError, get_domain_profile, list_domains, log_query_access
from src.ingestion.document_processor import DocumentParseError, DocumentProcessor
from src.rag.embeddings import EmbeddingError
from src.rag.indexing import DocumentIndexer, document_type_from_filename, sanitize_filename
from src.rag.pipeline import RAGPipeline
from src.security.auth import require_tenant_access

# Logging setup
logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG pipeline
rag_pipeline = RAGPipeline()
_indexer: Optional[DocumentIndexer] = None


def get_pipeline() -> RAGPipeline:
    return rag_pipeline


def get_indexer() -> DocumentIndexer:
    """Indexer sharing the pipeline retriever's store and embedder."""
    global _indexer
    retriever = rag_pipeline.retriever
    if _indexer is None or _indexer.store is not retriever.store:
        _indexer = DocumentIndexer(retriever.store, retriever.embedder, on_change=retriever.invalidate)
    return _indexer


_domain_pipelines = {}


def _pipeline_for(domain: Optional[str], default: RAGPipeline) -> RAGPipeline:
    """Pipeline for a per-request domain (lazily created, cached).

    Domain pipelines share the default pipeline's retriever, so they see the
    same tenant-scoped store and embedder.
    """
    if domain is None:
        return default
    profile = get_domain_profile(domain)  # raises DomainError for unknown names
    if profile.name == default.domain_profile.name:
        return default
    cached = _domain_pipelines.get(profile.name)
    if cached is None or cached.retriever is not default.retriever:
        cached = RAGPipeline(domain=profile.name, retriever=default.retriever)
        _domain_pipelines[profile.name] = cached
    return cached


@app.on_event("startup")
async def startup():
    """Initialize services on startup."""
    logger.info("Starting RAG System API")
    logger.info(f"Using LLM: {settings.LLM_MODEL}")
    logger.info(f"Ollama URL: {settings.OLLAMA_BASE_URL}")
    logger.info(f"Retrieval: mode={settings.RETRIEVAL_MODE} store={settings.VECTOR_STORE} embedder={settings.EMBEDDER}")
    if settings.AUTH_ENABLED:
        from src.security.auth import parse_api_keys

        try:
            n = len(parse_api_keys(settings.API_KEYS))
        except ValueError:
            n = 0
        if n == 0:
            logger.warning("AUTH_ENABLED=true but API_KEYS is empty or invalid; every API request will get 401")
    else:
        logger.warning("AUTH_ENABLED=false: API is unauthenticated (development only)")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown."""
    logger.info("Shutting down RAG System API")


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint."""
    return HealthCheck(
        status="healthy",
        version=settings.API_VERSION,
        components={
            "database": "configured",
            "vector_db": "configured",
            "llm": settings.LLM_MODEL,
            "domain": settings.DOMAIN,
            "cache": "configured",
        },
    )


@app.get("/api/v1/domains", response_model=DomainListResponse)
async def get_domains():
    """List available industry domains and the active one."""
    return DomainListResponse(
        active=settings.DOMAIN,
        domains=[DomainInfo(**get_domain_profile(n).to_summary()) for n in list_domains()],
    )


@app.post("/api/v1/{tenant_id}/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    tenant_id: str = Depends(require_tenant_access),
    pipeline: RAGPipeline = Depends(get_pipeline),
):
    """Execute RAG query for document retrieval and answer generation."""
    try:
        pipeline = _pipeline_for(request.domain, pipeline)
    except DomainError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        logger.info(f"Processing query for tenant {tenant_id}")

        # Execute RAG pipeline
        result = await pipeline.query(
            tenant_id=tenant_id,
            query=request.query,
            top_k=request.top_k
        )

        logger.info(f"Query completed in {result.latency_ms}ms")

        log_query_access(
            pipeline.domain_profile,
            tenant_id,
            request.query,
            [str(src.get("document_id", "unknown")) for src in result.sources],
        )

        return QueryResponse(
            answer=result.answer,
            sources=result.sources,
            confidence=result.confidence,
            latency_ms=result.latency_ms
        )

    except Exception as e:
        logger.error(f"Query error for tenant {tenant_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/api/v1/{tenant_id}/documents/upload", response_model=DocumentUploadResponse)
async def upload_documents(
    file: UploadFile = File(...),
    document_type: Optional[str] = Form(None),
    tenant_id: str = Depends(require_tenant_access),
    indexer: DocumentIndexer = Depends(get_indexer),
):
    """Upload a pdf/docx/txt/csv/json document; it is chunked, embedded and indexed for the tenant."""
    filename = sanitize_filename(file.filename)
    ext = document_type_from_filename(filename)
    if ext not in DocumentProcessor.SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Supported: {', '.join(DocumentProcessor.SUPPORTED_FORMATS)}",
        )
    if document_type and document_type.lower() != ext:
        raise HTTPException(status_code=415, detail=f"document_type '{document_type}' does not match file extension '{ext}'")

    max_bytes = settings.MAX_DOCUMENT_SIZE_MB * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_DOCUMENT_SIZE_MB} MB limit")
    if not data:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")

    try:
        result = await indexer.index_document(tenant_id, filename, data, ext)
    except DocumentParseError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except EmbeddingError as e:
        logger.error(f"Embedding failed during upload for tenant {tenant_id}: {e}")
        raise HTTPException(status_code=503, detail="Embedding service unavailable")
    except Exception as e:
        logger.error(f"Indexing failed for tenant {tenant_id}: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Vector store unavailable")
    return DocumentUploadResponse(status="indexed", **result)


@app.get("/api/v1/{tenant_id}/documents", response_model=DocumentListResponse)
async def list_documents(
    skip: int = 0,
    limit: int = 50,
    tenant_id: str = Depends(require_tenant_access),
    indexer: DocumentIndexer = Depends(get_indexer),
):
    """List indexed documents for a tenant."""
    try:
        docs = await indexer.store.list_documents(tenant_id)
    except Exception as e:
        logger.error(f"List failed for tenant {tenant_id}: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Vector store unavailable")
    page = docs[max(skip, 0): max(skip, 0) + max(limit, 0)]
    return DocumentListResponse(
        documents=[
            DocumentInfo(
                document_id=d.document_id,
                document_name=d.document_name,
                upload_date=d.upload_date,
                chunk_count=d.chunk_count,
                file_size_bytes=d.file_size_bytes,
            )
            for d in page
        ],
        total_count=len(docs),
    )


@app.delete("/api/v1/{tenant_id}/documents/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: str,
    tenant_id: str = Depends(require_tenant_access),
    indexer: DocumentIndexer = Depends(get_indexer),
):
    """Delete a document (all its chunks) from the tenant's index."""
    try:
        removed = await indexer.delete_document(tenant_id, document_id)
    except Exception as e:
        logger.error(f"Delete failed for tenant {tenant_id}: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Vector store unavailable")
    if removed == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentDeleteResponse(status="deleted", document_id=document_id, chunks_deleted=removed)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=settings.LOG_LEVEL.lower(),
    )
