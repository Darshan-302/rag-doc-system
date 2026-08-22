"""SQLAlchemy ORM models for PostgreSQL."""

from sqlalchemy import Column, String, Integer, Float, DateTime, Text, Boolean, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Document(Base):
    """Document metadata."""
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    source_type = Column(String(50), nullable=False)  # pdf, docx, txt, etc.
    file_size_bytes = Column(Integer)
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    indexed_at = Column(DateTime)
    embedding_model_version = Column(String(100))
    checksum = Column(String(64))


class DocumentChunk(Base):
    """Document chunks for indexing."""
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True)
    document_id = Column(String(36), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    tokens = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class VectorIndex(Base):
    """Vector index metadata."""
    __tablename__ = "vector_indices"

    id = Column(String(36), primary_key=True)
    chunk_id = Column(String(36), nullable=False, unique=True)
    embedding_vector = Column(LargeBinary)  # serialized numpy array
    embedding_model = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    """Audit trail for compliance."""
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    action = Column(String(100), nullable=False)  # document.uploaded, query.executed, etc.
    document_id = Column(String(36))
    user_id = Column(String(36))
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
