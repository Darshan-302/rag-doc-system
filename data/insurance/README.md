# Insurance Sample Data

> **SAMPLE DATA — fictional, for testing/demo purposes only, not real regulatory or policy content.**

This directory contains **synthetic, fictional** insurance data used to demonstrate the
Insurance Industry RAG Pipeline described in [`docs/INSURANCE_RAG_GUIDE.md`](../../docs/INSURANCE_RAG_GUIDE.md)
and [`docs/INSURANCE_EXAMPLES.md`](../../docs/INSURANCE_EXAMPLES.md).

All company names (e.g. "Meridian Mutual Insurance", "Northstar Harbor Group", "Summit
Lighthouse Assurance", "Evergreen Wellness Cooperative") are invented for this repository.
All policy numbers, claim numbers, names, dollar amounts, and dates are placeholders. Any
resemblance to a real company, person, or policy is coincidental. Regulatory concepts are
described in our own words as generic, non-authoritative illustrations — they are not
quotes from any statute or regulation and must not be relied on for compliance decisions.
This is separate, dedicated sample data for the insurance feature; it does not modify or
replace the pre-existing combined insurance+healthcare samples in
`data/raw/insurance_healthcare/`.

## Files

| File | Contents |
|---|---|
| `sample_policy_documents.json` | Fictional auto, homeowners, life, and health policy documents/templates. |
| `sample_claims.json` | Fictional claims with status and workflow-stage tracking examples. |
| `sample_underwriting_guidelines.json` | Fictional underwriting risk-tiering guidelines per product line. |
| `sample_premium_calculation_rules.json` | Fictional, simplified premium calculation formulas. |
| `sample_product_catalog.json` | Fictional insurance product catalog across product lines and states. |
| `sample_state_compliance_notes.json` | Generic, plain-language summaries of common state-regulatory concepts (not verbatim statute text). |
| `sample_qa_examples.json` | Example question/answer pairs used in tests and documentation. |

Every file above includes an `_disclaimer` field at the top restating that its contents
are fictional sample data.
