"""Tests for runtime domain selection (src/domains, DOMAIN setting, API)."""

import json
import os
import re
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.config import Settings, VALID_DOMAINS
from src.domains import (
    DomainConfigError,
    UnknownDomainError,
    build_prompt,
    check_escalation,
    clear_domain_cache,
    finalize_answer,
    get_domain_profile,
    list_domains,
    log_query_access,
)
from src.domains.profile import DEFAULT_CONFIG_DIR

DOMAINS = ["general", "insurance", "healthcare", "finance"]


@pytest.fixture(autouse=True)
def _fresh_cache():
    clear_domain_cache()
    yield
    clear_domain_cache()


# --- loader -----------------------------------------------------------------

def test_list_domains():
    assert list_domains() == list(VALID_DOMAINS) == DOMAINS


@pytest.mark.parametrize("name", DOMAINS)
def test_each_domain_loads(name):
    p = get_domain_profile(name)
    assert p.name == name
    assert p.system_prompt
    assert p.few_shot_examples
    assert p.prompts_path.is_file() and p.models_path.is_file()
    assert p.corpus_dir.parent.name in ("data",) or p.corpus_dir.name == "processed"


def test_profiles_are_cached_and_name_normalized():
    assert get_domain_profile("finance") is get_domain_profile(" Finance ")


def test_model_mapping():
    fin = get_domain_profile("finance")
    assert fin.preferred_model == "qwen_32b"  # qwen_32b_finance -> base key
    assert "mistral" in fin.fallback_models
    assert fin.temperature == 0.2
    assert fin.retrieval["top_k_documents"] == 8
    assert get_domain_profile("insurance").retrieval["top_k_documents"] == 6
    hc = get_domain_profile("healthcare")
    assert hc.temperature == 0.2 and hc.emergency_escalation_enabled
    assert get_domain_profile("general").temperature is None


def test_audit_logger_per_domain():
    assert {n: get_domain_profile(n).audit_logger for n in DOMAINS} == {
        "general": None, "insurance": "insurance", "healthcare": "healthcare", "finance": "finance",
    }


def test_unknown_domain():
    with pytest.raises(UnknownDomainError, match="Supported domains"):
        get_domain_profile("retail")


def test_missing_file(tmp_path):
    with pytest.raises(DomainConfigError, match="not found"):
        get_domain_profile("insurance", config_dir=tmp_path)


def _copy_config(tmp_path):
    dst = tmp_path / "config"
    shutil.copytree(DEFAULT_CONFIG_DIR, dst)
    return dst


def test_invalid_yaml(tmp_path):
    cfg = _copy_config(tmp_path)
    (cfg / "finance_prompts.yaml").write_text("system_prompt: [unclosed")
    with pytest.raises(DomainConfigError, match="not valid YAML"):
        get_domain_profile("finance", config_dir=cfg)


def test_missing_system_prompt(tmp_path):
    cfg = _copy_config(tmp_path)
    (cfg / "finance_prompts.yaml").write_text("few_shot_examples: []\n")
    with pytest.raises(DomainConfigError, match="system_prompt"):
        get_domain_profile("finance", config_dir=cfg)


def test_bad_example(tmp_path):
    cfg = _copy_config(tmp_path)
    (cfg / "general_x.yaml").write_text("")
    (cfg / "prompts.yaml").write_text("system_prompt: hi\nfew_shot_examples:\n  - query: q\n")
    with pytest.raises(DomainConfigError, match="few_shot_examples"):
        get_domain_profile("general", config_dir=cfg)


# --- prompt building ----------------------------------------------------------

@pytest.mark.parametrize("name", DOMAINS)
def test_prompt_contains_query_context_no_placeholders(name):
    p = get_domain_profile(name)
    prompt = build_prompt(p, "UNIQUE-QUERY-123 {braces}", "UNIQUE-CONTEXT-456 {x}")
    assert "UNIQUE-QUERY-123 {braces}" in prompt
    assert "UNIQUE-CONTEXT-456 {x}" in prompt
    assert p.system_prompt in prompt
    assert prompt.rstrip().endswith("Answer:")
    for ph in ("{context}", "{query}", "{question}", "{documents}", "%s", "{{"):
        assert ph not in prompt


def test_healthcare_safety_text():
    prompt = build_prompt(get_domain_profile("healthcare"), "q", "c")
    assert "not a substitute for professional medical advice" in prompt
    assert "does not provide medical" in prompt.replace("\n", " ") or "do not provide medical" in prompt.replace("\n", " ")
    assert "emergency" in prompt.lower()


def test_finance_safety_text():
    prompt = build_prompt(get_domain_profile("finance"), "q", "c")
    flat = re.sub(r"\s+", " ", prompt)
    assert "investment, legal, or tax advice" in flat
    assert "account ending 4321" in flat
    assert "Never fabricate regulatory citations" in flat


def test_insurance_safety_text():
    flat = re.sub(r"\s+", " ", build_prompt(get_domain_profile("insurance"), "q", "c"))
    assert "do not present your answer as legal advice" in flat
    assert "Never invent a policy number" in flat


def test_task_prompt():
    p = get_domain_profile("insurance")
    assert "Classify the following insurance text" in build_prompt(p, "q", "c", task="coverage_type_classification")
    with pytest.raises(KeyError):
        build_prompt(p, "q", "c", task="nope")


def test_healthcare_escalation_and_disclaimer():
    p = get_domain_profile("healthcare")
    resp = check_escalation(p, "I have CHEST PAIN right now")
    assert resp and "emergency" in resp.lower()
    assert check_escalation(p, "what is hypertension") is None
    assert check_escalation(get_domain_profile("finance"), "chest pain") is None
    out = finalize_answer(p, "Answer.")
    assert out.startswith("Answer.") and p.medical_disclaimer_text in out
    assert finalize_answer(p, out) == out  # idempotent
    assert finalize_answer(get_domain_profile("general"), "Answer.") == "Answer."


# --- settings -----------------------------------------------------------------

def test_settings_domain(monkeypatch):
    monkeypatch.delenv("DOMAIN", raising=False)
    assert Settings(_env_file=None).DOMAIN == "general"
    assert Settings(_env_file=None, DOMAIN=" Finance ").DOMAIN == "finance"
    assert Settings(_env_file=None, DOMAIN="").DOMAIN == "general"
    with pytest.raises(ValidationError, match="DOMAIN"):
        Settings(_env_file=None, DOMAIN="retail")


def test_settings_domain_from_env(monkeypatch):
    monkeypatch.setenv("DOMAIN", "healthcare")
    assert Settings(_env_file=None).DOMAIN == "healthcare"
    monkeypatch.setenv("DOMAIN", "bogus")
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


# --- audit wiring -------------------------------------------------------------

def _lines(path):
    return [json.loads(l) for l in Path(path).read_text().splitlines()]


def test_no_audit_for_general(tmp_path):
    assert log_query_access(get_domain_profile("general"), "t", "q", ["d"]) is False


def test_insurance_audit(tmp_path, monkeypatch):
    log = tmp_path / "ins.log"
    monkeypatch.setenv("INSURANCE_AUDIT_LOG_PATH", str(log))
    monkeypatch.delenv("INSURANCE_AUDIT_LOGGING_ENABLED", raising=False)
    p = get_domain_profile("insurance")
    assert log_query_access(p, "t1", "secret policy question", ["a", "b"]) is False
    assert not log.exists()
    monkeypatch.setenv("INSURANCE_AUDIT_LOGGING_ENABLED", "true")
    assert log_query_access(p, "t1", "secret policy question", ["a", "b"]) is True
    (ev,) = _lines(log)
    assert ev["tenant_id"] == "t1" and ev["action"] == "query" and ev["document_id"] == "a,b"
    assert "secret" not in log.read_text()


def test_healthcare_audit(tmp_path, monkeypatch):
    log = tmp_path / "hc.log"
    monkeypatch.setenv("HIPAA_AUDIT_LOG_PATH", str(log))
    monkeypatch.delenv("HIPAA_AUDIT_LOGGING_ENABLED", raising=False)
    p = get_domain_profile("healthcare")
    assert log_query_access(p, "t1", "patient John has chest pain", ["d1"]) is False
    assert not log.exists()
    monkeypatch.setenv("HIPAA_AUDIT_LOGGING_ENABLED", "true")
    assert log_query_access(p, "t1", "patient John has chest pain", ["d1"]) is True
    (ev,) = _lines(log)
    assert ev["action"] == "query" and ev["resource_id"] == "d1" and ev["actor_id"] == "tenant:t1"
    assert "John" not in log.read_text()


def test_finance_audit_masks(tmp_path, monkeypatch):
    log = tmp_path / "fin.log"
    monkeypatch.setenv("FINANCE_AUDIT_LOG_PATH", str(log))
    monkeypatch.delenv("FINANCE_AUDIT_LOGGING_ENABLED", raising=False)
    p = get_domain_profile("finance")
    assert log_query_access(p, "t1", "acct 123456789012", ["d1"]) is False
    monkeypatch.setenv("FINANCE_AUDIT_LOGGING_ENABLED", "true")
    assert log_query_access(p, "t1", "acct 123456789012", ["d1"]) is True
    (ev,) = _lines(log)
    assert ev["document_ids"] == ["d1"] and "123456789012" not in log.read_text()


def test_audit_failure_never_raises(tmp_path, monkeypatch):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setenv("INSURANCE_AUDIT_LOGGING_ENABLED", "true")
    monkeypatch.setenv("INSURANCE_AUDIT_LOG_PATH", str(blocker / "sub" / "a.log"))
    assert log_query_access(get_domain_profile("insurance"), "t", "q", []) is False


# --- API ------------------------------------------------------------------------

@pytest.fixture
def api(tmp_path, monkeypatch):
    import src.main as main

    (tmp_path / "data" / "processed").mkdir(parents=True)
    (tmp_path / "data" / "processed" / "rag_training_data.jsonl").write_text(
        json.dumps({"text": "kyc policy text", "source": "s", "document_id": "doc-1", "chunk_id": 1}) + "\n"
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FINANCE_AUDIT_LOGGING_ENABLED", "true")
    monkeypatch.setenv("FINANCE_AUDIT_LOG_PATH", str(tmp_path / "fin.log"))
    monkeypatch.setattr(main.settings, "DOMAIN", "general")
    prompts = []

    class FakeResp:
        status_code = 200
        def json(self):
            return {"response": "mock answer"}

    async def fake_post(url, json=None, **kw):
        prompts.append(json)
        return FakeResp()

    main._domain_pipelines.clear()
    main.rag_pipeline = main.RAGPipeline(domain="general")
    main._domain_pipelines["general"] = main.rag_pipeline
    original = main.RAGPipeline

    class Patched(original):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.client.post = fake_post

    main.RAGPipeline = Patched
    main.rag_pipeline.client.post = fake_post
    yield TestClient(main.app), prompts, tmp_path
    main.RAGPipeline = original
    main._domain_pipelines.clear()


def test_api_domains_and_health(api):
    client, _, _ = api
    r = client.get("/api/v1/domains")
    assert r.status_code == 200
    body = r.json()
    assert body["active"] == "general"
    assert [d["name"] for d in body["domains"]] == DOMAINS
    assert client.get("/health").json()["components"]["domain"] == "general"


def test_api_default_domain_query(api):
    client, prompts, _ = api
    r = client.post("/api/v1/t1/query", json={"query": "kyc"})
    assert r.status_code == 200 and r.json()["answer"] == "mock answer"
    assert "helpful healthcare and insurance assistant" in prompts[-1]["prompt"]


def test_api_per_request_domain(api):
    client, prompts, tmp = api
    r = client.post("/api/v1/t1/query", json={"query": "kyc acct 123456789012", "domain": "finance"})
    assert r.status_code == 200
    assert "investment, legal, or tax advice" in re.sub(r"\s+", " ", prompts[-1]["prompt"])
    assert prompts[-1]["temperature"] == 0.2
    (ev,) = _lines(tmp / "fin.log")
    assert ev["document_ids"] == ["doc-1"] and "123456789012" not in (tmp / "fin.log").read_text()


def test_api_healthcare_emergency_skips_llm(api):
    client, prompts, _ = api
    r = client.post("/api/v1/t1/query", json={"query": "chest pain kyc", "domain": "healthcare"})
    assert r.status_code == 200 and "emergency" in r.json()["answer"].lower()
    assert prompts == []


def test_api_healthcare_disclaimer_appended(api):
    client, _, _ = api
    r = client.post("/api/v1/t1/query", json={"query": "kyc", "domain": "healthcare"})
    assert "general educational purposes only" in r.json()["answer"]


def test_api_invalid_domain(api):
    client, _, _ = api
    r = client.post("/api/v1/t1/query", json={"query": "kyc", "domain": "retail"})
    assert r.status_code == 422
