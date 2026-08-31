"""Tests for synthetic sample data under data/healthcare/.

Validates that the sample healthcare documents required by GitHub issue #15
exist, parse as valid JSON/text, and carry the required "SAMPLE DATA"
disclaimer, following the style of tests/unit/test_config.py.
"""

import json
import os

import pytest

HEALTHCARE_DATA_DIR = os.path.join("data", "healthcare")

DISCLAIMER_SNIPPET = "sample data"
FICTIONAL_SNIPPET = "fictional"

JSON_FILES = [
    os.path.join(HEALTHCARE_DATA_DIR, "medical_guidelines", "hypertension_management_guideline.json"),
    os.path.join(HEALTHCARE_DATA_DIR, "medical_guidelines", "diabetes_screening_protocol.json"),
    os.path.join(HEALTHCARE_DATA_DIR, "clinical_trials", "clinical_trials_sample.json"),
    os.path.join(HEALTHCARE_DATA_DIR, "drug_interactions", "drug_interactions_sample.json"),
    os.path.join(HEALTHCARE_DATA_DIR, "conditions", "condition_fact_sheets.json"),
    os.path.join(HEALTHCARE_DATA_DIR, "qa", "healthcare_qa_examples.json"),
]

TEXT_FILES = [
    os.path.join(HEALTHCARE_DATA_DIR, "consent_forms", "patient_consent_template.md"),
    os.path.join(HEALTHCARE_DATA_DIR, "README.md"),
]


def test_healthcare_data_directory_exists():
    assert os.path.isdir(HEALTHCARE_DATA_DIR)


@pytest.mark.parametrize("path", JSON_FILES)
def test_json_sample_file_exists_and_parses(path):
    assert os.path.isfile(path), f"Missing sample file: {path}"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data is not None


@pytest.mark.parametrize("path", JSON_FILES)
def test_json_sample_file_has_disclaimer(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "disclaimer" in data, f"{path} missing top-level 'disclaimer' field"
    disclaimer = data["disclaimer"].lower()
    assert DISCLAIMER_SNIPPET in disclaimer
    assert FICTIONAL_SNIPPET in disclaimer


@pytest.mark.parametrize("path", TEXT_FILES)
def test_text_sample_file_exists_and_has_disclaimer(path):
    assert os.path.isfile(path), f"Missing sample file: {path}"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read().lower()
    assert len(content) > 0
    assert DISCLAIMER_SNIPPET in content
    assert FICTIONAL_SNIPPET in content


def test_clinical_trials_use_fictional_trial_ids():
    path = os.path.join(HEALTHCARE_DATA_DIR, "clinical_trials", "clinical_trials_sample.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for trial in data["trials"]:
        assert trial["trial_id"].startswith("SYNTH-TRIAL-")


def test_drug_interactions_sample_matches_drug_database_config():
    """Sanity-check that data/healthcare drug interaction sample uses the
    same fictional drug names as config/drug_database.yaml, so the two
    stay consistent."""
    import yaml

    with open("config/drug_database.yaml", "r") as f:
        drug_config = yaml.safe_load(f)
    known_names = {d["name"] for d in drug_config["drugs"]}

    path = os.path.join(HEALTHCARE_DATA_DIR, "drug_interactions", "drug_interactions_sample.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for interaction in data["interactions"]:
        assert interaction["drug_a"] in known_names
        assert interaction["drug_b"] in known_names


def test_qa_examples_include_emergency_escalation_case():
    path = os.path.join(HEALTHCARE_DATA_DIR, "qa", "healthcare_qa_examples.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    styles = [qa["answer_style"] for qa in data["qa_examples"]]
    assert any("emergency" in style.lower() for style in styles)
