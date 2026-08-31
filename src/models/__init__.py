"""Model registry, config loading, and resource-detection utilities.

This package implements the "multi-model runtime flexibility" feature:
- ``registry``: loads config/models.yaml, validates requested models,
  and resolves a runtime model through a fallback chain that accounts
  for available RAM/VRAM (see GitHub issues #1, #5, #7, #8, #9).
- ``resources``: best-effort system resource detection (RAM, disk, GPU
  VRAM, Ollama reachability) used by the registry and by
  scripts/validate_system.py (see issues #5, #11).
"""

from src.models.registry import (
    ModelConfigLoader,
    ModelMetadata,
    ModelNotFoundError,
    ModelRegistry,
    NoSuitableModelError,
    QuantizationProfile,
    parse_fallback_chain,
)
from src.models.resources import (
    check_ollama_reachable,
    get_available_ram_gb,
    get_disk_space_gb,
    get_gpu_vram_gb,
    get_total_ram_gb,
)

__all__ = [
    "ModelConfigLoader",
    "ModelMetadata",
    "ModelNotFoundError",
    "ModelRegistry",
    "NoSuitableModelError",
    "QuantizationProfile",
    "parse_fallback_chain",
    "check_ollama_reachable",
    "get_available_ram_gb",
    "get_disk_space_gb",
    "get_gpu_vram_gb",
    "get_total_ram_gb",
]
