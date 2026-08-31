"""Lightweight, illustrative HIPAA-style audit logging hook.

DESIGN NOTE (read before using in anything real):
    This module is a documentation/reference implementation shipped as part
    of the healthcare RAG feature (see docs/HEALTHCARE_RAG_GUIDE.md, section
    7 "HIPAA Audit Logging"). It demonstrates the *shape* of an audit event
    for PHI-adjacent actions (queries, document views, uploads, exports).

    It is intentionally simple: it appends structured JSON lines to a local
    file. It is NOT a production-grade, tamper-evident audit trail. A real
    deployment handling actual PHI should write audit events to a
    centralized, access-controlled, write-once/tamper-evident store (e.g. a
    SIEM or an append-only cloud logging service), and should have that
    design reviewed by qualified security/compliance personnel.

    Nothing in this module inspects, redacts, or validates PHI. Callers are
    responsible for ensuring `resource_id` and other fields passed in do not
    themselves contain PHI (e.g. log a document ID, not a patient name).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


DEFAULT_AUDIT_LOG_PATH = "./logs/healthcare_audit.log"

# Actions this hook expects to be used for. Not an enforced/validated enum --
# just documentation of the intended vocabulary.
KNOWN_ACTIONS = (
    "query",
    "document_view",
    "document_upload",
    "document_delete",
    "export",
    "consent_update",
    "access_denied",
)


@dataclass
class AuditEvent:
    """A single HIPAA-style audit trail entry.

    Fields intentionally mirror the minimum fields called out in
    docs/HEALTHCARE_RAG_GUIDE.md section 7:
    timestamp, actor, action, resource, outcome, source.
    """

    actor_id: str
    action: str
    resource_id: Optional[str] = None
    outcome: str = "success"
    role: Optional[str] = None
    source_ip: Optional[str] = None
    reason: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "actor_id": self.actor_id,
            "role": self.role,
            "action": self.action,
            "resource_id": self.resource_id,
            "outcome": self.outcome,
            "source_ip": self.source_ip,
            "reason": self.reason,
        }


def log_phi_access(
    actor_id: str,
    action: str,
    resource_id: Optional[str] = None,
    outcome: str = "success",
    role: Optional[str] = None,
    source_ip: Optional[str] = None,
    reason: Optional[str] = None,
    log_path: Optional[str] = None,
) -> AuditEvent:
    """Record an illustrative audit log entry for a PHI-adjacent action.

    This appends one JSON line per call to `log_path` (creating parent
    directories as needed). It does not raise on I/O errors becoming a
    reason to block the underlying action in this reference implementation;
    a real deployment should decide explicitly whether a failed audit write
    should fail the associated request (many compliance regimes expect
    "fail closed" for audit logging of sensitive actions).

    Args:
        actor_id: Identifier of the user/service performing the action.
            Should be an internal ID, not PHI.
        action: One of KNOWN_ACTIONS (not enforced, just documented).
        resource_id: Identifier of the resource touched (e.g. document ID,
            query ID). Callers must not pass PHI content here.
        outcome: "success" or "failure" (or a more specific failure reason
            code).
        role: The actor's role at the time of the action, if known.
        source_ip: Originating IP/service, for forensic purposes.
        reason: Free-text reason, e.g. for access-denied events. Callers
            must not pass PHI content here.
        log_path: Override the destination file. Defaults to
            HIPAA_AUDIT_LOG_PATH env var, then DEFAULT_AUDIT_LOG_PATH.

    Returns:
        The AuditEvent that was written (or attempted).
    """
    event = AuditEvent(
        actor_id=actor_id,
        action=action,
        resource_id=resource_id,
        outcome=outcome,
        role=role,
        source_ip=source_ip,
        reason=reason,
    )

    destination = log_path or os.environ.get(
        "HIPAA_AUDIT_LOG_PATH", DEFAULT_AUDIT_LOG_PATH
    )
    path = Path(destination)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), sort_keys=True) + "\n")
    except OSError:
        # Reference implementation: swallow I/O errors rather than crash the
        # caller. See the module docstring -- a real deployment should make
        # an explicit fail-open/fail-closed decision here.
        pass

    return event


def read_audit_events(log_path: Optional[str] = None) -> list[dict]:
    """Read back audit events from a local audit log file (helper for tests
    and local development/debugging only -- not intended as a query
    interface for a production audit store)."""
    destination = log_path or os.environ.get(
        "HIPAA_AUDIT_LOG_PATH", DEFAULT_AUDIT_LOG_PATH
    )
    path = Path(destination)
    if not path.exists():
        return []
    events = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            events.append(json.loads(line))
    return events
