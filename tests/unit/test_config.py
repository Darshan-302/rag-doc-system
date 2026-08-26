"""Test application configuration."""

import os
import pytest
from src.config import settings


def test_settings_load_successfully():
    """Test that settings load without errors."""
    assert settings is not None


def test_default_database_url_configured():
    """Test that database URL is configured."""
    assert settings.DATABASE_URL is not None
    assert "postgres" in settings.DATABASE_URL.lower()


def test_redis_url_configured():
    """Test that Redis URL is configured."""
    assert settings.REDIS_URL is not None
    assert "redis" in settings.REDIS_URL.lower()


def test_weaviate_url_configured():
    """Test that Weaviate URL is configured."""
    assert settings.WEAVIATE_URL is not None


def test_ollama_base_url_configured():
    """Test that Ollama URL is configured."""
    assert settings.OLLAMA_BASE_URL is not None
    assert "11434" in settings.OLLAMA_BASE_URL


def test_default_llm_model_set():
    """Test that LLM model is configured."""
    assert settings.LLM_MODEL is not None
    assert len(settings.LLM_MODEL) > 0


def test_embedding_model_set():
    """Test that embedding model is configured."""
    assert settings.EMBEDDING_MODEL is not None


def test_chunk_size_reasonable():
    """Test that chunk size is reasonable."""
    assert settings.CHUNK_SIZE > 0
    assert settings.CHUNK_SIZE <= 2048, "Chunk size too large"


def test_top_k_documents_reasonable():
    """Test that TOP_K is reasonable."""
    assert settings.TOP_K_DOCUMENTS > 0
    assert settings.TOP_K_DOCUMENTS <= 20, "TOP_K too large"


def test_temperature_in_valid_range():
    """Test that temperature is in valid range."""
    assert 0 <= settings.LLM_TEMPERATURE <= 2.0


def test_max_tokens_reasonable():
    """Test that max tokens is reasonable."""
    assert settings.LLM_MAX_TOKENS > 0
    assert settings.LLM_MAX_TOKENS <= 8192
