"""Tests for the lightweight, illustrative healthcare audit logging hook."""

import json
import os

from src.security.healthcare_audit_log import log_phi_access, read_audit_events


def test_log_phi_access_writes_expected_fields(tmp_path):
    log_path = str(tmp_path / "audit.log")

    event = log_phi_access(
        actor_id="clinician_123",
        action="query",
        resource_id="doc_synth_001",
        outcome="success",
        role="clinician",
        log_path=log_path,
    )

    assert event.actor_id == "clinician_123"
    assert event.action == "query"
    assert os.path.isfile(log_path)

    events = read_audit_events(log_path=log_path)
    assert len(events) == 1
    assert events[0]["actor_id"] == "clinician_123"
    assert events[0]["action"] == "query"
    assert events[0]["resource_id"] == "doc_synth_001"
    assert "timestamp" in events[0]


def test_log_phi_access_appends_multiple_events(tmp_path):
    log_path = str(tmp_path / "audit.log")

    log_phi_access(actor_id="user_a", action="query", log_path=log_path)
    log_phi_access(actor_id="user_b", action="document_view", log_path=log_path)

    events = read_audit_events(log_path=log_path)
    assert len(events) == 2
    assert events[0]["actor_id"] == "user_a"
    assert events[1]["actor_id"] == "user_b"


def test_log_file_contains_valid_json_lines(tmp_path):
    log_path = str(tmp_path / "audit.log")
    log_phi_access(actor_id="user_a", action="query", log_path=log_path)

    with open(log_path, "r", encoding="utf-8") as f:
        lines = [line for line in f.read().splitlines() if line.strip()]

    assert len(lines) == 1
    parsed = json.loads(lines[0])
    assert parsed["actor_id"] == "user_a"


def test_read_audit_events_returns_empty_list_for_missing_file(tmp_path):
    missing_path = str(tmp_path / "does_not_exist.log")
    assert read_audit_events(log_path=missing_path) == []
