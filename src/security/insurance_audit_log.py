"""Lightweight audit-logging hook for insurance document access.

This is a small, self-contained utility that records who accessed which insurance
document/policy/claim record and when. It is intended as a *design reference and
minimal working example* for the audit-logging requirement described in
docs/INSURANCE_RAG_GUIDE.md ("Compliance Features" section), not a complete
compliance/audit subsystem.

For a production deployment, route these events into the existing `AuditLog`
table (see `src/db/models.py`) or a centralized log pipeline instead of (or in
addition to) the local file used here, and consult qualified compliance counsel
on what an actual audit trail must capture for your jurisdiction and product line.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("insurance.audit")


@dataclass
class InsuranceAuditEvent:
    """A single document/record access event for compliance logging.

    Fields intentionally mirror the shape of `src.db.models.AuditLog` so this
    lightweight hook can be swapped for a database-backed implementation later
    without changing callers.
    """

    tenant_id: str
    action: str  # e.g. "document.viewed", "policy.lookup", "claim.status_query"
    document_id: Optional[str] = None
    user_id: Optional[str] = None
    details: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()


def is_audit_logging_enabled() -> bool:
    """Whether the audit-log hook is enabled, via INSURANCE_AUDIT_LOGGING_ENABLED."""
    return os.environ.get("INSURANCE_AUDIT_LOGGING_ENABLED", "false").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def _audit_log_path() -> Path:
    return Path(os.environ.get("INSURANCE_AUDIT_LOG_PATH", "logs/insurance_audit.log"))


def log_document_access(
    tenant_id: str,
    action: str,
    document_id: Optional[str] = None,
    user_id: Optional[str] = None,
    details: Optional[str] = None,
) -> Optional[InsuranceAuditEvent]:
    """Record an insurance document/record access event.

    No-ops (besides a debug log) unless INSURANCE_AUDIT_LOGGING_ENABLED is set,
    so this hook is safe to call from request-handling code without requiring
    extra setup in local development.

    Returns the event that was recorded, or None if logging is disabled.
    """
    event = InsuranceAuditEvent(
        tenant_id=tenant_id,
        action=action,
        document_id=document_id,
        user_id=user_id,
        details=details,
    )

    if not is_audit_logging_enabled():
        logger.debug("Insurance audit logging disabled; skipping event: %s", event.action)
        return None

    path = _audit_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(event)) + "\n")

    logger.info("Insurance audit event recorded: %s (tenant=%s)", event.action, event.tenant_id)
    return event
