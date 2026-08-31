"""Tests for ModelConfigLoader / ModelRegistry (GitHub issues #1, #5, #7, #8, #9)."""

import textwrap

import pytest

from src.models.registry import (
    ModelConfigLoader,
    ModelNotFoundError,
    ModelRegistry,
    NoSuitableModelError,
    parse_fallback_chain,
)

REAL_CONFIG_PATH = "config/models.yaml"


# --- ModelConfigLoader against the real config/models.yaml ---


def test_loader_loads_real_models_yaml():
    """config/models.yaml loads on startup (issue #7)."""
    loader = ModelConfigLoader(REAL_CONFIG_PATH).load()
    models = loader.list_llm_models()
    assert set(models.keys()) == {"mistral", "qwen", "qwen_32b", "llama2"}


def test_loader_lazy_loads_on_first_use():
    """Calling get_llm_model without an explicit .load() still works."""
    loader = ModelConfigLoader(REAL_CONFIG_PATH)
    model = loader.get_llm_model("qwen")
    assert model.name == "Qwen 7B"


def test_loader_get_by_config_key():
    loader = ModelConfigLoader(REAL_CONFIG_PATH).load()
    model = loader.get_llm_model("qwen_32b")
    assert model.name == "Qwen 32B"
    assert model.parameters == 32_000_000_000


def test_loader_get_by_ollama_tag():
    """Models are also resolvable by their ollama tag (e.g. LLM_MODEL=qwen:7b)."""
    loader = ModelConfigLoader(REAL_CONFIG_PATH).load()
    model = loader.get_llm_model("qwen:7b")
    assert model.key == "qwen"


def test_loader_validate_model_exists():
    loader = ModelConfigLoader(REAL_CONFIG_PATH).load()
    assert loader.validate_model_exists("qwen:32b") is True
    assert loader.validate_model_exists("qwen") is True
    assert loader.validate_model_exists("gpt-5-turbo-does-not-exist") is False


def test_loader_unknown_model_raises_with_available_list():
    loader = ModelConfigLoader(REAL_CONFIG_PATH).load()
    with pytest.raises(ModelNotFoundError) as exc_info:
        loader.get_llm_model("does-not-exist:99b")
    assert "does-not-exist:99b" in str(exc_info.value)
    assert "qwen" in str(exc_info.value)  # available models listed for guidance


def test_loader_missing_file_raises_filenotfound():
    loader = ModelConfigLoader("config/does_not_exist.yaml")
    with pytest.raises(FileNotFoundError):
        loader.load()


# --- Metadata fields required by issue #8 ---


def test_model_metadata_has_required_fields():
    loader = ModelConfigLoader(REAL_CONFIG_PATH).load()
    qwen_32b = loader.get_llm_model("qwen_32b")

    assert qwen_32b.vram_required_gb == 32
    assert qwen_32b.vram_minimum_gb == 8
    assert qwen_32b.expected_latency_ms > 0
    assert qwen_32b.tokens_per_second > 0
    assert qwen_32b.max_batch_size >= 1
    assert "int4" in qwen_32b.quantization_options


def test_all_models_have_quantization_metadata():
    """Every model.yaml entry has fp16/int8/int4 quantization profiles (issue #9)."""
    loader = ModelConfigLoader(REAL_CONFIG_PATH).load()
    for key, model in loader.list_llm_models().items():
        for method in ("fp16", "int8", "int4"):
            assert method in model.quantizations, f"{key} missing '{method}' quantization profile"
            profile = model.quantizations[method]
            assert profile.vram_gb > 0

        # int4 should require meaningfully less VRAM than fp16 (quantization actually helps)
        assert model.quantizations["int4"].vram_gb < model.quantizations["fp16"].vram_gb


def test_quantization_vram_matches_published_reduction_percentages():
    """README claims int8 ~50% reduction, int4 ~75% reduction vs fp16."""
    loader = ModelConfigLoader(REAL_CONFIG_PATH).load()
    for model in loader.list_llm_models().values():
        fp16 = model.quantizations["fp16"].vram_gb
        int8 = model.quantizations["int8"].vram_gb
        int4 = model.quantizations["int4"].vram_gb
        assert int8 == pytest.approx(fp16 * 0.5, rel=0.01)
        assert int4 == pytest.approx(fp16 * 0.25, rel=0.01)


def test_vram_for_quantization_falls_back_to_fp16_for_unknown_method():
    loader = ModelConfigLoader(REAL_CONFIG_PATH).load()
    model = loader.get_llm_model("qwen")
    assert model.vram_for_quantization("nonexistent-method") == model.vram_required_gb


# --- parse_fallback_chain (issue #12 env var parsing) ---


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("qwen:32b,qwen:7b,mistral:7b", ["qwen:32b", "qwen:7b", "mistral:7b"]),
        ("[qwen:32b, qwen:14b, qwen:7b]", ["qwen:32b", "qwen:14b", "qwen:7b"]),
        ("", []),
        ("   ", []),
        ("qwen:7b", ["qwen:7b"]),
    ],
)
def test_parse_fallback_chain(raw, expected):
    assert parse_fallback_chain(raw) == expected


# --- ModelRegistry: RAM-fit / fallback resolution (issue #1, #5) ---


def test_registry_resolves_requested_model_when_it_fits():
    registry = ModelRegistry(ModelConfigLoader(REAL_CONFIG_PATH))
    resolved = registry.resolve("qwen", available_ram_gb=16, quantization="fp16")
    assert resolved.key == "qwen"


def test_registry_raises_when_ram_too_low_for_entire_fallback_chain():
    """Mock scenario: only 4GB RAM available -> no fp16 model fits (all need >= 8GB)."""
    registry = ModelRegistry(ModelConfigLoader(REAL_CONFIG_PATH))
    with pytest.raises(NoSuitableModelError):
        registry.resolve(
            "qwen_32b",
            available_ram_gb=4,
            quantization="fp16",
            fallback_chain=["qwen", "mistral"],
        )


def test_registry_falls_back_to_smaller_model_that_fits():
    registry = ModelRegistry(ModelConfigLoader(REAL_CONFIG_PATH))
    # qwen_32b needs 32GB fp16; with only 16GB available it should fall back to qwen (8GB).
    resolved = registry.resolve(
        "qwen_32b",
        available_ram_gb=16,
        quantization="fp16",
        fallback_chain=["qwen", "mistral"],
    )
    assert resolved.key == "qwen"


def test_registry_uses_quantization_to_fit_larger_model():
    """int4 quantization lets qwen_32b (normally 32GB) fit in 16GB."""
    registry = ModelRegistry(ModelConfigLoader(REAL_CONFIG_PATH))
    resolved = registry.resolve("qwen_32b", available_ram_gb=16, quantization="int4")
    assert resolved.key == "qwen_32b"


def test_registry_raises_clear_error_when_nothing_fits():
    """With 1GB RAM, nothing in the fallback chain fits -> clear error with suggestions."""
    registry = ModelRegistry(ModelConfigLoader(REAL_CONFIG_PATH))
    with pytest.raises(NoSuitableModelError) as exc_info:
        registry.resolve(
            "qwen_32b",
            available_ram_gb=1,
            quantization="fp16",
            fallback_chain=["qwen", "mistral", "llama2"],
        )
    message = str(exc_info.value)
    assert "qwen_32b" in message
    # error message should be actionable
    assert "GB" in message


def test_registry_skips_unknown_models_in_fallback_chain():
    """A typo'd model in the fallback chain is skipped, not fatal, and logged."""
    registry = ModelRegistry(ModelConfigLoader(REAL_CONFIG_PATH))
    resolved = registry.resolve(
        "does-not-exist",
        available_ram_gb=16,
        quantization="fp16",
        fallback_chain=["also-does-not-exist", "qwen"],
    )
    assert resolved.key == "qwen"


def test_registry_suggest_alternatives_sorted_largest_first():
    registry = ModelRegistry(ModelConfigLoader(REAL_CONFIG_PATH))
    alternatives = registry.suggest_alternatives(available_gb=16, quantization="fp16")
    keys = [m.key for m in alternatives]
    assert "qwen_32b" not in keys  # doesn't fit at fp16 with 16GB
    assert "qwen" in keys
    # sorted largest VRAM requirement first
    vram_values = [m.vram_for_quantization("fp16") for m in alternatives]
    assert vram_values == sorted(vram_values, reverse=True)


def test_registry_is_available_checks_existence():
    registry = ModelRegistry(ModelConfigLoader(REAL_CONFIG_PATH))
    assert registry.is_available("qwen:7b") is True
    assert registry.is_available("totally-made-up-model") is False


def test_registry_resolve_without_ram_figure_skips_fit_check():
    """When no RAM figure is supplied, resolve just checks the model exists."""
    registry = ModelRegistry(ModelConfigLoader(REAL_CONFIG_PATH))
    resolved = registry.resolve("qwen_32b", available_ram_gb=None)
    assert resolved.key == "qwen_32b"
