"""Runtime industry-domain selection (general, insurance, healthcare, finance)."""

from src.domains.audit import log_query_access
from src.domains.profile import (
    DomainConfigError,
    DomainError,
    DomainProfile,
    UnknownDomainError,
    clear_domain_cache,
    get_domain_profile,
    list_domains,
)
from src.domains.prompts import build_prompt, check_escalation, finalize_answer

__all__ = [
    "DomainConfigError",
    "DomainError",
    "DomainProfile",
    "UnknownDomainError",
    "build_prompt",
    "check_escalation",
    "clear_domain_cache",
    "finalize_answer",
    "get_domain_profile",
    "list_domains",
    "log_query_access",
]
