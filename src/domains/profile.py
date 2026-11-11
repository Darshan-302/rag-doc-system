"""Industry domain profiles: loads a domain's prompt/model YAML files.

A *domain* (general, insurance, healthcare, finance) bundles:

* a prompts YAML (system prompt, few-shot examples, task prompts, safety text),
* a models YAML (recommended models and retrieval tuning),
* a default corpus location, and
* which audit hook (if any) applies.

Mapping of a domain ``*_models.yaml`` onto the base ``config/models.yaml``:
the domain files use the same ``llm_models:`` layout but carry no runtime
metadata (no ``ollama_tag``/VRAM figures). They are therefore treated as
*recommendations*: each ``llm_models`` key is mapped to a base registry key
(``<key>_<domain>`` -> ``<key>``, e.g. ``qwen_32b_finance`` -> ``qwen_32b``),
the first one is ``preferred_model`` and the rest ``fallback_models``. The
actual model is still chosen by ``LLM_MODEL`` / ``MODEL_FALLBACK_CHAIN`` and
resolved by ``src.models.registry``.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from src.config import VALID_DOMAINS

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CONFIG_DIR = REPO_ROOT / "config"


class DomainError(ValueError):
    """Base class for domain loading problems."""


class UnknownDomainError(DomainError):
    """Requested domain name is not one of the supported domains."""


class DomainConfigError(DomainError):
    """A domain config file is missing or invalid."""


@dataclass(frozen=True)
class _DomainSpec:
    prompts_file: str
    models_file: str
    corpus_dir: str
    audit: Optional[str]  # "insurance" | "healthcare" | "finance" | None
    retrieval_key: Optional[str]  # section of the models YAML with retrieval params
    description: str


_SPECS: Dict[str, _DomainSpec] = {
    "general": _DomainSpec(
        "prompts.yaml", "models.yaml", "data/processed", None, None,
        "Generic document Q&A (default).",
    ),
    "insurance": _DomainSpec(
        "insurance_prompts.yaml", "insurance_models.yaml", "data/insurance",
        "insurance", "insurance_retrieval",
        "Insurance policies, claims, underwriting and state compliance notes.",
    ),
    "healthcare": _DomainSpec(
        "healthcare_prompts.yaml", "healthcare_models.yaml", "data/healthcare",
        "healthcare", "healthcare_defaults",
        "Informational healthcare assistant (synthetic sample data).",
    ),
    "finance": _DomainSpec(
        "finance_prompts.yaml", "finance_models.yaml", "data/finance",
        "finance", "retrieval_tuning",
        "Financial services research (regulations, compliance, products).",
    ),
}


@dataclass
class DomainProfile:
    """Everything the runtime needs to know about one domain."""

    name: str
    description: str
    system_prompt: str
    few_shot_examples: List[dict] = field(default_factory=list)
    task_prompts: Dict[str, dict] = field(default_factory=dict)
    response_format: Dict[str, Any] = field(default_factory=dict)
    escalation_keywords: List[str] = field(default_factory=list)
    medical_disclaimer_text: Optional[str] = None
    preferred_model: Optional[str] = None
    fallback_models: List[str] = field(default_factory=list)
    embedding_models: List[str] = field(default_factory=list)
    retrieval: Dict[str, Any] = field(default_factory=dict)
    temperature: Optional[float] = None
    corpus_dir: Path = Path("data/processed")
    audit_logger: Optional[str] = None
    prompts_path: Optional[Path] = None
    models_path: Optional[Path] = None

    @property
    def emergency_escalation_enabled(self) -> bool:
        return bool(self.escalation_keywords) and bool(
            self.retrieval.get("enable_emergency_escalation_check", False)
        )

    def to_summary(self) -> dict:
        """JSON-safe summary for the API (no prompt text)."""
        return {
            "name": self.name,
            "description": self.description,
            "preferred_model": self.preferred_model,
            "fallback_models": list(self.fallback_models),
            "corpus_dir": str(self.corpus_dir),
            "audit_logger": self.audit_logger,
            "task_prompts": sorted(self.task_prompts),
            "retrieval": dict(self.retrieval),
        }


def _read_yaml(path: Path, what: str) -> dict:
    if not path.is_file():
        raise DomainConfigError(f"{what} file not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise DomainConfigError(f"{what} file {path} is not valid YAML: {e}") from e
    if not isinstance(data, dict):
        raise DomainConfigError(f"{what} file {path} must contain a YAML mapping at the top level")
    return data


def _base_model_key(key: str, domain: str) -> str:
    suffix = f"_{domain}"
    return key[: -len(suffix)] if key.endswith(suffix) and len(key) > len(suffix) else key


def _load_profile(name: str, config_dir: Path) -> DomainProfile:
    spec = _SPECS[name]
    prompts_path = config_dir / spec.prompts_file
    models_path = config_dir / spec.models_file
    prompts = _read_yaml(prompts_path, "Prompts")
    models = _read_yaml(models_path, "Models")

    system_prompt = prompts.get("system_prompt")
    if not isinstance(system_prompt, str) or not system_prompt.strip():
        raise DomainConfigError(f"{prompts_path} must define a non-empty 'system_prompt'")

    examples = prompts.get("few_shot_examples") or []
    if not isinstance(examples, list):
        raise DomainConfigError(f"{prompts_path}: 'few_shot_examples' must be a list")
    for i, ex in enumerate(examples):
        if not isinstance(ex, dict) or not all(k in ex for k in ("query", "context", "answer")):
            raise DomainConfigError(
                f"{prompts_path}: few_shot_examples[{i}] needs 'query', 'context' and 'answer'"
            )

    task_prompts = prompts.get("task_prompts") or {}
    if not isinstance(task_prompts, dict):
        raise DomainConfigError(f"{prompts_path}: 'task_prompts' must be a mapping")

    llm_models = models.get("llm_models") or {}
    if not isinstance(llm_models, dict):
        raise DomainConfigError(f"{models_path}: 'llm_models' must be a mapping")
    model_keys = [_base_model_key(k, name) for k in llm_models]

    embeddings = models.get("embedding_models") or {}
    embedding_keys = [_base_model_key(k, name) for k in embeddings] if isinstance(embeddings, dict) else []

    retrieval: dict = {}
    if spec.retrieval_key:
        section = models.get(spec.retrieval_key) or {}
        if not isinstance(section, dict):
            raise DomainConfigError(f"{models_path}: '{spec.retrieval_key}' must be a mapping")
        retrieval = dict(section)

    temperature: Optional[float] = None
    if "llm_temperature" in retrieval:
        temperature = retrieval["llm_temperature"]
    else:
        for data in llm_models.values():
            if isinstance(data, dict) and "temperature" in data:
                temperature = data["temperature"]
                break
    if temperature is not None and not isinstance(temperature, (int, float)):
        raise DomainConfigError(f"{models_path}: temperature must be a number, got {temperature!r}")

    return DomainProfile(
        name=name,
        description=spec.description,
        system_prompt=system_prompt.strip(),
        few_shot_examples=examples,
        task_prompts=task_prompts,
        response_format=prompts.get("response_format") or {},
        escalation_keywords=[str(k) for k in (prompts.get("escalation_keywords") or [])],
        medical_disclaimer_text=(prompts.get("medical_disclaimer_text") or "").strip() or None,
        preferred_model=model_keys[0] if model_keys else None,
        fallback_models=model_keys[1:],
        embedding_models=embedding_keys,
        retrieval=retrieval,
        temperature=float(temperature) if temperature is not None else None,
        corpus_dir=REPO_ROOT / spec.corpus_dir,
        audit_logger=spec.audit,
        prompts_path=prompts_path,
        models_path=models_path,
    )


_cache: Dict[tuple, DomainProfile] = {}
_lock = threading.Lock()


def list_domains() -> List[str]:
    """Supported domain names, in a stable order."""
    return list(VALID_DOMAINS)


def get_domain_profile(
    name: str, config_dir: Optional[Union[Path, str]] = None
) -> DomainProfile:
    """Load (and cache) the profile for ``name``.

    Raises UnknownDomainError for an unsupported name and DomainConfigError
    for missing/invalid config files.
    """
    normalized = (name or "").strip().lower()
    if normalized not in _SPECS:
        raise UnknownDomainError(
            f"Unknown domain '{name}'. Supported domains: {', '.join(list_domains())}"
        )
    directory = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR
    key = (normalized, str(directory))
    with _lock:
        if key not in _cache:
            _cache[key] = _load_profile(normalized, directory)
        return _cache[key]


def clear_domain_cache() -> None:
    with _lock:
        _cache.clear()
