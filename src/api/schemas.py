"""Pydantic models for API request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional, List


class QueryRequest(BaseModel):
    """User query request."""
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(5, ge=1, le=20)
    domain: Optional[str] = Field(
        None, description="Industry domain for this request; defaults to the configured DOMAIN."
    )


class SourceDocument(BaseModel):
    """Source document in response."""
    document_id: str
    document_name: str
    chunk_id: int
    score: float
    text: str


class QueryResponse(BaseModel):
    """RAG query response."""
    answer: str
    sources: List[SourceDocument]
    confidence: float = Field(..., ge=0.0, le=1.0)
    latency_ms: float


class DocumentUploadRequest(BaseModel):
    """Document upload request."""
    document_name: str
    document_type: str = Field(..., pattern="^(pdf|docx|txt|csv|json)$")


class DocumentUploadResponse(BaseModel):
    """Result of indexing an uploaded document."""
    status: str
    document_id: str
    document_name: str
    chunk_count: int
    file_size_bytes: int


class DocumentDeleteResponse(BaseModel):
    """Result of deleting a document."""
    status: str
    document_id: str
    chunks_deleted: int


class DocumentInfo(BaseModel):
    """Document metadata."""
    document_id: str
    document_name: str
    upload_date: str
    chunk_count: int
    file_size_bytes: int


class DocumentListResponse(BaseModel):
    """List of documents."""
    documents: List[DocumentInfo]
    total_count: int


class HealthCheck(BaseModel):
    """System health check response."""
    status: str
    version: str
    components: dict


class DomainInfo(BaseModel):
    """One selectable industry domain."""
    name: str
    description: str
    preferred_model: Optional[str] = None
    fallback_models: List[str] = []
    corpus_dir: str
    audit_logger: Optional[str] = None
    task_prompts: List[str] = []
    retrieval: dict = {}


class DomainListResponse(BaseModel):
    """Available domains and the active (configured) one."""
    active: str
    domains: List[DomainInfo]
