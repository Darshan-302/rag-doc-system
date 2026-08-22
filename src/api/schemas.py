"""Pydantic models for API request/response validation."""

from pydantic import BaseModel, Field
from typing import Optional, List


class QueryRequest(BaseModel):
    """User query request."""
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(5, ge=1, le=20)


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
