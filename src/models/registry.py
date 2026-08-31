"""Model configuration loading and runtime model resolution.

Implements the ModelRegistry abstraction / model selector-factory pattern
required by GitHub issue #1 ("Hardcoded LLM model with no runtime
flexibility"), the config loader required by issue #7 ("models.yaml defines
models but code doesn't use them"), the metadata fields required by issue #8
("Missing model metadata"), and the quantization support required by issue
#9 ("No quantization support configuration"). RAM/VRAM fit-checking used by
issue #5 lives here too, backed by src/models/resources.py.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml

logger = logging.getLogger(__name__)

# config/models.yaml relative to the repo root (src/models/registry.py -> src/models -> src -> repo root)
DEFAULT_MODELS_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "models.yaml"

VALID_QUANTIZATIONS = ("fp16", "int8", "int4")


class ModelNotFoundError(Exception):
    """Raised when a requested model identifier is not defined in models.yaml."""


class NoSuitableModelError(Exception):
    """Raised when no model in a fallback chain fits the available resources."""


@dataclass
class QuantizationProfile:
    """VRAM / quality / speed trade-off for one quantization method of a model."""

    method: str
    vram_gb: float
    quality_impact_percent: float = 0.0
    speed_multiplier: float = 1.0


@dataclass
class ModelMetadata:
    """Full metadata for one LLM entry from config/models.yaml."""

    key: str
    name: str
    size: str
    context_length: int
    parameters: int
    speed: str
    quality: str
    ollama_tag: str
    vram_required_gb: float
    vram_minimum_gb: float
    expected_latency_ms: float
    tokens_per_second: float
    max_batch_size: int
    quality_score: Optional[float] = None
    throughput_req_per_sec: Optional[float] = None
    quantization_options: List[str] = field(default_factory=list)
    quantizations: Dict[str, QuantizationProfile] = field(default_factory=dict)

    def vram_for_quantization(self, quantization: str = "fp16") -> float:
        """VRAM (GB) required to run this model at the given quantization.

        Falls back to vram_required_gb (fp16) if the model has no explicit
        entry for the requested quantization method.
        """
        profile = self.quantizations.get(quantization)
        if profile is not None:
            return profile.vram_gb
        logger.debug(
            f"Model '{self.key}' has no explicit '{quantization}' profile; "
            f"falling back to fp16 requirement ({self.vram_required_gb}GB)"
        )
        return self.vram_required_gb

    def fits_in_ram(self, available_gb: float, quantization: str = "fp16") -> bool:
        """Whether this model (at the given quantization) fits in available_gb."""
        return available_gb >= self.vram_for_quantization(quantization)

    def supports_quantization(self, quantization: str) -> bool:
        return quantization in self.quantization_options or quantization in self.quantizations


class ModelConfigLoader:
    """Loads and validates config/models.yaml (issue #7).

    Usage:
        loader = ModelConfigLoader().load()
        model = loader.get_llm_model("qwen:7b")   # by ollama_tag
        model = loader.get_llm_model("qwen")       # or by config key
    """

    def __init__(self, config_path: Optional[Union[Path, str]] = None):
        self.config_path = Path(config_path) if config_path else DEFAULT_MODELS_CONFIG_PATH
        self._raw: dict = {}
        self._llm_models: Dict[str, ModelMetadata] = {}
        self._loaded = False

    def load(self) -> "ModelConfigLoader":
        """Read and parse the YAML file. Safe to call more than once (re-reads)."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Model config not found at '{self.config_path}'")

        with open(self.config_path, "r") as f:
            self._raw = yaml.safe_load(f) or {}

        raw_llm_models = self._raw.get("llm_models") or {}
        self._llm_models = {key: self._parse_llm_model(key, data) for key, data in raw_llm_models.items()}
        self._loaded = True
        logger.info(f"Loaded {len(self._llm_models)} LLM model definitions from {self.config_path}")
        return self

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    @staticmethod
    def _parse_llm_model(key: str, data: dict) -> ModelMetadata:
        quantizations = {
            method: QuantizationProfile(
                method=method,
                vram_gb=float(q["vram_gb"]),
                quality_impact_percent=float(q.get("quality_impact_percent", 0)),
                speed_multiplier=float(q.get("speed_multiplier", 1.0)),
            )
            for method, q in (data.get("quantizations") or {}).items()
        }
        vram_required_gb = float(data.get("vram_required_gb", 0))
        return ModelMetadata(
            key=key,
            name=data.get("name", key),
            size=data.get("size", "unknown"),
            context_length=int(data.get("context_length", 0)),
            parameters=int(data.get("parameters", 0)),
            speed=data.get("speed", "unknown"),
            quality=data.get("quality", "unknown"),
            ollama_tag=data.get("ollama_tag", key),
            vram_required_gb=vram_required_gb,
            vram_minimum_gb=float(data.get("vram_minimum_gb", vram_required_gb)),
            expected_latency_ms=float(data.get("expected_latency_ms", 0)),
            tokens_per_second=float(data.get("tokens_per_second", 0)),
            max_batch_size=int(data.get("max_batch_size", 1)),
            quality_score=data.get("quality_score"),
            throughput_req_per_sec=data.get("throughput_req_per_sec"),
            quantization_options=list(data.get("quantization_options", [])),
            quantizations=quantizations,
        )

    def list_llm_models(self) -> Dict[str, ModelMetadata]:
        """All configured LLM models, keyed by their models.yaml key."""
        self._ensure_loaded()
        return dict(self._llm_models)

    def get_llm_model(self, identifier: str) -> ModelMetadata:
        """Look up a model by its config key (e.g. 'qwen') or ollama_tag (e.g. 'qwen:7b')."""
        self._ensure_loaded()
        if identifier in self._llm_models:
            return self._llm_models[identifier]
        for model in self._llm_models.values():
            if model.ollama_tag == identifier:
                return model
        available = ", ".join(sorted(self._llm_models))
        raise ModelNotFoundError(f"Model '{identifier}' not found in {self.config_path}. Available models: {available}")

    def validate_model_exists(self, identifier: str) -> bool:
        """True if `identifier` (key or ollama_tag) resolves to a configured model."""
        try:
            self.get_llm_model(identifier)
            return True
        except ModelNotFoundError:
            return False


def parse_fallback_chain(raw: str) -> List[str]:
    """Parse a MODEL_FALLBACK_CHAIN env value into an ordered list of model identifiers.

    Accepts either a plain comma-separated string:
        "qwen:32b,qwen:7b,mistral:7b"
    or the bracketed form shown in issue #12's example:
        "[qwen:32b, qwen:14b, qwen:7b]"
    Empty/whitespace-only input returns an empty list.
    """
    if not raw or not raw.strip():
        return []
    cleaned = raw.strip()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    items = [item.strip().strip("'\"") for item in cleaned.split(",")]
    return [item for item in items if item]


class ModelRegistry:
    """Runtime model selector/factory: resolves a usable model through a fallback chain.

    This is the abstraction required by issue #1 ("ModelRegistry abstraction,
    model selector/factory pattern, runtime model loading, model availability
    checking") combined with the RAM/VRAM validation required by issue #5.
    """

    def __init__(self, loader: Optional[ModelConfigLoader] = None):
        self.loader = loader or ModelConfigLoader()
        self.loader.load()

    def is_available(self, identifier: str) -> bool:
        """Model availability checking (issue #1) - does this identifier exist in config?"""
        return self.loader.validate_model_exists(identifier)

    def get(self, identifier: str) -> ModelMetadata:
        return self.loader.get_llm_model(identifier)

    def suggest_alternatives(self, available_gb: float, quantization: str = "fp16") -> List[ModelMetadata]:
        """Models (largest-first) that fit within available_gb at the given quantization."""
        fitting = [m for m in self.loader.list_llm_models().values() if m.fits_in_ram(available_gb, quantization)]
        fitting.sort(key=lambda m: m.vram_for_quantization(quantization), reverse=True)
        return fitting

    def check_fit(self, identifier: str, available_gb: float, quantization: str = "fp16") -> bool:
        return self.get(identifier).fits_in_ram(available_gb, quantization)

    def resolve(
        self,
        requested_model: str,
        available_ram_gb: Optional[float] = None,
        quantization: str = "fp16",
        fallback_chain: Optional[List[str]] = None,
    ) -> ModelMetadata:
        """Resolve a usable ModelMetadata, walking requested_model -> fallback_chain.

        If available_ram_gb is None, resource checking is skipped and the
        first model that exists in config is returned (identifier existence
        is still checked - "model availability checking" from issue #1).
        If available_ram_gb is given, each candidate is checked in order and
        the first one that both exists AND fits is returned. Raises
        NoSuitableModelError with actionable suggestions if nothing fits.
        """
        seen = set()
        candidates = []
        for candidate in [requested_model, *(fallback_chain or [])]:
            if candidate and candidate not in seen:
                seen.add(candidate)
                candidates.append(candidate)

        errors: List[str] = []
        for candidate in candidates:
            try:
                model = self.loader.get_llm_model(candidate)
            except ModelNotFoundError as e:
                logger.warning(f"Model '{candidate}' is not defined in {self.loader.config_path}; skipping. ({e})")
                errors.append(f"'{candidate}': not found in model config")
                continue

            if available_ram_gb is None:
                logger.info(f"Selected model '{model.key}' ({model.name}); no RAM figure supplied, skipping fit check.")
                return model

            required = model.vram_for_quantization(quantization)
            if available_ram_gb >= required:
                logger.info(
                    f"Selected model '{model.key}' ({model.name}): requires {required:.1f}GB "
                    f"[{quantization}], {available_ram_gb:.1f}GB available."
                )
                return model

            logger.warning(
                f"Model '{model.key}' ({model.name}) requires {required:.1f}GB [{quantization}] "
                f"but only {available_ram_gb:.1f}GB is available; trying next fallback."
            )
            errors.append(f"'{model.key}': needs {required:.1f}GB, only {available_ram_gb:.1f}GB available")

        suggestions = self.suggest_alternatives(available_ram_gb, quantization) if available_ram_gb is not None else []
        suggestion_text = (
            f" Alternatives that fit {available_ram_gb:.1f}GB available: "
            f"{', '.join(f'{m.key} ({m.vram_for_quantization(quantization):.1f}GB)' for m in suggestions)}."
            if suggestions
            else " No model in the catalog fits the available resources; consider int4 quantization or adding RAM."
        )
        raise NoSuitableModelError(
            f"No model in the fallback chain {candidates} could be loaded.{suggestion_text} "
            f"Details: {'; '.join(errors)}"
        )
