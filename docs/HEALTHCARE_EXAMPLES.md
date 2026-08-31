# Healthcare RAG — Example Queries & Flows

> **SAMPLE DATA — fictional, for testing/demo purposes only. Not real medical
> guidance. Not reviewed by a medical professional. Do not use for actual
> clinical, diagnostic, or treatment decisions.**
>
> Every example below uses synthetic patients, fictional drug names, and
> illustrative (not verified) data drawn from
> [`data/healthcare/`](../data/healthcare/). Prompts and answers follow the
> conventions in [`config/healthcare_prompts.yaml`](../config/healthcare_prompts.yaml)
> and are described in full in
> [`docs/HEALTHCARE_RAG_GUIDE.md`](HEALTHCARE_RAG_GUIDE.md).

These examples illustrate the intended shape of request/response flows for a
healthcare-domain RAG deployment built on this configuration. They are
worked examples for documentation purposes; no live inference is executed by
this repository as part of this feature.

---

## 1. Medical Condition Info Lookup

**Query:** "What is hypertension and how is it generally managed?"

**Retrieved document:** `data/healthcare/medical_guidelines/hypertension_management_guideline.json` (`guideline_synth_001`)

**Example answer:**
> Hypertension is a condition where blood pressure against the artery walls
> stays elevated over time. Educational sources describe management
> generally involving lifestyle changes such as diet and exercise, and
> medication when a clinician recommends it. This is general educational
> information, not a treatment plan — a clinician should determine the right
> approach for any individual.
>
> *Source: Example Guideline Summary: General Approach to Hypertension
> Management (Synthetic). This information is for general educational
> purposes only and is not medical advice.*

---

## 2. Drug Interaction Checking

**Query:** "Could Synthovas-A and Glucomend-X interact, based on the sample interaction data?"

**Retrieved document:** `data/healthcare/drug_interactions/drug_interactions_sample.json` (mirrors `config/drug_database.yaml`)

**Example answer:**
> The sample interaction data includes an illustrative (fictional) entry
> showing Synthovas-A and Glucomend-X marked as a "moderate (example only)"
> interaction, intended only to demonstrate the data shape. This is synthetic
> data, not a real drug interaction finding, and must not be used to make an
> actual medication decision — consult a pharmacist or prescriber.
>
> *Source: synthetic drug interaction sample. This information is not
> medical advice.*

---

## 3. Treatment Option Recommendations

**Query:** "What treatment approaches are generally discussed for the example hypertension guideline?"

**Retrieved document:** `data/healthcare/medical_guidelines/hypertension_management_guideline.json`, section "Medication therapy (illustrative)"

**Example answer:**
> The synthetic guideline summary describes, at a general level, that when
> lifestyle measures alone aren't sufficient, a clinician may consider
> medication therapy — but this sample document intentionally does not
> specify which medication or dosage, since that is an individualized
> clinical decision. This system does not recommend specific treatments;
> please discuss options with a qualified clinician.
>
> *Source: synthetic hypertension guideline summary. Not a treatment
> recommendation.*

---

## 4. Medical Procedure Explanations

**Query:** "Can you explain, in general terms, what a routine blood pressure screening involves?"

**Retrieved document:** `data/healthcare/medical_guidelines/hypertension_management_guideline.json`, section "Monitoring (illustrative)"

**Example answer:**
> In general educational terms, a routine blood pressure check is a brief,
> non-invasive measurement (commonly using an inflatable cuff) used to
> assess blood pressure as part of general health maintenance. This example
> intentionally omits clinical thresholds. Specific frequency and
> interpretation of results should be determined by a clinician based on
> individual risk factors — this response is general educational information
> only.
>
> *Source: synthetic hypertension guideline summary.*

---

## 5. Clinical Trial Eligibility Assessment

**Query:** "Am I eligible for the fictional trial SYNTH-TRIAL-001?"

**Retrieved document:** `data/healthcare/clinical_trials/clinical_trials_sample.json` (`SYNTH-TRIAL-001`)

**Example answer:**
> Per the synthetic sample data, the fictional trial SYNTH-TRIAL-001 lists
> illustrative eligibility criteria such as being an adult (18–75, example
> only) with the example condition present, and not being enrolled in
> another example study within 30 days. This is fabricated demonstration
> data, not a real trial — real eligibility must be confirmed via
> ClinicalTrials.gov or the actual study team, not this sample system.
>
> *Source: synthetic clinical trial sample.*

---

## 6. Insurance Coverage Verification

**Query:** "Based on the sample data, is Illustrative Procedure X generally covered?"

**Retrieved document:** existing sample coverage data in `data/raw/insurance_healthcare/` (pre-existing, unrelated to this feature; shown here to illustrate a cross-domain query)

**Example answer:**
> The sample coverage data shows a fictional example where "Illustrative
> Procedure X" is marked as typically covered when documented as medically
> necessary, with an example note about possible prior authorization. This
> is synthetic example data — actual coverage depends on the individual's
> real insurance plan and should be verified directly with the insurer.
>
> *Source: synthetic insurance coverage sample.*

---

## 7. General Healthcare Q&A

**Query:** "What does the example fact sheet say about type 2 diabetes risk factors?"

**Retrieved document:** `data/healthcare/conditions/condition_fact_sheets.json` (`condition_synth_002`)

**Example answer:**
> The example fact sheet describes, at a general educational level, that
> commonly discussed risk factors for type 2 diabetes include age, elevated
> body weight, family history, and history of elevated blood glucose — this
> list is illustrative and non-exhaustive. It is not a diagnostic tool.
>
> *Source: synthetic condition fact sheet. Not medical advice.*

---

## 8. Emergency Escalation (safety behavior, not a normal Q&A flow)

**Query:** "I have chest pain right now, what should I do?"

**Expected behavior:** The query matches an `escalation_keywords` entry in
`config/healthcare_prompts.yaml` ("chest pain"). The system does **not**
attempt to answer clinically or retrieve documents for this query — it
returns a static response directing the user to seek immediate emergency
care.

**Example response:**
> This may be a medical emergency. Please contact emergency services (e.g.,
> call your local emergency number) or go to the nearest emergency
> department immediately. This system cannot provide emergency medical care.

See `data/healthcare/qa/healthcare_qa_examples.json` (`qa_synth_006`) for the
structured version of this example, and
[`docs/HEALTHCARE_RAG_GUIDE.md`](HEALTHCARE_RAG_GUIDE.md) section 9 for the
non-diagnostic framing principle behind this behavior.
