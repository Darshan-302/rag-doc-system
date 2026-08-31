"""Lightweight audit-logging hook for regulated (finance) query access.

This is a design-reference implementation, not a certified compliance
control. It illustrates the shape of an audit trail suitable for later
review against real regulatory record-keeping requirements (e.g., SEC/FINRA
record-retention rules, SOX/SOC2 change- and access-logging expectations).
A real deployment must have this reviewed by qualified compliance/security
engineers before relying on it for regulatory purposes.

Design goals:
- Append-only, structured (JSON Lines) log entries.
- Never write the full query text or full document content that could
  contain sensitive financial PII - only metadata plus a short, masked
  preview.
- Fail safe: a logging failure must never raise into the calling request
  path (compliance logging should not be able to take down user-facing
  functionality), but it is surfaced via a bool return value the caller can
  check/alert on.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Very small set of illustrative PII-ish patterns to mask in the logged
# preview text. This is NOT a substitute for a real PII/PHI detection engine.
_ACCOUNT_NUMBER_RE = re.compile(r"\b\d{6,17}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


def mask_sensitive_text(text: str, preview_chars: int = 120) -> str:
    """Return a short, masked preview of ``text`` safe to write to an audit log.

    Long numeric sequences (candidate account numbers) and SSN-shaped
    sequences are replaced with a masked placeholder that keeps only the
    last 4 digits, then the preview is truncated to ``preview_chars``.
    """
    if text is None:
        return ""

    def _mask_account(match: "re.Match[str]") -> str:
        digits = match.group(0)
        return f"***{digits[-4:]}"

    masked = _SSN_RE.sub("***-**-****", text)
    masked = _ACCOUNT_NUMBER_RE.sub(_mask_account, masked)

    if len(masked) > preview_chars:
        masked = masked[:preview_chars].rstrip() + "..."
    return masked


@dataclass
class FinanceAuditLogger:
    """Append-only JSON-lines audit logger for finance RAG query access.

    Example:
        logger = FinanceAuditLogger(log_path="logs/finance_audit.log")
        logger.log_query_access(
            user_id="analyst_42",
            tenant_id="acme-finance",
            role="analyst",
            query_text="What is the KYC policy for new accounts?",
            document_ids=["policy_template_001"],
        )
    """

    log_path: str = "logs/finance_audit.log"
    enabled: bool = True
    _write_failures: int = field(default=0, init=False, repr=False)

    def log_query_access(
        self,
        *,
        user_id: str,
        tenant_id: str,
        role: str,
        query_text: str,
        document_ids: Optional[list] = None,
        action: str = "query",
    ) -> bool:
        """Record one audit entry. Returns True on success, False on failure.

        Never raises - a logging failure must not break the request path.
        """
        if not self.enabled:
            return True

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "user_id": user_id,
            "tenant_id": tenant_id,
            "role": role,
            "query_preview": mask_sensitive_text(query_text),
            "document_ids": document_ids or [],
        }

        try:
            path = Path(self.log_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, sort_keys=True) + "\n")
            return True
        except OSError:
            self._write_failures += 1
            return False

    @property
    def write_failures(self) -> int:
        """Count of failed log writes since this logger was created.

        A real deployment should alert on this being non-zero, since a
        silent audit-log failure is itself a compliance concern.
        """
        return self._write_failures
