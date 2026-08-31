#!/usr/bin/env python3
"""Validate system resources against the configured LLM before startup.

Implements GitHub issue #11 ("No memory validation during setup") and the
startup-validation half of issue #5 ("No validation that models fit in
available RAM"). Reuses the ModelConfigLoader/ModelRegistry built for
issues #1/#7 (src/models/registry.py) and the resource-detection helpers in
src/models/resources.py.

Usage:
    python scripts/validate_system.py
    python scripts/validate_system.py --model qwen:32b
    python scripts/validate_system.py --model qwen:32b --quantization int4
    python scripts/validate_system.py --min-disk-gb 100 --json
"""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings  # noqa: E402
from src.models.registry import ModelConfigLoader, ModelNotFoundError  # noqa: E402
from src.models.resources import (  # noqa: E402
    check_ollama_reachable,
    get_available_ram_gb,
    get_disk_space_gb,
    get_gpu_vram_gb,
    get_total_ram_gb,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CHECK = "✓"  # checkmark
CROSS = "✗"  # X mark
MIN_DISK_GB_DEFAULT = 20.0


def validate_system_resources(min_disk_gb: float = MIN_DISK_GB_DEFAULT) -> dict:
    """Check RAM, disk, GPU VRAM, and Ollama reachability. Returns a result dict."""
    print("Validating system resources...")

    result = {}

    total_ram = get_total_ram_gb()
    available_ram = get_available_ram_gb()
    ram_ok = available_ram > 0
    result["ram_available_gb"] = available_ram
    result["ram_total_gb"] = total_ram
    if ram_ok:
        print(f"{CHECK} RAM Available: {available_ram:.1f}GB (of {total_ram:.1f}GB total)")
        logger.info(f"RAM check passed: {available_ram:.1f}GB available / {total_ram:.1f}GB total")
    else:
        print(f"{CROSS} RAM Available: could not be determined on this platform")
        logger.warning("RAM check inconclusive: unable to detect available RAM (psutil not installed?)")

    disk_free = get_disk_space_gb(".")
    disk_ok = disk_free >= min_disk_gb
    result["disk_available_gb"] = disk_free
    if disk_ok:
        print(f"{CHECK} Disk Available: {disk_free:.1f}GB")
        logger.info(f"Disk check passed: {disk_free:.1f}GB free (minimum {min_disk_gb}GB)")
    else:
        print(f"{CROSS} Disk Available: {disk_free:.1f}GB (minimum recommended: {min_disk_gb}GB)")
        logger.warning(f"Disk check failed: only {disk_free:.1f}GB free, minimum recommended is {min_disk_gb}GB")

    gpu_info = get_gpu_vram_gb()
    if gpu_info is not None:
        vram_gb, gpu_name = gpu_info
        result["gpu_vram_gb"] = vram_gb
        result["gpu_name"] = gpu_name
        print(f"{CHECK} GPU VRAM: {vram_gb:.0f}GB ({gpu_name})")
        logger.info(f"GPU detected: {gpu_name} with {vram_gb:.0f}GB VRAM")
    else:
        result["gpu_vram_gb"] = None
        result["gpu_name"] = None
        print(f"{CHECK} GPU VRAM: N/A (no NVIDIA GPU detected - CPU/RAM-based inference assumed)")
        logger.info("No GPU detected; falling back to RAM-based fit checks for models")

    ollama_ok = check_ollama_reachable(settings.OLLAMA_BASE_URL)
    result["ollama_reachable"] = ollama_ok
    if ollama_ok:
        print(f"{CHECK} Ollama reachable at {settings.OLLAMA_BASE_URL}")
        logger.info(f"Ollama reachability check passed at {settings.OLLAMA_BASE_URL}")
    else:
        print(f"{CROSS} Ollama NOT reachable at {settings.OLLAMA_BASE_URL}")
        logger.warning(f"Ollama reachability check failed at {settings.OLLAMA_BASE_URL} - is it running?")

    result["ram_ok"] = ram_ok
    result["disk_ok"] = disk_ok
    result["ollama_ok"] = ollama_ok
    return result


def validate_model_selection(model_identifier: str, quantization: str, available_gb: float) -> dict:
    """Check whether `model_identifier` fits in `available_gb` and suggest alternatives if not."""
    print(f"\nChecking model: {model_identifier}")

    loader = ModelConfigLoader()
    try:
        loader.load()
    except FileNotFoundError as e:
        print(f"{CROSS} Could not load config/models.yaml: {e}")
        logger.error(f"Model config load failed: {e}")
        return {"model_found": False, "fits": False}

    try:
        model = loader.get_llm_model(model_identifier)
    except ModelNotFoundError as e:
        print(f"{CROSS} {e}")
        logger.error(str(e))
        return {"model_found": False, "fits": False}

    required_gb = model.vram_for_quantization(quantization)
    fits = available_gb is not None and available_gb >= required_gb

    result = {
        "model_found": True,
        "model_key": model.key,
        "model_name": model.name,
        "required_gb": required_gb,
        "available_gb": available_gb,
        "quantization": quantization,
        "fits": fits,
    }

    if available_gb is None:
        print(f"{CROSS} Requires {required_gb:.0f}GB ({quantization}) but available RAM could not be determined")
        logger.warning(f"Cannot validate '{model.key}' fit: available RAM unknown")
        return result

    if fits:
        print(f"{CHECK} {model.name} fits: requires {required_gb:.0f}GB ({quantization}), {available_gb:.0f}GB available")
        logger.info(f"Model fit check passed: '{model.key}' requires {required_gb:.0f}GB, {available_gb:.0f}GB available")
        return result

    print(f"{CROSS} Requires {required_gb:.0f}GB {quantization.upper() if quantization != 'fp16' else 'VRAM'} but only {available_gb:.0f}GB available")
    logger.warning(f"Model '{model.key}' does not fit: needs {required_gb:.0f}GB, only {available_gb:.0f}GB available")

    alternatives = [
        m for m in loader.list_llm_models().values()
        if m.key != model.key and m.fits_in_ram(available_gb, quantization)
    ]
    alternatives.sort(key=lambda m: m.vram_for_quantization(quantization), reverse=True)

    result["alternatives"] = [a.key for a in alternatives]

    if alternatives:
        for i, alt in enumerate(alternatives):
            label = "Recommended" if i == 0 else ("Fast option" if i == len(alternatives) - 1 else "Alternative")
            req = alt.vram_for_quantization(quantization)
            print(f"{CHECK} Alternative: {alt.name} ({req:.0f}GB {'VRAM' if quantization == 'fp16' else quantization}) - {label}")
        logger.info(f"Suggested {len(alternatives)} alternative(s) for '{model.key}': {[a.key for a in alternatives]}")
    elif model.supports_quantization("int4") and quantization != "int4":
        int4_gb = model.vram_for_quantization("int4")
        print(f"{CHECK} Alternative: {model.name} with QUANTIZATION_METHOD=int4 ({int4_gb:.0f}GB) - Recommended")
        logger.info(f"Suggested int4 quantization for '{model.key}': {int4_gb:.0f}GB required")
    else:
        print(f"{CROSS} No alternative model in config/models.yaml fits {available_gb:.0f}GB available")
        logger.warning(f"No alternative model fits {available_gb:.0f}GB available")

    return result


def main():
    parser = argparse.ArgumentParser(description="Validate system resources for running the RAG system's LLM.")
    parser.add_argument("--model", default=settings.LLM_MODEL, help="Model identifier to validate (default: LLM_MODEL from settings/.env)")
    parser.add_argument("--quantization", default=settings.QUANTIZATION_METHOD, choices=["fp16", "int8", "int4"], help="Quantization method to validate against")
    parser.add_argument("--min-disk-gb", type=float, default=MIN_DISK_GB_DEFAULT, help="Minimum free disk space (GB) considered healthy")
    parser.add_argument("--json", action="store_true", help="Also print a machine-readable JSON summary")
    args = parser.parse_args()

    system_result = validate_system_resources(min_disk_gb=args.min_disk_gb)

    # Prefer GPU VRAM for the fit check when a GPU is present; otherwise use available RAM.
    available_gb = system_result.get("gpu_vram_gb") or (system_result.get("ram_available_gb") or None)
    if available_gb == 0:
        available_gb = None

    model_result = validate_model_selection(args.model, args.quantization, available_gb)

    print()
    overall_ok = system_result["disk_ok"] and system_result["ollama_ok"] and model_result.get("model_found", False)
    if overall_ok and model_result.get("fits", False):
        print(f"{CHECK} System validation complete: ready to run '{args.model}'.")
    elif overall_ok:
        print(f"{CROSS} System validation complete with warnings: see alternatives above before running '{args.model}'.")
    else:
        print(f"{CROSS} System validation failed: resolve the issues above before starting the RAG system.")

    if args.json:
        print(json.dumps({"system": system_result, "model": model_result}, indent=2))

    # Non-fatal by default: this script informs, it does not block startup on its own.
    # A hard failure (missing config, unreachable Ollama, and no model found) exits non-zero
    # so it can be wired into CI/startup checks if desired.
    if not model_result.get("model_found", False):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
