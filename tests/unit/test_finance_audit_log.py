"""Tests for the lightweight finance compliance audit-logging hook."""

import json
import os

from src.compliance.audit_log import FinanceAuditLogger, mask_sensitive_text


def test_mask_sensitive_text_masks_ssn():
    masked = mask_sensitive_text("Customer SSN is 123-45-6789 on file.")
    assert "123-45-6789" not in masked
    assert "***-**-****" in masked


def test_mask_sensitive_text_masks_long_account_number():
    masked = mask_sensitive_text("Account number 1234567890123 was queried.")
    assert "1234567890123" not in masked
    assert "***0123" in masked


def test_mask_sensitive_text_truncates_long_text():
    long_text = "a" * 500
    masked = mask_sensitive_text(long_text, preview_chars=50)
    assert len(masked) <= 53  # 50 chars + "..."
    assert masked.endswith("...")


def test_mask_sensitive_text_handles_none():
    assert mask_sensitive_text(None) == ""


def test_finance_audit_logger_writes_json_lines_entry(tmp_path):
    log_path = tmp_path / "finance_audit.log"
    logger = FinanceAuditLogger(log_path=str(log_path))

    success = logger.log_query_access(
        user_id="analyst_42",
        tenant_id="acme-finance",
        role="analyst",
        query_text="What is the KYC policy for account 1234567890123?",
        document_ids=["policy_template_001"],
    )

    assert success is True
    assert log_path.exists()

    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 1

    entry = json.loads(lines[0])
    assert entry["user_id"] == "analyst_42"
    assert entry["tenant_id"] == "acme-finance"
    assert entry["role"] == "analyst"
    assert entry["document_ids"] == ["policy_template_001"]
    # The raw account number must not appear in the logged preview.
    assert "1234567890123" not in entry["query_preview"]
    assert "timestamp" in entry


def test_finance_audit_logger_appends_multiple_entries(tmp_path):
    log_path = tmp_path / "finance_audit.log"
    logger = FinanceAuditLogger(log_path=str(log_path))

    logger.log_query_access(
        user_id="u1", tenant_id="t1", role="analyst", query_text="q1"
    )
    logger.log_query_access(
        user_id="u2", tenant_id="t1", role="compliance_officer", query_text="q2"
    )

    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 2


def test_finance_audit_logger_disabled_does_not_write(tmp_path):
    log_path = tmp_path / "finance_audit.log"
    logger = FinanceAuditLogger(log_path=str(log_path), enabled=False)

    success = logger.log_query_access(
        user_id="u1", tenant_id="t1", role="analyst", query_text="q1"
    )

    assert success is True
    assert not log_path.exists()


def test_finance_audit_logger_creates_parent_directories(tmp_path):
    log_path = tmp_path / "nested" / "dir" / "finance_audit.log"
    logger = FinanceAuditLogger(log_path=str(log_path))

    logger.log_query_access(
        user_id="u1", tenant_id="t1", role="analyst", query_text="q1"
    )

    assert log_path.exists()
    assert logger.write_failures == 0
