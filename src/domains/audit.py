"""Routes query-access events to the active domain's existing audit hook.

Reuses the opt-in flags already defined by the hooks / env examples:

* insurance  - INSURANCE_AUDIT_LOGGING_ENABLED, INSURANCE_AUDIT_LOG_PATH
* healthcare - HIPAA_AUDIT_LOGGING_ENABLED, HIPAA_AUDIT_LOG_PATH
* finance    - FINANCE_AUDIT_LOGGING_ENABLED, FINANCE_AUDIT_LOG_PATH

These are read from the process environment at call time. All default to off.
Raw query text is never passed to the insurance/healthcare hooks; the finance
hook receives it because it only stores its own masked, truncated preview.
Audit failures never propagate into the request path.
"""

from __future__ import annotations

import logging
import os
from typing import Iterable, Optional

from src.domains.profile import DomainProfile

logger = logging.getLogger(__name__)

_TRUE = ("1", "true", "yes")


def _flag(name: str) -> bool:
    return os.environ.get(name, "false").strip().lower() in _TRUE


def log_query_access(
    profile: DomainProfile,
    tenant_id: str,
    query: str,
    document_ids: Optional[Iterable[str]] = None,
) -> bool:
    """Record a query-access event. Returns True if an event was written."""
    kind = profile.audit_logger
    if not kind:
        return False
    ids = [str(d) for d in (document_ids or [])]
    try:
        if kind == "insurance":
            from src.security import insurance_audit_log as hook

            return hook.log_document_access(
                tenant_id=tenant_id,
                action="query",
                document_id=",".join(ids) or None,
            ) is not None

        if kind == "healthcare":
            if not _flag("HIPAA_AUDIT_LOGGING_ENABLED"):
                return False
            from src.security import healthcare_audit_log as hook

            hook.log_phi_access(
                actor_id=f"tenant:{tenant_id}",
                action="query",
                resource_id=",".join(ids) or None,
            )
            return True

        if kind == "finance":
            if not _flag("FINANCE_AUDIT_LOGGING_ENABLED"):
                return False
            from src.compliance.audit_log import FinanceAuditLogger

            audit = FinanceAuditLogger(
                log_path=os.environ.get("FINANCE_AUDIT_LOG_PATH", "logs/finance_audit.log")
            )
            return audit.log_query_access(
                user_id="anonymous",
                tenant_id=tenant_id,
                role="unknown",
                query_text=query,
                document_ids=ids,
            )
    except Exception as e:  # audit problems must not break queries
        logger.warning("Audit logging failed for domain '%s': %s", profile.name, e)
    return False
