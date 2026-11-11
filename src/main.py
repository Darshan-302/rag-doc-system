"""FastAPI application entry point."""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.api.schemas import (
    QueryRequest, QueryResponse, DocumentListResponse, HealthCheck,
    DomainInfo, DomainListResponse,
)
from src.domains import DomainError, get_domain_profile, list_domains, log_query_access
from src.rag.pipeline import RAGPipeline

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
_domain_pipelines = {rag_pipeline.domain_profile.name: rag_pipeline}


def _pipeline_for(domain):
    """Pipeline for a per-request domain (lazily created, cached)."""
    if domain is None:
        return rag_pipeline
    profile = get_domain_profile(domain)  # raises DomainError for unknown names
    if profile.name not in _domain_pipelines:
        _domain_pipelines[profile.name] = RAGPipeline(domain=profile.name)
    return _domain_pipelines[profile.name]


@app.on_event("startup")
async def startup():
    """Initialize services on startup."""
    logger.info("Starting RAG System API")
    logger.info(f"Using LLM: {settings.LLM_MODEL}")
    logger.info(f"Ollama URL: {settings.OLLAMA_BASE_URL}")


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
async def query(tenant_id: str, request: QueryRequest):
    """Execute RAG query for document retrieval and answer generation."""
    try:
        pipeline = _pipeline_for(request.domain)
    except DomainError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        logger.info(f"Processing query for tenant {tenant_id}: {request.query}")

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


@app.post("/api/v1/{tenant_id}/documents/upload")
async def upload_documents(tenant_id: str):
    """Upload documents for indexing."""
    return {
        "status": "not_implemented",
        "message": "Document upload not yet implemented"
    }


@app.get("/api/v1/{tenant_id}/documents", response_model=DocumentListResponse)
async def list_documents(tenant_id: str, skip: int = 0, limit: int = 50):
    """List indexed documents for a tenant."""
    return DocumentListResponse(documents=[], total_count=0)


@app.delete("/api/v1/{tenant_id}/documents/{document_id}")
async def delete_document(tenant_id: str, document_id: str):
    """Delete a document from the index."""
    return {"status": "not_implemented"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=settings.LOG_LEVEL.lower(),
    )
