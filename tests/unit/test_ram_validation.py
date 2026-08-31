"""Tests for RAM/disk/GPU resource detection and RAM-aware model selection
(GitHub issues #5 and #11: "No validation that models fit in available RAM",
"No memory validation during setup")."""

from unittest.mock import MagicMock, patch

import pytest

import src.models.resources as resources
from src.models.registry import ModelConfigLoader, ModelRegistry, NoSuitableModelError

REAL_CONFIG_PATH = "config/models.yaml"


# --- get_available_ram_gb() ---


def test_get_available_ram_gb_uses_psutil_when_present():
    fake_vmem = MagicMock(available=16 * (1024 ** 3))
    with patch.object(resources, "_HAS_PSUTIL", True), patch.object(resources, "psutil", MagicMock(virtual_memory=lambda: fake_vmem)):
        assert resources.get_available_ram_gb() == pytest.approx(16.0)


def test_get_available_ram_gb_falls_back_without_psutil(tmp_path, monkeypatch):
    """Without psutil, falls back to reading /proc/meminfo (Linux-style)."""
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemTotal:       33554432 kB\nMemAvailable:   8388608 kB\n")

    real_open = open

    def fake_open(path, *args, **kwargs):
        if path == "/proc/meminfo":
            return real_open(meminfo, *args, **kwargs)
        return real_open(path, *args, **kwargs)

    with patch.object(resources, "_HAS_PSUTIL", False), patch("builtins.open", fake_open):
        available_gb = resources.get_available_ram_gb()
    assert available_gb == pytest.approx(8.0, rel=0.01)


def test_get_available_ram_gb_returns_zero_when_undetectable():
    with patch.object(resources, "_HAS_PSUTIL", False), patch("builtins.open", side_effect=FileNotFoundError):
        assert resources.get_available_ram_gb() == 0.0


# --- get_disk_space_gb() ---


def test_get_disk_space_gb_reports_positive_value(tmp_path):
    free_gb = resources.get_disk_space_gb(str(tmp_path))
    assert free_gb > 0


# --- get_gpu_vram_gb() best-effort detection ---


def test_get_gpu_vram_gb_returns_none_without_nvidia_smi():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        assert resources.get_gpu_vram_gb() is None


def test_get_gpu_vram_gb_parses_nvidia_smi_output():
    fake_result = MagicMock(returncode=0, stdout="24576, NVIDIA RTX 4090\n")
    with patch("subprocess.run", return_value=fake_result):
        vram_gb, name = resources.get_gpu_vram_gb()
    assert vram_gb == pytest.approx(24.0, rel=0.01)
    assert "4090" in name


# --- check_ollama_reachable() ---


def test_check_ollama_reachable_true_on_200():
    fake_response = MagicMock(status_code=200)
    with patch("httpx.get", return_value=fake_response):
        assert resources.check_ollama_reachable("http://localhost:11434") is True


def test_check_ollama_reachable_false_on_connection_error():
    with patch("httpx.get", side_effect=ConnectionError("refused")):
        assert resources.check_ollama_reachable("http://localhost:11434") is False


# --- RAM-aware model resolution (mocking "available RAM") ---


def test_resolve_picks_correct_fallback_for_mocked_low_ram():
    """Simulates a machine with only 10GB available: qwen_32b (32GB) must fall back to a 7B model."""
    registry = ModelRegistry(ModelConfigLoader(REAL_CONFIG_PATH))
    mocked_available_ram_gb = 10.0  # e.g. patched value of resources.get_available_ram_gb()

    resolved = registry.resolve(
        "qwen_32b",
        available_ram_gb=mocked_available_ram_gb,
        quantization="fp16",
        fallback_chain=["qwen", "mistral", "llama2"],
    )

    assert resolved.key in {"qwen", "mistral", "llama2"}
    assert resolved.vram_for_quantization("fp16") <= mocked_available_ram_gb


def test_resolve_raises_clear_error_for_mocked_very_low_ram():
    """Simulates a machine with only 1GB available: nothing fits, error must be actionable."""
    registry = ModelRegistry(ModelConfigLoader(REAL_CONFIG_PATH))
    mocked_available_ram_gb = 1.0

    with pytest.raises(NoSuitableModelError) as exc_info:
        registry.resolve(
            "qwen_32b",
            available_ram_gb=mocked_available_ram_gb,
            quantization="fp16",
            fallback_chain=["qwen", "mistral", "llama2"],
        )

    message = str(exc_info.value)
    # Clear, actionable error: names the requested model and reports the shortfall.
    assert "qwen_32b" in message
    assert "1.0GB" in message or "1GB" in message


def test_resolve_suggests_int4_sized_alternative_when_ram_is_tight():
    """With 10GB available, int4 quantization should let qwen_32b fit (8GB int4)."""
    registry = ModelRegistry(ModelConfigLoader(REAL_CONFIG_PATH))
    resolved = registry.resolve("qwen_32b", available_ram_gb=10.0, quantization="int4")
    assert resolved.key == "qwen_32b"
