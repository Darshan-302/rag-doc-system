"""Test insurance-specific configuration files (config/insurance_*.yaml)."""

import yaml
import pytest


@pytest.fixture
def insurance_models_config():
    """Load config/insurance_models.yaml"""
    with open("config/insurance_models.yaml", "r") as f:
        return yaml.safe_load(f)


@pytest.fixture
def insurance_prompts_config():
    """Load config/insurance_prompts.yaml"""
    with open("config/insurance_prompts.yaml", "r") as f:
        return yaml.safe_load(f)


# --- insurance_models.yaml -------------------------------------------------


def test_insurance_models_is_valid_yaml(insurance_models_config):
    """Test that insurance_models.yaml parses as valid YAML."""
    assert insurance_models_config is not None
    assert isinstance(insurance_models_config, dict)


def test_insurance_models_has_expected_top_level_keys(insurance_models_config):
    """Test that insurance_models.yaml has the expected top-level sections,
    mirroring the structure of config/models.yaml."""
    expected_keys = {
        "llm_models",
        "embedding_models",
        "reranker_models",
        "insurance_retrieval",
        "insurance_domain_features",
    }
    for key in expected_keys:
        assert key in insurance_models_config, f"Missing top-level key: {key}"


def test_insurance_models_llm_models_nonempty(insurance_models_config):
    """Test that at least one LLM model is defined."""
    llm_models = insurance_models_config["llm_models"]
    assert isinstance(llm_models, dict)
    assert len(llm_models) > 0
    for model_id, model in llm_models.items():
        assert "name" in model, f"{model_id} missing 'name'"
        assert "context_length" in model, f"{model_id} missing 'context_length'"


def test_insurance_domain_features_lists_required_capabilities(insurance_models_config):
    """Test that all domain-specific features from the issue scope are documented."""
    features = set(insurance_models_config["insurance_domain_features"])
    expected_features = {
        "policy_number_extraction_validation",
        "coverage_type_classification",
        "claim_status_tracking",
        "premium_calculation_assistance",
        "risk_assessment_queries",
        "compliance_checking_state_wise",
        "customer_policy_lookup",
    }
    assert expected_features.issubset(features)


# --- insurance_prompts.yaml -------------------------------------------------


def test_insurance_prompts_is_valid_yaml(insurance_prompts_config):
    """Test that insurance_prompts.yaml parses as valid YAML."""
    assert insurance_prompts_config is not None
    assert isinstance(insurance_prompts_config, dict)


def test_insurance_prompts_has_expected_top_level_keys(insurance_prompts_config):
    """Test that insurance_prompts.yaml has the expected top-level sections,
    mirroring the structure of config/prompts.yaml, plus a task_prompts section."""
    expected_keys = {
        "system_prompt",
        "few_shot_examples",
        "response_format",
        "task_prompts",
    }
    for key in expected_keys:
        assert key in insurance_prompts_config, f"Missing top-level key: {key}"


def test_insurance_prompts_system_prompt_is_nonempty_string(insurance_prompts_config):
    """Test that the system prompt is present and non-trivial."""
    system_prompt = insurance_prompts_config["system_prompt"]
    assert isinstance(system_prompt, str)
    assert len(system_prompt.strip()) > 20


def test_insurance_prompts_few_shot_examples_have_required_fields(insurance_prompts_config):
    """Test that each few-shot example has query/context/answer fields."""
    examples = insurance_prompts_config["few_shot_examples"]
    assert isinstance(examples, list)
    assert len(examples) > 0
    for example in examples:
        assert "query" in example
        assert "context" in example
        assert "answer" in example


def test_insurance_prompts_task_prompts_cover_domain_features(insurance_prompts_config):
    """Test that task_prompts documents a prompt for each domain-specific feature."""
    task_prompts = insurance_prompts_config["task_prompts"]
    expected_tasks = {
        "policy_number_extraction",
        "coverage_type_classification",
        "claim_status_tracking",
        "premium_calculation_assistance",
        "risk_assessment_queries",
        "compliance_checking_state_wise",
        "customer_policy_lookup",
    }
    assert expected_tasks.issubset(set(task_prompts.keys()))
    for task_name, task in task_prompts.items():
        assert "prompt" in task, f"{task_name} missing 'prompt'"
        assert len(task["prompt"].strip()) > 0, f"{task_name} has empty prompt"


def test_insurance_prompts_response_format_matches_base_shape(insurance_prompts_config):
    """Test that response_format has the same shape as config/prompts.yaml's."""
    response_format = insurance_prompts_config["response_format"]
    assert "include_sources" in response_format
    assert "include_confidence" in response_format
    assert "max_length" in response_format
    assert isinstance(response_format["max_length"], int)
