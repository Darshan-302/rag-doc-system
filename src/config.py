"""Configuration management for RAG System."""

from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import List, Optional

VALID_QUANTIZATION_METHODS = ("fp16", "int8", "int4")
VALID_MODEL_SIZES = ("small", "medium", "large")
VALID_RETRIEVAL_MODES = ("keyword", "vector", "hybrid")
VALID_VECTOR_STORES = ("weaviate", "memory")
VALID_EMBEDDERS = ("ollama", "hashing")
VALID_DOMAINS = ("general", "insurance", "healthcare", "finance")


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
    WEAVIATE_GRPC_PORT: int = 50051
    WEAVIATE_COLLECTION: str = "DocumentChunk"

    # Industry domain: selects prompts/model recommendations/audit hook from
    # src/domains (general, insurance, healthcare, finance).
    DOMAIN: str = "general"

    # LLM (Ollama)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen:7b"
    EMBEDDING_MODEL: str = "nomic-embed-text:latest"

    # Inference Parameters
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2048
    LLM_TOP_P: float = 0.9
    EMBEDDING_BATCH_SIZE: int = 128

    # --- Multi-Model Runtime Flexibility (see docs/ARCHITECTURE.md, config/models.yaml) ---

    # Auto-select the best-fitting model from config/models.yaml instead of
    # failing when LLM_MODEL doesn't fit in RAM_AVAILABLE_GB.
    ENABLE_MODEL_AUTO_SELECT: bool = False

    # Available system RAM/VRAM in GB, used to validate LLM_MODEL fits before
    # loading (issue #5). If unset, it is auto-detected at startup via
    # src/models/resources.py (psutil when installed).
    RAM_AVAILABLE_GB: Optional[float] = None

    # Coarse hint used by ENABLE_MODEL_AUTO_SELECT / scripts/select_models.py
    # when recommending a model: "small", "medium", or "large".
    PREFERRED_MODEL_SIZE: str = "medium"

    # Ordered list of model identifiers (config/models.yaml keys or ollama
    # tags) to try if LLM_MODEL doesn't fit or fails to load, e.g.
    # "qwen:32b,qwen:7b,mistral:7b" or the bracketed "[qwen:32b, qwen:7b]".
    MODEL_FALLBACK_CHAIN: str = "qwen:7b,mistral:7b"

    # Quantization method to request when loading LLM_MODEL: fp16, int8, or int4.
    QUANTIZATION_METHOD: str = "fp16"

    # If the requested QUANTIZATION_METHOD isn't enough to fit RAM_AVAILABLE_GB,
    # allow the pipeline to drop to a more aggressive quantization automatically.
    ALLOW_QUANTIZATION_FALLBACK: bool = True

    # Performance tuning
    BATCH_SIZE: int = 32
    MAX_CONCURRENT_REQUESTS: int = 4
    CONTEXT_LENGTH: int = 2048
    LLM_TIMEOUT: int = 30

    # Document Processing
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50
    MAX_DOCUMENT_SIZE_MB: int = 100

    # Retrieval
    TOP_K_DOCUMENTS: int = 5
    SIMILARITY_THRESHOLD: float = 0.3

    # keyword = BM25 only, vector = embeddings only, hybrid = BM25 + vector
    # fused with Reciprocal Rank Fusion.
    RETRIEVAL_MODE: str = "hybrid"
    # weaviate = persistent, one Weaviate tenant per API tenant;
    # memory = process-local (dev/tests, lost on restart).
    VECTOR_STORE: str = "weaviate"
    # ollama = real embeddings via OLLAMA_BASE_URL; hashing = deterministic
    # offline feature-hashing embedder (no network, lower quality).
    EMBEDDER: str = "ollama"
    RRF_K: int = 60
    # JSONL of public demo chunks used when the vector store/embedder is
    # unreachable or a tenant has no indexed documents. Blank disables it.
    SAMPLE_CORPUS_PATH: str = "data/processed/rag_training_data.jsonl"

    # API authentication (see src/security/auth.py).
    # API_KEYS format: "key1=tenantA,tenantB;key2=*"  ("*" = every tenant)
    AUTH_ENABLED: bool = True
    API_KEYS: str = ""

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

    @field_validator("RAM_AVAILABLE_GB", mode="before")
    @classmethod
    def _empty_ram_available_is_unset(cls, value):
        """Treat RAM_AVAILABLE_GB= (blank, as left by .env.example) as unset/None."""
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    @field_validator("DOMAIN", mode="before")
    @classmethod
    def _validate_domain(cls, value):
        normalized = str(value).strip().lower() if value is not None else ""
        if normalized == "":
            return "general"
        if normalized not in VALID_DOMAINS:
            raise ValueError(f"DOMAIN must be one of {VALID_DOMAINS}, got '{value}'")
        return normalized

    @field_validator("QUANTIZATION_METHOD")
    @classmethod
    def _validate_quantization_method(cls, value: str) -> str:
        if value not in VALID_QUANTIZATION_METHODS:
            raise ValueError(
                f"QUANTIZATION_METHOD must be one of {VALID_QUANTIZATION_METHODS}, got '{value}'"
            )
        return value

    @field_validator("RETRIEVAL_MODE")
    @classmethod
    def _validate_retrieval_mode(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in VALID_RETRIEVAL_MODES:
            raise ValueError(f"RETRIEVAL_MODE must be one of {VALID_RETRIEVAL_MODES}, got '{value}'")
        return value

    @field_validator("VECTOR_STORE")
    @classmethod
    def _validate_vector_store(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in VALID_VECTOR_STORES:
            raise ValueError(f"VECTOR_STORE must be one of {VALID_VECTOR_STORES}, got '{value}'")
        return value

    @field_validator("EMBEDDER")
    @classmethod
    def _validate_embedder(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in VALID_EMBEDDERS:
            raise ValueError(f"EMBEDDER must be one of {VALID_EMBEDDERS}, got '{value}'")
        return value

    @field_validator("PREFERRED_MODEL_SIZE")
    @classmethod
    def _validate_preferred_model_size(cls, value: str) -> str:
        if value not in VALID_MODEL_SIZES:
            raise ValueError(
                f"PREFERRED_MODEL_SIZE must be one of {VALID_MODEL_SIZES}, got '{value}'"
            )
        return value

    @property
    def model_fallback_list(self) -> List[str]:
        """MODEL_FALLBACK_CHAIN parsed into an ordered list of model identifiers."""
        from src.models.registry import parse_fallback_chain

        return parse_fallback_chain(self.MODEL_FALLBACK_CHAIN)


settings = Settings()
