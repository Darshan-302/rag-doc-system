"""Test insurance sample data files in data/insurance/.

These tests validate that the fictional sample data introduced for the
Insurance Industry RAG Pipeline feature exists, is well-formed, and carries the
required "SAMPLE DATA" disclaimer (see data/insurance/README.md).
"""

import json
import os

import pytest

INSURANCE_DATA_DIR = os.path.join("data", "insurance")

REQUIRED_DISCLAIMER_SNIPPET = "SAMPLE DATA"

EXPECTED_JSON_FILES = [
    "sample_policy_documents.json",
    "sample_claims.json",
    "sample_underwriting_guidelines.json",
    "sample_premium_calculation_rules.json",
    "sample_product_catalog.json",
    "sample_state_compliance_notes.json",
    "sample_qa_examples.json",
]


def test_insurance_data_directory_exists():
    """Test that data/insurance/ exists."""
    assert os.path.isdir(INSURANCE_DATA_DIR)


def test_insurance_data_readme_exists_with_disclaimer():
    """Test that data/insurance/README.md exists and carries the disclaimer."""
    readme_path = os.path.join(INSURANCE_DATA_DIR, "README.md")
    assert os.path.isfile(readme_path)
    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert REQUIRED_DISCLAIMER_SNIPPET in content


@pytest.mark.parametrize("filename", EXPECTED_JSON_FILES)
def test_sample_json_file_exists(filename):
    """Test that each expected sample data file exists."""
    path = os.path.join(INSURANCE_DATA_DIR, filename)
    assert os.path.isfile(path), f"Missing expected sample data file: {path}"


@pytest.mark.parametrize("filename", EXPECTED_JSON_FILES)
def test_sample_json_file_is_valid_json(filename):
    """Test that each sample data file parses as valid JSON."""
    path = os.path.join(INSURANCE_DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert isinstance(data, dict)


@pytest.mark.parametrize("filename", EXPECTED_JSON_FILES)
def test_sample_json_file_has_disclaimer(filename):
    """Test that each sample data file has a top-level _disclaimer field
    containing the required 'SAMPLE DATA' marker."""
    path = os.path.join(INSURANCE_DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "_disclaimer" in data, f"{filename} missing '_disclaimer' field"
    assert REQUIRED_DISCLAIMER_SNIPPET in data["_disclaimer"]


def test_sample_policy_documents_have_required_fields():
    """Test that sample policy documents include a policy number and fictional
    company framing."""
    path = os.path.join(INSURANCE_DATA_DIR, "sample_policy_documents.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    policies = data["policies"]
    assert len(policies) >= 4, "Expected at least 4 sample policies (auto, home, life, health)"

    product_types = {p["product_type"] for p in policies}
    assert {"auto", "homeowners", "life", "health"}.issubset(product_types)

    for policy in policies:
        assert policy["policy_number"].endswith("-SAMPLE"), (
            f"Policy number {policy['policy_number']} should be clearly marked as a sample"
        )
        assert "fictional" in policy["company"].lower()


def test_sample_claims_have_status_and_workflow_stage():
    """Test that sample claims support claim-status tracking queries."""
    path = os.path.join(INSURANCE_DATA_DIR, "sample_claims.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    claims = data["claims"]
    assert len(claims) >= 3
    for claim in claims:
        assert claim["claim_number"].endswith("-SAMPLE")
        assert "status" in claim
        assert "workflow_stage" in claim


def test_sample_qa_examples_have_at_least_five_pairs():
    """Test that there are at least 5 example Q&A pairs (matches
    docs/INSURANCE_EXAMPLES.md acceptance criteria of 5+ examples)."""
    path = os.path.join(INSURANCE_DATA_DIR, "sample_qa_examples.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    qa_pairs = data["qa_pairs"]
    assert len(qa_pairs) >= 5
    for pair in qa_pairs:
        assert "question" in pair
        assert "expected_answer" in pair
        assert "source_document" in pair


def test_sample_state_compliance_notes_are_not_verbatim_statute_framing():
    """Test that compliance notes explicitly frame themselves as general concepts,
    not verbatim regulatory text (per the CRITICAL constraint on sample data)."""
    path = os.path.join(INSURANCE_DATA_DIR, "sample_state_compliance_notes.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "not legal advice" in data["_disclaimer"].lower() or "not legal advice" in json.dumps(data).lower()

    notes = data["compliance_notes"]
    assert len(notes) >= 3
    for note in notes:
        assert "state" in note
        assert "in our own words" in note["content"].lower()


def test_insurance_documentation_files_exist():
    """Test that the required insurance documentation files exist."""
    assert os.path.isfile(os.path.join("docs", "INSURANCE_RAG_GUIDE.md"))
    assert os.path.isfile(os.path.join("docs", "INSURANCE_EXAMPLES.md"))


def test_insurance_examples_doc_has_disclaimer_and_five_examples():
    """Test that docs/INSURANCE_EXAMPLES.md has the disclaimer banner and at
    least 5 numbered examples."""
    path = os.path.join("docs", "INSURANCE_EXAMPLES.md")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    assert REQUIRED_DISCLAIMER_SNIPPET in content
    # Count "### Example N" headings
    example_count = content.count("### Example")
    assert example_count >= 5, f"Expected at least 5 '### Example' sections, found {example_count}"


def test_insurance_config_files_exist():
    """Test that the required insurance config files exist."""
    assert os.path.isfile(os.path.join("config", "insurance_models.yaml"))
    assert os.path.isfile(os.path.join("config", "insurance_prompts.yaml"))
    assert os.path.isfile(os.path.join("config", "insurance.env.example"))
