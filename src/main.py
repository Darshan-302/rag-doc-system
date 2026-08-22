"""FastAPI application entry point."""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.api.schemas import QueryRequest, QueryResponse, DocumentListResponse, HealthCheck
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
            "cache": "configured",
        },
    )


@app.post("/api/v1/{tenant_id}/query", response_model=QueryResponse)
async def query(tenant_id: str, request: QueryRequest):
    """Execute RAG query for document retrieval and answer generation."""
    try:
        logger.info(f"Processing query for tenant {tenant_id}: {request.query}")

        # Execute RAG pipeline
        result = await rag_pipeline.query(
            tenant_id=tenant_id,
            query=request.query,
            top_k=request.top_k
        )

        logger.info(f"Query completed in {result.latency_ms}ms")

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
