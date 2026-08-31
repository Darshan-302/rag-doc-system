"""Tests for the multi-model-flexibility environment variables on Settings
(GitHub issue #12: ".env.example template for model configuration") and the
validation added for issues #1/#9."""

import pytest

from src.config import Settings


def test_new_model_flexibility_settings_have_sane_defaults():
    settings = Settings()
    assert settings.ENABLE_MODEL_AUTO_SELECT is False
    assert settings.RAM_AVAILABLE_GB is None
    assert settings.PREFERRED_MODEL_SIZE == "medium"
    assert settings.MODEL_FALLBACK_CHAIN
    assert settings.QUANTIZATION_METHOD == "fp16"
    assert settings.ALLOW_QUANTIZATION_FALLBACK is True
    assert settings.BATCH_SIZE > 0
    assert settings.MAX_CONCURRENT_REQUESTS > 0
    assert settings.CONTEXT_LENGTH > 0
    assert settings.LLM_TIMEOUT > 0


def test_settings_load_model_flexibility_vars_from_env(monkeypatch):
    monkeypatch.setenv("ENABLE_MODEL_AUTO_SELECT", "true")
    monkeypatch.setenv("RAM_AVAILABLE_GB", "48")
    monkeypatch.setenv("PREFERRED_MODEL_SIZE", "large")
    monkeypatch.setenv("MODEL_FALLBACK_CHAIN", "qwen:32b,qwen:7b,mistral:7b")
    monkeypatch.setenv("QUANTIZATION_METHOD", "int4")
    monkeypatch.setenv("ALLOW_QUANTIZATION_FALLBACK", "false")
    monkeypatch.setenv("BATCH_SIZE", "16")
    monkeypatch.setenv("MAX_CONCURRENT_REQUESTS", "8")
    monkeypatch.setenv("CONTEXT_LENGTH", "4096")
    monkeypatch.setenv("LLM_TIMEOUT", "60")

    settings = Settings()

    assert settings.ENABLE_MODEL_AUTO_SELECT is True
    assert settings.RAM_AVAILABLE_GB == 48.0
    assert settings.PREFERRED_MODEL_SIZE == "large"
    assert settings.MODEL_FALLBACK_CHAIN == "qwen:32b,qwen:7b,mistral:7b"
    assert settings.QUANTIZATION_METHOD == "int4"
    assert settings.ALLOW_QUANTIZATION_FALLBACK is False
    assert settings.BATCH_SIZE == 16
    assert settings.MAX_CONCURRENT_REQUESTS == 8
    assert settings.CONTEXT_LENGTH == 4096
    assert settings.LLM_TIMEOUT == 60


def test_model_fallback_list_property_parses_env_value(monkeypatch):
    monkeypatch.setenv("MODEL_FALLBACK_CHAIN", "qwen:32b, qwen:7b , mistral:7b")
    settings = Settings()
    assert settings.model_fallback_list == ["qwen:32b", "qwen:7b", "mistral:7b"]


@pytest.mark.parametrize("invalid_method", ["fp32", "int2", "none", ""])
def test_invalid_quantization_method_rejected(monkeypatch, invalid_method):
    monkeypatch.setenv("QUANTIZATION_METHOD", invalid_method)
    with pytest.raises(Exception):
        Settings()


@pytest.mark.parametrize("valid_method", ["fp16", "int8", "int4"])
def test_valid_quantization_methods_accepted(monkeypatch, valid_method):
    monkeypatch.setenv("QUANTIZATION_METHOD", valid_method)
    settings = Settings()
    assert settings.QUANTIZATION_METHOD == valid_method


@pytest.mark.parametrize("invalid_size", ["tiny", "huge", ""])
def test_invalid_preferred_model_size_rejected(monkeypatch, invalid_size):
    monkeypatch.setenv("PREFERRED_MODEL_SIZE", invalid_size)
    with pytest.raises(Exception):
        Settings()


def test_ram_available_gb_blank_env_value_treated_as_unset(monkeypatch):
    """.env.example ships `RAM_AVAILABLE_GB=` (blank) as a template default; must not crash Settings()."""
    monkeypatch.setenv("RAM_AVAILABLE_GB", "")
    settings = Settings()
    assert settings.RAM_AVAILABLE_GB is None


def test_llm_model_still_changeable_via_env(monkeypatch):
    """Issue #1 acceptance: 'Model can be changed via environment variable'."""
    monkeypatch.setenv("LLM_MODEL", "qwen:32b")
    settings = Settings()
    assert settings.LLM_MODEL == "qwen:32b"
