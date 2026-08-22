"""Configuration management for RAG System."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # API Configuration
    API_TITLE: str = "RAG Pipeline API"
    API_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Database
    DATABASE_URL: str = "postgresql://rag_user:rag_password@localhost:5432/rag_db"
    DB_USER: str = "rag_user"
    DB_PASSWORD: str = "rag_password"
    DB_NAME: str = "rag_db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_CACHE_TTL: int = 3600  # 1 hour

    # Vector Database (Weaviate)
    WEAVIATE_URL: str = "http://localhost:8080"
    WEAVIATE_API_KEY: str = "weaviate-key"

    # LLM (Ollama)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen:7b"
    EMBEDDING_MODEL: str = "nomic-embed-text:latest"

    # Inference Parameters
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2048
    LLM_TOP_P: float = 0.9
    EMBEDDING_BATCH_SIZE: int = 128

    # Document Processing
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    MAX_DOCUMENT_SIZE_MB: int = 100

    # Retrieval
    TOP_K_DOCUMENTS: int = 5
    SIMILARITY_THRESHOLD: float = 0.3

    # S3 / MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_USER: str = "minioadmin"
    MINIO_PASSWORD: str = "minioadmin"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "rag-documents"
    MINIO_SECURE: bool = False

    # Multi-Tenancy
    ENABLE_MULTI_TENANCY: bool = True

    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 10
    RATE_LIMIT_WINDOW: int = 60  # seconds

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


settings = Settings()
