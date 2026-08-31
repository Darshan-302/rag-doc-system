# data/healthcare/

> **SAMPLE DATA — fictional, for testing/demo purposes only. Not real medical
> guidance. Not reviewed by a medical professional. Do not use for actual
> clinical, diagnostic, or treatment decisions.**

This directory contains **synthetic** sample data for the healthcare RAG
pipeline feature (see [`docs/HEALTHCARE_RAG_GUIDE.md`](../../docs/HEALTHCARE_RAG_GUIDE.md)
and [`docs/HEALTHCARE_EXAMPLES.md`](../../docs/HEALTHCARE_EXAMPLES.md)). Every
file here uses fictional patient names/IDs, fictional drug names, and
illustrative (not verified) figures. No real patient data, and no verbatim
copyrighted CDC/FDA text, is included.

This is separate from the pre-existing `data/raw/insurance_healthcare/`
directory, which is unrelated prior content for the insurance RAG pipeline
and is not modified by this feature.

## Layout

| Path | Contents |
|---|---|
| `medical_guidelines/` | Synthetic condition-management guideline summaries, written in original wording (not copied CDC/FDA text) |
| `clinical_trials/` | Fictional clinical trial records (fictional trial IDs, sponsors, eligibility criteria) |
| `drug_interactions/` | Fictional drug interaction sample data (fictional drug names) |
| `conditions/` | Synthetic condition fact sheets |
| `consent_forms/` | A fictional/template patient consent form |
| `qa/` | Sample healthcare Q&A pairs used in `docs/HEALTHCARE_EXAMPLES.md` |

Every JSON file in this directory includes a top-level `"disclaimer"` field
carrying the same warning as this README.
