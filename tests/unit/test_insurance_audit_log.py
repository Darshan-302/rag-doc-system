"""Test the lightweight insurance audit-logging hook
(src/security/insurance_audit_log.py)."""

import json
import os

from src.security.insurance_audit_log import (
    is_audit_logging_enabled,
    log_document_access,
)


def test_audit_logging_disabled_by_default(monkeypatch):
    """Test that audit logging is disabled unless explicitly enabled."""
    monkeypatch.delenv("INSURANCE_AUDIT_LOGGING_ENABLED", raising=False)
    assert is_audit_logging_enabled() is False


def test_log_document_access_noop_when_disabled(monkeypatch, tmp_path):
    """Test that log_document_access returns None and writes nothing when disabled."""
    monkeypatch.setenv("INSURANCE_AUDIT_LOGGING_ENABLED", "false")
    log_path = tmp_path / "audit.log"
    monkeypatch.setenv("INSURANCE_AUDIT_LOG_PATH", str(log_path))

    result = log_document_access(
        tenant_id="test-tenant",
        action="policy.lookup",
        document_id="policy_ins_001",
        user_id="tester",
    )

    assert result is None
    assert not log_path.exists()


def test_log_document_access_writes_event_when_enabled(monkeypatch, tmp_path):
    """Test that enabling audit logging writes a JSON event to the configured path."""
    monkeypatch.setenv("INSURANCE_AUDIT_LOGGING_ENABLED", "true")
    log_path = tmp_path / "audit.log"
    monkeypatch.setenv("INSURANCE_AUDIT_LOG_PATH", str(log_path))

    event = log_document_access(
        tenant_id="test-tenant",
        action="policy.lookup",
        document_id="policy_ins_001",
        user_id="tester",
        details="unit test",
    )

    assert event is not None
    assert event.tenant_id == "test-tenant"
    assert event.action == "policy.lookup"

    assert log_path.exists()
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["tenant_id"] == "test-tenant"
    assert record["document_id"] == "policy_ins_001"
    assert "timestamp" in record
