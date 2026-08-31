"""Tests for healthcare-domain configuration files.

Validates that config/healthcare_prompts.yaml, config/healthcare_models.yaml,
and config/drug_database.yaml parse as valid YAML and contain the expected
top-level keys, following the style of tests/unit/test_config.py and
tests/unit/test_docker_config.py.
"""

import yaml
import pytest


@pytest.fixture
def healthcare_models_config():
    with open("config/healthcare_models.yaml", "r") as f:
        return yaml.safe_load(f)


@pytest.fixture
def healthcare_prompts_config():
    with open("config/healthcare_prompts.yaml", "r") as f:
        return yaml.safe_load(f)


@pytest.fixture
def drug_database_config():
    with open("config/drug_database.yaml", "r") as f:
        return yaml.safe_load(f)


# --- healthcare_models.yaml -------------------------------------------------


def test_healthcare_models_is_valid_yaml(healthcare_models_config):
    assert healthcare_models_config is not None
    assert isinstance(healthcare_models_config, dict)


def test_healthcare_models_has_expected_top_level_keys(healthcare_models_config):
    for key in ("llm_models", "embedding_models", "reranker_models", "healthcare_defaults"):
        assert key in healthcare_models_config, f"Missing top-level key: {key}"


def test_healthcare_models_llm_entries_have_required_fields(healthcare_models_config):
    llm_models = healthcare_models_config["llm_models"]
    assert len(llm_models) > 0
    for model_id, model in llm_models.items():
        assert "name" in model, f"{model_id} missing 'name'"
        assert "context_length" in model, f"{model_id} missing 'context_length'"
        assert "parameters" in model, f"{model_id} missing 'parameters'"


def test_healthcare_defaults_has_expected_flags(healthcare_models_config):
    defaults = healthcare_models_config["healthcare_defaults"]
    assert "require_source_citation" in defaults
    assert "require_medical_disclaimer" in defaults
    assert defaults["require_source_citation"] is True
    assert defaults["require_medical_disclaimer"] is True


# --- healthcare_prompts.yaml -------------------------------------------------


def test_healthcare_prompts_is_valid_yaml(healthcare_prompts_config):
    assert healthcare_prompts_config is not None
    assert isinstance(healthcare_prompts_config, dict)


def test_healthcare_prompts_has_expected_top_level_keys(healthcare_prompts_config):
    for key in (
        "system_prompt",
        "escalation_keywords",
        "medical_disclaimer_text",
        "few_shot_examples",
        "response_format",
    ):
        assert key in healthcare_prompts_config, f"Missing top-level key: {key}"


def test_healthcare_prompts_system_prompt_mentions_not_medical_advice(healthcare_prompts_config):
    system_prompt = healthcare_prompts_config["system_prompt"].lower()
    assert "not a clinician" in system_prompt or "not provide medical advice" in system_prompt


def test_healthcare_prompts_has_at_least_five_few_shot_examples(healthcare_prompts_config):
    examples = healthcare_prompts_config["few_shot_examples"]
    assert len(examples) >= 5
    for example in examples:
        assert "query" in example
        assert "context" in example
        assert "answer" in example


def test_healthcare_prompts_escalation_keywords_nonempty(healthcare_prompts_config):
    keywords = healthcare_prompts_config["escalation_keywords"]
    assert isinstance(keywords, list)
    assert len(keywords) > 0
    assert "chest pain" in keywords


def test_healthcare_prompts_response_format_requires_disclaimer(healthcare_prompts_config):
    response_format = healthcare_prompts_config["response_format"]
    assert response_format.get("include_medical_disclaimer") is True
    assert response_format.get("include_sources") is True


# --- drug_database.yaml -------------------------------------------------


def test_drug_database_is_valid_yaml(drug_database_config):
    assert drug_database_config is not None
    assert isinstance(drug_database_config, dict)


def test_drug_database_has_expected_top_level_keys(drug_database_config):
    for key in ("disclaimer", "drugs", "interactions", "interaction_check_settings"):
        assert key in drug_database_config, f"Missing top-level key: {key}"


def test_drug_database_has_disclaimer_text(drug_database_config):
    disclaimer = drug_database_config["disclaimer"].lower()
    assert "sample data" in disclaimer
    assert "fictional" in disclaimer
    assert "not real medical guidance" in disclaimer


def test_drug_database_entries_are_marked_synthetic(drug_database_config):
    drugs = drug_database_config["drugs"]
    assert len(drugs) > 0
    for drug in drugs:
        assert drug.get("synthetic") is True, f"Drug entry {drug.get('id')} not marked synthetic"
        assert "name" in drug
        assert "class" in drug


def test_drug_database_interactions_reference_known_drugs(drug_database_config):
    drug_names = {d["name"] for d in drug_database_config["drugs"]}
    interactions = drug_database_config["interactions"]
    assert len(interactions) > 0
    for interaction in interactions:
        assert interaction["drug_a"] in drug_names
        assert interaction["drug_b"] in drug_names
        assert "illustrative_severity" in interaction
