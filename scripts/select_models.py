#!/usr/bin/env python3
"""Interactive/CLI model selection and download helper for the RAG system.

Implements GitHub issue #10 ("Missing model download/setup guidance"):
- Validates available disk space before downloading a model
- Checks VRAM/RAM requirements against config/models.yaml
- Prints model download recommendations based on detected/declared RAM
- Verifies a model after `ollama pull` (via `ollama list`)

Style follows scripts/setup_qwen.sh (step-numbered output, .env update) and
scripts/download_training_data.py (a small class + logging module, runnable
as `python scripts/select_models.py`).

Usage:
    python scripts/select_models.py --list                 # show all models + fit status
    python scripts/select_models.py --recommend             # recommend a model for this machine
    python scripts/select_models.py --pull qwen              # download + verify a model
    python scripts/select_models.py --pull qwen --dry-run    # show what would happen, no download
    python scripts/select_models.py                          # interactive menu (TTY only)
"""

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import settings  # noqa: E402
from src.models.registry import ModelConfigLoader, ModelMetadata, ModelNotFoundError  # noqa: E402
from src.models.resources import get_available_ram_gb, get_disk_space_gb, get_gpu_vram_gb  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Rough multiplier from a model's on-disk size (models.yaml `size`, e.g. "65GB")
# to the free disk space we require before pulling it, to leave headroom for
# the Ollama layer cache and a partially-downloaded blob.
DISK_HEADROOM_MULTIPLIER = 1.2


def _parse_size_gb(size_str: str) -> float:
    """Parse a models.yaml `size` field like '15GB' into a float number of GB."""
    return float(size_str.upper().rstrip("GB").strip())


class ModelSelector:
    """Recommends, downloads, and verifies Ollama models using config/models.yaml."""

    def __init__(self, config_path: str = None):
        self.loader = ModelConfigLoader(config_path) if config_path else ModelConfigLoader()
        self.loader.load()

    def list_models(self, available_gb: float = None) -> list:
        """Return all configured models with a computed 'fits' flag."""
        models = list(self.loader.list_llm_models().values())
        models.sort(key=lambda m: m.vram_required_gb)
        return models

    def print_model_table(self, available_gb: float = None):
        logger.info("Available models (config/models.yaml):")
        print(f"\n{'Model':<12} {'Params':<8} {'VRAM(fp16)':<12} {'VRAM(int4)':<12} {'Quality':<10} {'Fits?':<6}")
        print("-" * 66)
        for model in self.list_models():
            fits = "n/a" if available_gb is None else (
                "yes" if model.fits_in_ram(available_gb, "fp16") else
                ("int4" if model.fits_in_ram(available_gb, "int4") else "no")
            )
            params_b = model.parameters / 1_000_000_000
            print(
                f"{model.key:<12} {params_b:>5.0f}B   {model.vram_required_gb:>8.0f}GB    "
                f"{model.vram_for_quantization('int4'):>8.0f}GB    {model.quality:<10} {fits:<6}"
            )
        print()

    def recommend(self, available_gb: float, preferred_size: str = "medium") -> ModelMetadata:
        """Recommend the best-quality model (optionally requiring quantization) that fits."""
        candidates = list(self.loader.list_llm_models().values())

        size_order = {"small": 0, "medium": 1, "large": 2}
        preferred_rank = size_order.get(preferred_size, 1)

        def size_rank(m: ModelMetadata) -> int:
            if m.vram_required_gb <= 8:
                return 0
            if m.vram_required_gb <= 16:
                return 1
            return 2

        fitting_fp16 = [m for m in candidates if m.fits_in_ram(available_gb, "fp16")]
        fitting_int4 = [m for m in candidates if m.fits_in_ram(available_gb, "int4")]

        pool = fitting_fp16 or fitting_int4
        if not pool:
            raise RuntimeError(
                f"No model fits in {available_gb:.1f}GB even with int4 quantization. "
                f"Smallest model needs {min(m.vram_for_quantization('int4') for m in candidates):.1f}GB."
            )

        # Prefer models matching the preferred size bucket; otherwise the best-quality fitting model.
        matching_size = [m for m in pool if size_rank(m) == preferred_rank]
        pool_to_rank = matching_size or pool
        pool_to_rank.sort(key=lambda m: (m.quality_score or 0), reverse=True)
        return pool_to_rank[0]

    def validate_disk_space(self, model: ModelMetadata, target_path: str = ".") -> tuple:
        """Return (ok, free_gb, required_gb) - required includes download headroom."""
        required_gb = _parse_size_gb(model.size) * DISK_HEADROOM_MULTIPLIER
        free_gb = get_disk_space_gb(target_path)
        return free_gb >= required_gb, free_gb, required_gb

    @staticmethod
    def _ollama_available() -> bool:
        return shutil.which("ollama") is not None

    def pull(self, model: ModelMetadata, dry_run: bool = False) -> bool:
        """Download `model` via `ollama pull` after validating disk space, then verify it."""
        ok, free_gb, required_gb = self.validate_disk_space(model)
        if not ok:
            logger.error(f"Insufficient disk space for '{model.key}': need ~{required_gb:.1f}GB, only {free_gb:.1f}GB free")
            print(f"✗ Not enough disk space: need ~{required_gb:.1f}GB, only {free_gb:.1f}GB free")
            return False
        logger.info(f"Disk space check passed for '{model.key}': {free_gb:.1f}GB free, ~{required_gb:.1f}GB required")
        print(f"✓ Disk space OK: {free_gb:.1f}GB free (need ~{required_gb:.1f}GB)")

        if dry_run:
            print(f"[dry-run] Would run: ollama pull {model.ollama_tag}")
            return True

        if not self._ollama_available():
            logger.error("`ollama` CLI not found on PATH; install it from https://ollama.ai before pulling models.")
            print("✗ `ollama` CLI not found on PATH. Install it from https://ollama.ai and re-run this script.")
            return False

        print(f"Downloading {model.name} ({model.ollama_tag})...")
        logger.info(f"Running: ollama pull {model.ollama_tag}")
        result = subprocess.run(["ollama", "pull", model.ollama_tag])
        if result.returncode != 0:
            logger.error(f"`ollama pull {model.ollama_tag}` failed with exit code {result.returncode}")
            print(f"✗ Download failed (exit code {result.returncode})")
            return False

        return self.verify(model)

    def verify(self, model: ModelMetadata) -> bool:
        """Verify a model is installed via `ollama list`."""
        if not self._ollama_available():
            print("✗ Cannot verify: `ollama` CLI not found on PATH")
            return False
        try:
            result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=15)
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"Could not run `ollama list` to verify '{model.key}': {e}")
            print(f"✗ Could not verify installation: {e}")
            return False

        installed = model.ollama_tag.split(":")[0] in result.stdout and model.ollama_tag in result.stdout
        if installed:
            logger.info(f"Verified '{model.ollama_tag}' is installed")
            print(f"✓ Verified: {model.name} ({model.ollama_tag}) is installed and ready")
        else:
            logger.warning(f"'{model.ollama_tag}' not found in `ollama list` output after pull")
            print(f"⚠ Warning: '{model.ollama_tag}' not found in `ollama list` output; the pull may not have completed")
        return installed


def _print_env_hint(model: ModelMetadata):
    print("\nTo use this model, set in your .env:")
    print(f"  LLM_MODEL={model.ollama_tag}")


def run_interactive(selector: ModelSelector, available_gb: float):
    print("\n" + "=" * 60)
    print("RAG System - Interactive Model Selection")
    print("=" * 60)
    selector.print_model_table(available_gb)

    models = selector.list_models()
    for i, m in enumerate(models, 1):
        print(f"  {i}. {m.name} ({m.key})")
    print(f"  0. Auto-recommend for {available_gb:.1f}GB available" if available_gb else "  0. Auto-recommend")

    choice = input("\nSelect a model to download [0]: ").strip() or "0"
    try:
        idx = int(choice)
    except ValueError:
        print("Invalid selection.")
        return

    if idx == 0:
        model = selector.recommend(available_gb or 8.0, settings.PREFERRED_MODEL_SIZE)
        print(f"Recommended: {model.name}")
    elif 1 <= idx <= len(models):
        model = models[idx - 1]
    else:
        print("Invalid selection.")
        return

    confirm = input(f"Download {model.name} ({model.ollama_tag})? [y/N]: ").strip().lower()
    if confirm == "y":
        selector.pull(model)
        _print_env_hint(model)
    else:
        print("Skipped download.")
        _print_env_hint(model)


def main():
    parser = argparse.ArgumentParser(description="Select, validate, and download RAG system LLM models.")
    parser.add_argument("--list", action="store_true", help="List all models in config/models.yaml with fit status")
    parser.add_argument("--recommend", action="store_true", help="Recommend a model for the detected/declared RAM")
    parser.add_argument("--pull", metavar="MODEL", help="Download + verify a model (config key or ollama tag)")
    parser.add_argument("--verify", metavar="MODEL", help="Verify a model is already installed via `ollama list`")
    parser.add_argument("--ram-gb", type=float, default=None, help="Override available RAM/VRAM (GB); defaults to RAM_AVAILABLE_GB or auto-detection")
    parser.add_argument("--dry-run", action="store_true", help="Validate everything but don't actually run `ollama pull`")
    parser.add_argument("--non-interactive", action="store_true", help="Never prompt; used for CI / scripted runs")
    args = parser.parse_args()

    selector = ModelSelector()

    available_gb = args.ram_gb if args.ram_gb is not None else settings.RAM_AVAILABLE_GB
    if available_gb is None:
        gpu = get_gpu_vram_gb()
        available_gb = gpu[0] if gpu else get_available_ram_gb()

    if args.list:
        selector.print_model_table(available_gb)
        return

    if args.recommend:
        try:
            model = selector.recommend(available_gb, settings.PREFERRED_MODEL_SIZE)
        except RuntimeError as e:
            print(f"✗ {e}")
            sys.exit(1)
        print(f"\nRecommended model for {available_gb:.1f}GB available ({settings.PREFERRED_MODEL_SIZE} preference):")
        print(f"  {model.name} ({model.ollama_tag}) - {model.vram_required_gb:.0f}GB VRAM (fp16), quality: {model.quality}")
        _print_env_hint(model)
        return

    if args.verify:
        try:
            model = selector.loader.get_llm_model(args.verify)
        except ModelNotFoundError as e:
            print(f"✗ {e}")
            sys.exit(1)
        ok = selector.verify(model)
        sys.exit(0 if ok else 1)

    if args.pull:
        try:
            model = selector.loader.get_llm_model(args.pull)
        except ModelNotFoundError as e:
            print(f"✗ {e}")
            sys.exit(1)

        if available_gb and not model.fits_in_ram(available_gb, "fp16"):
            print(f"⚠ Warning: {model.name} needs {model.vram_required_gb:.0f}GB but only {available_gb:.1f}GB is available.")
            if model.fits_in_ram(available_gb, "int4"):
                print(f"  It would fit with QUANTIZATION_METHOD=int4 ({model.vram_for_quantization('int4'):.0f}GB).")
            alternatives = [m for m in selector.list_models() if m.key != model.key and m.fits_in_ram(available_gb, "fp16")]
            if alternatives:
                print(f"  Alternative: {alternatives[0].name} ({alternatives[0].ollama_tag}) fits comfortably.")
            if not args.non_interactive and sys.stdin.isatty():
                if input("Continue anyway? [y/N]: ").strip().lower() != "y":
                    print("Aborted.")
                    return

        ok = selector.pull(model, dry_run=args.dry_run)
        if ok and not args.dry_run:
            _print_env_hint(model)
        sys.exit(0 if ok else 1)

    # No flags given: interactive menu if we have a TTY, otherwise show the table + recommendation.
    if args.non_interactive or not sys.stdin.isatty():
        print("Non-interactive mode (no TTY / --non-interactive): showing model table and recommendation.\n")
        selector.print_model_table(available_gb)
        try:
            model = selector.recommend(available_gb, settings.PREFERRED_MODEL_SIZE)
            print(f"Recommended: {model.name} ({model.ollama_tag})")
            _print_env_hint(model)
        except RuntimeError as e:
            print(f"✗ {e}")
        return

    run_interactive(selector, available_gb)


if __name__ == "__main__":
    main()
