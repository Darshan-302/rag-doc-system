# Insurance RAG Pipeline — Worked Examples

> **SAMPLE DATA — fictional, for testing/demo purposes only, not real regulatory or
> policy content.** Every company name, policy number, claim number, dollar figure,
> and regulatory note below is synthetic and was created for this repository. Company
> names like "Meridian Mutual Insurance", "Northstar Harbor Group", "Summit Lighthouse
> Assurance", and "Evergreen Wellness Cooperative" are fictional. Regulatory concepts
> are paraphrased in general terms, are not quotes from any statute, and are not legal
> advice — consult qualified compliance counsel for a real deployment.

This document gives example insurance policy documents, example queries, claims
processing workflow examples, and premium/coverage retrieval examples for the
pipeline described in [`docs/INSURANCE_RAG_GUIDE.md`](INSURANCE_RAG_GUIDE.md). The
underlying data is checked into [`data/insurance/`](../data/insurance/) as JSON so it
can be loaded into the RAG pipeline and used in automated tests
(`tests/unit/test_insurance_data.py`).

---

## Example Policy Documents (Anonymized/Synthetic)

### 1. Auto policy — Meridian Mutual Insurance (fictional)

```
Policy Number: MMI-AUTO-0001234-SAMPLE
Named Insured: Jordan A. Sample
Product: Personal Auto — Standard Tier
State: IL
Effective Period: 2026-01-01 to 2027-01-01

Coverage Summary:
- Bodily Injury Liability: $100,000 per person / $300,000 per accident
- Property Damage Liability: $50,000 per accident
- Collision Coverage: Actual cash value minus $500 deductible
- Comprehensive Coverage: Actual cash value minus $250 deductible
- Uninsured/Underinsured Motorist: $100,000 per person / $300,000 per accident

Premium (fictional): $1,284.00 annually, billed in 6 installments of $214.00.
```
*(Full record: `data/insurance/sample_policy_documents.json#policy_ins_001`)*

### 2. Homeowners policy — Northstar Harbor Group (fictional)

```
Policy Number: NHG-HOME-0009876-SAMPLE
Named Insured: Casey R. Example
Product: Homeowners HO-3 — Sample Template
State: TX
Effective Period: 2026-03-15 to 2027-03-15

Coverage A (Dwelling): $350,000     Coverage D (Loss of Use): $70,000
Coverage B (Other Structures): $35,000   Coverage E (Personal Liability): $300,000
Coverage C (Personal Property): $175,000 Coverage F (Med. Payments): $5,000
Deductible: $1,500 (all perils), $3,500 (named windstorm/hail)
```
*(Full record: `data/insurance/sample_policy_documents.json#policy_ins_002`)*

---

## Example Queries and Responses

### Example 1 — Policy information lookup

**Query:** "What is the bodily injury liability limit on policy
MMI-AUTO-0001234-SAMPLE?"

**Retrieved context:** `sample_policy_documents.json#policy_ins_001`

**Expected response:**
> Policy MMI-AUTO-0001234-SAMPLE (Meridian Mutual Insurance, a fictional sample
> policy) has Bodily Injury Liability coverage of $100,000 per person and $300,000
> per accident.

---

### Example 2 — Claims processing workflow

**Query:** "What is the status of claim MMI-CLM-20260214-0001-SAMPLE, and what's the
next step?"

**Retrieved context:** `sample_claims.json#claim_ins_001`

**Expected response:**
> Claim MMI-CLM-20260214-0001-SAMPLE is currently **Under Review**, at the **damage
> assessment** stage. The next steps in this fictional workflow are: damage
> assessment → estimate approval → payment issued → claim closed.

**Claims workflow reference (from the sample data):**

```
Initial review → Damage assessment → Estimate approval → Payment issued → Claim closed
```

---

### Example 3 — Claim denial and appeal

**Query:** "Why was claim EWC-CLM-20260410-0003-SAMPLE denied, and by when must an
appeal be filed?"

**Retrieved context:** `sample_claims.json#claim_ins_003`

**Expected response:**
> Claim EWC-CLM-20260410-0003-SAMPLE was denied because prior authorization was not
> obtained for an out-of-network specialist visit (fictional example). The fictional
> appeal deadline noted on the claim is 2026-05-10.

---

### Example 4 — Coverage/deductible retrieval

**Query:** "What deductible applies for wind/hail damage on Casey R. Example's
homeowners policy?"

**Retrieved context:** `sample_policy_documents.json#policy_ins_002`

**Expected response:**
> Under fictional policy NHG-HOME-0009876-SAMPLE, a $3,500 deductible applies to
> named windstorm/hail damage, compared to $1,500 for other covered perils.

---

### Example 5 — Premium calculation assistance

**Query:** "Using the sample auto premium formula, what would the estimated annual
premium be for a Tier B risk with a 4-8 year old vehicle, a 1.05 territory factor,
and a multi-policy discount?"

**Retrieved context:** `sample_premium_calculation_rules.json#prem_ins_001`

**Expected response:**
> Using the fictional simplified formula: $800 base × 1.00 (Tier B) × 1.00 (vehicle
> age 4-8 yrs) × 1.05 (territory) × 0.90 (multi-policy discount) ≈ **$756.00/year**.
> This is an illustrative estimate only, not a binding quote.

---

### Example 6 — Risk assessment / underwriting query

**Query:** "A driver has 1 at-fault accident in the past 5 years and 2 moving
violations in the past 3 years. Which fictional risk tier applies under Meridian
Mutual's sample auto underwriting guideline?"

**Retrieved context:** `sample_underwriting_guidelines.json#uw_ins_001`

**Expected response:**
> This driver falls into **Risk Tier B (Standard)** under the fictional sample
> guideline, which allows up to 1 at-fault accident in 5 years and up to 2 moving
> violations in 3 years.

---

### Example 7 — State compliance question

**Query:** "In general, what kind of safeguards are commonly expected when a health
insurer handles protected health information (PHI)?"

**Retrieved context:** `sample_state_compliance_notes.json#reg_ins_004`

**Expected response:**
> In general (non-authoritative) terms: administrative, physical, and technical
> safeguards — such as access controls, encryption, and audit logging — consistent
> with the general aims of HIPAA. This is a general summary, not legal advice; consult
> qualified compliance counsel for your specific situation and jurisdiction.

---

## Customer Policy Lookup Example

**Query:** "Look up the health insurance policy for member Sam P. Illustrative."

**Retrieved context:** `sample_policy_documents.json#policy_ins_004`

**Expected response:**
> Found policy EWC-HEALTH-0002468-SAMPLE (Evergreen Wellness Cooperative, fictional,
> Gold PPO tier). Annual deductible: $1,500 individual / $3,000 family. Out-of-pocket
> maximum: $6,000 individual / $12,000 family.

---

## Notes on Using These Examples

- All examples above are reproduced from (or directly derived from) the JSON files in
  [`data/insurance/`](../data/insurance/); see that directory's `README.md` for the
  full file listing and disclaimer.
- The `data/insurance/sample_qa_examples.json` file contains these same question/answer
  pairs in a machine-readable form, used by
  `tests/unit/test_insurance_data.py` to validate the sample data.
- To adapt these for a real deployment, replace every fictional company name, policy
  number, and figure with your real (properly access-controlled) data, and remove the
  "SAMPLE"/fictional framing — but keep the underlying compliance and privacy
  practices described in [`docs/INSURANCE_RAG_GUIDE.md`](INSURANCE_RAG_GUIDE.md).
