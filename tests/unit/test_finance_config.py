"""Tests for the finance RAG pipeline configuration and sample data.

Covers:
- config/finance_models.yaml, config/finance_prompts.yaml,
  config/regulations.yaml parse as valid YAML with expected top-level keys.
- Sample data files under data/finance/ exist, are valid JSON, and contain
  the required "SAMPLE DATA" disclaimer.
"""

import json
import os

import pytest
import yaml

CONFIG_DIR = "config"
FINANCE_DATA_DIR = os.path.join("data", "finance")


@pytest.fixture
def finance_models_config():
    with open(os.path.join(CONFIG_DIR, "finance_models.yaml"), "r") as f:
        return yaml.safe_load(f)


@pytest.fixture
def finance_prompts_config():
    with open(os.path.join(CONFIG_DIR, "finance_prompts.yaml"), "r") as f:
        return yaml.safe_load(f)


@pytest.fixture
def regulations_config():
    with open(os.path.join(CONFIG_DIR, "regulations.yaml"), "r") as f:
        return yaml.safe_load(f)


# --- config/finance_models.yaml ---


def test_finance_models_is_valid_yaml(finance_models_config):
    assert finance_models_config is not None
    assert isinstance(finance_models_config, dict)


def test_finance_models_has_expected_top_level_keys(finance_models_config):
    for key in ("llm_models", "embedding_models", "reranker_models", "retrieval_tuning"):
        assert key in finance_models_config, f"Missing top-level key: {key}"


def test_finance_models_llm_entries_have_required_fields(finance_models_config):
    llm_models = finance_models_config["llm_models"]
    assert len(llm_models) > 0
    for model_id, model in llm_models.items():
        assert "name" in model, f"{model_id} missing 'name'"
        assert "context_length" in model, f"{model_id} missing 'context_length'"
        assert "parameters" in model, f"{model_id} missing 'parameters'"


def test_finance_models_retrieval_tuning_reasonable(finance_models_config):
    tuning = finance_models_config["retrieval_tuning"]
    assert tuning["chunk_size"] > 0
    assert tuning["top_k_documents"] > 0
    assert 0 <= tuning["similarity_threshold"] <= 1


# --- config/finance_prompts.yaml ---


def test_finance_prompts_is_valid_yaml(finance_prompts_config):
    assert finance_prompts_config is not None
    assert isinstance(finance_prompts_config, dict)


def test_finance_prompts_has_expected_top_level_keys(finance_prompts_config):
    for key in (
        "system_prompt",
        "financial_terminology",
        "few_shot_examples",
        "response_format",
        "disclaimer",
    ):
        assert key in finance_prompts_config, f"Missing top-level key: {key}"


def test_finance_prompts_terminology_covers_expected_categories(finance_prompts_config):
    terminology = finance_prompts_config["financial_terminology"]
    for category in (
        "regulatory_bodies",
        "compliance_terms",
        "financial_products",
        "reporting_standards",
        "risk_terms",
    ):
        assert category in terminology, f"Missing terminology category: {category}"
        assert len(terminology[category]) > 0


def test_finance_prompts_has_multiple_few_shot_examples(finance_prompts_config):
    examples = finance_prompts_config["few_shot_examples"]
    assert isinstance(examples, list)
    assert len(examples) >= 3
    for example in examples:
        assert "query" in example
        assert "context" in example
        assert "answer" in example


def test_finance_prompts_system_prompt_mentions_no_advice(finance_prompts_config):
    system_prompt = finance_prompts_config["system_prompt"].lower()
    assert "advice" in system_prompt


# --- config/regulations.yaml ---


def test_regulations_is_valid_yaml(regulations_config):
    assert regulations_config is not None
    assert isinstance(regulations_config, dict)


def test_regulations_has_expected_top_level_keys(regulations_config):
    for key in (
        "regulatory_bodies",
        "regulatory_topics",
        "reporting_standards",
        "disclaimer",
    ):
        assert key in regulations_config, f"Missing top-level key: {key}"


def test_regulations_bodies_include_core_regulators(regulations_config):
    bodies = regulations_config["regulatory_bodies"]
    for expected in ("sec", "finra", "occ", "fincen"):
        assert expected in bodies, f"Missing regulatory body: {expected}"
        assert "name" in bodies[expected]
        assert "abbreviation" in bodies[expected]


def test_regulations_disclaimer_present_and_non_authoritative(regulations_config):
    disclaimer = regulations_config["disclaimer"].lower()
    assert "sample" in disclaimer or "fictional" in disclaimer
    assert "not" in disclaimer


# --- data/finance/ sample data ---

EXPECTED_FINANCE_DATA_FILES = {
    "regulation_summaries.json": "regulation_summaries",
    "product_prospectuses.json": "prospectuses",
    "trading_rules.json": "trading_rules",
    "compliance_policies.json": "compliance_policies",
    "finance_qa.json": "qa_pairs",
}

DISCLAIMER_MARKER = "SAMPLE DATA"


def test_finance_data_directory_exists():
    assert os.path.isdir(FINANCE_DATA_DIR)


@pytest.mark.parametrize("filename", sorted(EXPECTED_FINANCE_DATA_FILES.keys()))
def test_finance_data_file_exists(filename):
    path = os.path.join(FINANCE_DATA_DIR, filename)
    assert os.path.isfile(path), f"Missing sample data file: {path}"


@pytest.mark.parametrize("filename", sorted(EXPECTED_FINANCE_DATA_FILES.keys()))
def test_finance_data_file_is_valid_json(filename):
    path = os.path.join(FINANCE_DATA_DIR, filename)
    with open(path, "r") as f:
        data = json.load(f)
    assert isinstance(data, dict)


@pytest.mark.parametrize("filename", sorted(EXPECTED_FINANCE_DATA_FILES.keys()))
def test_finance_data_file_has_disclaimer(filename):
    path = os.path.join(FINANCE_DATA_DIR, filename)
    with open(path, "r") as f:
        data = json.load(f)
    assert "disclaimer" in data, f"{filename} missing top-level 'disclaimer' key"
    assert DISCLAIMER_MARKER in data["disclaimer"]


@pytest.mark.parametrize(
    "filename,list_key", sorted(EXPECTED_FINANCE_DATA_FILES.items())
)
def test_finance_data_file_has_expected_records(filename, list_key):
    path = os.path.join(FINANCE_DATA_DIR, filename)
    with open(path, "r") as f:
        data = json.load(f)
    assert list_key in data, f"{filename} missing expected key: {list_key}"
    records = data[list_key]
    assert isinstance(records, list)
    assert len(records) > 0
    for record in records:
        assert "id" in record
        assert "content" in record or "answer" in record


def test_finance_qa_has_at_least_five_examples():
    path = os.path.join(FINANCE_DATA_DIR, "finance_qa.json")
    with open(path, "r") as f:
        data = json.load(f)
    assert len(data["qa_pairs"]) >= 5
