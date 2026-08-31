# Insurance Industry RAG Pipeline Guide

> **Disclaimer:** This guide, and every sample document it links to, uses **fictional,
> synthetic data**. Company names such as "Meridian Mutual Insurance", "Northstar
> Harbor Group", "Summit Lighthouse Assurance", and "Evergreen Wellness Cooperative"
> are invented for this repository. Regulatory and compliance content in this guide
> is a general, plain-language summary of common concepts written in our own words —
> it is **not legal advice**, is **not a substitute for qualified compliance counsel**,
> and must not be treated as authoritative or current regulatory text. A real
> deployment handling real policyholder or health data must be reviewed by qualified
> legal/compliance counsel before use.

This guide documents how to configure and use the RAG pipeline in this repository for
an **insurance industry** use case: policy documents, claims processing, underwriting
guidelines, premium calculation, and compliance-aware Q&A. It complements the general
setup instructions in the top-level [README.md](../README.md) and
[GETTING_STARTED.md](../GETTING_STARTED.md).

This is primarily a **documentation, configuration, and sample-data** feature. Several
"domain-specific features" below are described/designed rather than shipped as trained
ML models — see each feature's "Status" note.

---

## 1. Insurance-Specific Data Sources

The pipeline can ingest the following insurance document categories. Fictional sample
files for each category live in [`data/insurance/`](../data/insurance/):

| Data source | Sample file | Description |
|---|---|---|
| Policy documents/templates | `sample_policy_documents.json` | Auto, homeowners, life, and health policy documents with coverage summaries. |
| Claims processing records | `sample_claims.json` | Claims with status, workflow stage, and adjuster notes. |
| Underwriting guidelines | `sample_underwriting_guidelines.json` | Risk-tiering criteria per product line. |
| Premium calculation rules | `sample_premium_calculation_rules.json` | Simplified rating-factor formulas. |
| Insurance product catalogs | `sample_product_catalog.json` | Product lines, states available, summaries. |
| Regulatory compliance notes (state-wise) | `sample_state_compliance_notes.json` | General, non-authoritative summaries of common state regulatory concepts. |
| Example Q&A pairs | `sample_qa_examples.json` | Question/answer pairs for evaluation and documentation. |

In a real deployment, these would be sourced from your own document management
system, claims system, policy administration system, and your compliance team's
guidance for each state you operate in — **not** from this repository's fictional
samples.

### Ingesting insurance documents

The existing ingestion pipeline (`src/ingestion/document_processor.py`) and RAG
pipeline (`src/rag/pipeline.py`) work as documented in the main README — insurance
documents are ingested the same way as any other document (PDF, DOCX, TXT, JSON).
To use the insurance-tuned configuration instead of the defaults:

```bash
# Point the pipeline at the insurance-specific config files
export INSURANCE_CONFIG_MODELS_PATH=config/insurance_models.yaml
export INSURANCE_CONFIG_PROMPTS_PATH=config/insurance_prompts.yaml

# Load the fictional sample insurance documents (for local testing/demo only)
python scripts/load_test_data.py --source data/insurance/
```

> Note: `scripts/load_test_data.py` loads generic test fixtures today; passing a
> `--source` directory is illustrative of the intended usage pattern for insurance
> data. Wire up the actual insurance-specific loading logic (reading the JSON
> shape shown in `data/insurance/`) as part of adopting this guide in your fork.

See [`config/insurance.env.example`](../config/insurance.env.example) for the full
list of insurance-specific environment variables (model selection, chunking, HIPAA
mode, audit logging, retention window).

---

## 2. Domain-Specific Features

These are the insurance-specific capabilities this pipeline is designed to support.
Each is described here, with prompt templates provided in
[`config/insurance_prompts.yaml`](../config/insurance_prompts.yaml) under
`task_prompts`. None require a bespoke trained classifier — they are implemented as
prompt-engineered LLM tasks over retrieved context, which keeps them consistent with
the rest of this repository's "local LLM + retrieval" architecture.

| Feature | Status | How it works |
|---|---|---|
| Policy number extraction/validation | Prompt-based (described) | `task_prompts.policy_number_extraction` asks the LLM to find and validate policy-number-shaped strings (`COMPANY-PRODUCT-DIGITS`) in a query or document. For strict validation, pair with a regex pre-filter, e.g. `^[A-Z]{2,4}-[A-Z]+-\d{4,10}(-SAMPLE)?$`, before the LLM step. |
| Coverage type classification | Prompt-based (described) | `task_prompts.coverage_type_classification` classifies text into `auto \| homeowners \| life \| health \| other`. |
| Claim status tracking | Retrieval + prompt (described) | `task_prompts.claim_status_tracking` answers status/workflow-stage questions using only the retrieved claim record (see `sample_claims.json`'s `status` and `workflow_stage` fields). |
| Premium calculation assistance | Retrieval + prompt (described) | `task_prompts.premium_calculation_assistance` walks through the rating-factor formula found in context (see `sample_premium_calculation_rules.json`). It explains a calculation; it is **not** a rating engine and must not be used to bind real quotes. |
| Risk assessment queries | Retrieval + prompt (described) | `task_prompts.risk_assessment_queries` explains which fictional risk tier applies given underwriting-guideline context. |
| Compliance checking (state-wise) | Retrieval + prompt (described) | `task_prompts.compliance_checking_state_wise` answers general questions using only the state-specific compliance notes retrieved, and always appends a "consult counsel" caveat. |
| Customer policy lookup | Retrieval + prompt (described) | `task_prompts.customer_policy_lookup` answers policy-detail questions from retrieved policy documents, citing the policy number and source. |

All of the above rely on retrieval quality (see `insurance_retrieval` tuning in
[`config/insurance_models.yaml`](../config/insurance_models.yaml)) plus the
`system_prompt` in `config/insurance_prompts.yaml`, which instructs the model to
never invent a policy number, claim number, coverage limit, or premium figure that
isn't present in retrieved context.

---

## 3. Setup Instructions for Insurance Data

1. **Configure environment variables.** Copy the relevant lines from
   [`config/insurance.env.example`](../config/insurance.env.example) into your `.env`
   file (alongside the base variables documented in the main README).
2. **Review the model and prompt configs.**
   [`config/insurance_models.yaml`](../config/insurance_models.yaml) and
   [`config/insurance_prompts.yaml`](../config/insurance_prompts.yaml) follow the
   same structure as `config/models.yaml` / `config/prompts.yaml` — swap in your
   preferred models/prompts as needed.
3. **Load sample data (optional, for local testing/demo only).** The fictional
   sample files in `data/insurance/` can be ingested to try out the pipeline before
   connecting real document sources. See [`docs/INSURANCE_EXAMPLES.md`](INSURANCE_EXAMPLES.md)
   for example queries and expected responses against this sample data.
4. **Enable HIPAA-mode / audit logging if handling health-insurance data.** Set
   `INSURANCE_HIPAA_MODE_ENABLED=true` and `INSURANCE_AUDIT_LOGGING_ENABLED=true` in
   your `.env`. See the Compliance section below and
   `src/security/insurance_audit_log.py` for the lightweight audit-logging hook.
5. **Point ingestion at your real document sources.** Replace `data/insurance/` with
   your actual policy administration, claims, and underwriting systems' export/API,
   subject to your organization's data-handling and access-control policies.

---

## 4. Compliance Requirements

> The notes in this section are **general, educational summaries written in our own
> words**, not legal advice, and not quotes from any statute or regulation. Insurance
> regulation varies significantly by state (and by product line: auto, home, life,
> health each have different regulatory regimes) and changes over time. **Consult
> qualified compliance counsel** before relying on any of this for a real deployment.

### 4.1 State insurance regulations (general concepts)

Common regulatory themes across US states, described generically (see
`data/insurance/sample_state_compliance_notes.json` for fictional, illustrative
per-state notes in this same style):

- **Rate and form filing** — insurers commonly must file rates and policy forms with
  state regulators before use, with some lines requiring prior approval.
- **Claims-handling timelines and fair-claims practices** — states commonly set
  expectations for prompt acknowledgment, investigation, and communication of claim
  decisions, and prohibit specific unfair claims practices.
- **Licensing** — insurers, and often the systems/vendors that help produce
  customer-facing communications (including AI-generated ones), may be subject to
  state licensing and market-conduct oversight.
- **Data privacy** — many states have their own consumer-data-privacy requirements
  layered on top of federal ones, particularly for sensitive categories like health
  information.

Any RAG-generated answer that touches these topics should: (a) cite the retrieved
source document, (b) note the state the answer applies to, and (c) include a caveat
that the user should confirm with compliance/legal for authoritative guidance. The
`compliance_checking_state_wise` prompt template in `config/insurance_prompts.yaml`
does this by default.

### 4.2 HIPAA (for health insurance products)

If your deployment ingests or answers questions about **health insurance** documents
containing **protected health information (PHI)** — member names, diagnoses,
treatment details, claim details tied to an individual — general, non-authoritative
concepts to keep in mind:

- **Minimum necessary access** — limit what's retrieved/returned to what's needed to
  answer the specific query; avoid dumping full member records into an LLM prompt
  when a narrower context would do.
- **Access controls & authentication** — PHI-bearing indices/collections should sit
  behind the same tenant isolation and authentication used elsewhere in this system
  (see `src/security/tenant_isolation.py`), not a separate unauthenticated path.
- **Audit logging** — record who accessed which PHI-bearing document/record and
  when. See `src/security/insurance_audit_log.py` for a lightweight hook, and
  `src/db/models.py`'s existing `AuditLog` table for a database-backed alternative.
- **Encryption** — PHI should be encrypted at rest and in transit, consistent with
  the rest of this system's security posture.
- **De-identification for non-production use** — use de-identified or synthetic data
  (like the samples in `data/insurance/`) for development, testing, and demos; never
  real member PHI.
- **Business Associate Agreements (BAAs)** — if health-insurance customers' PHI will
  flow through third-party services (hosted LLM APIs, cloud vector DBs, etc.), a BAA
  is typically required with each such vendor. This repository's default local-LLM
  architecture (Ollama, self-hosted Weaviate/Postgres) avoids sending PHI to external
  vendors by default — but confirm this for your actual deployment topology.

`INSURANCE_HIPAA_MODE_ENABLED=true` (see `config/insurance.env.example`) is a marker
you can use in your own code to route health-insurance document types through
stricter logging/access-control paths; it does not itself implement encryption or
BAA management.

### 4.3 Privacy / data-handling guidelines

- Treat policy numbers, claim numbers, and any personally identifying details as
  sensitive even outside of health insurance (e.g., SSNs sometimes present on older
  paper policy applications, driver's license numbers on auto claims).
- Never log full PHI or PII payloads in plaintext application logs — the audit hook
  in `src/security/insurance_audit_log.py` deliberately logs *which* document/record
  was accessed and *by whom*, not the document's content.
- Apply the existing multi-tenant isolation (`src/security/tenant_isolation.py`) so
  one customer's/carrier's insurance documents are never retrievable by another
  tenant's queries.
- Redact or mask sensitive fields (e.g., partial policy numbers, masked SSNs) in any
  answer surfaced to end users who aren't authorized to see the full value.

### 4.4 Audit logging for document access

A lightweight audit-logging hook is provided at
[`src/security/insurance_audit_log.py`](../src/security/insurance_audit_log.py):

```python
from src.security.insurance_audit_log import log_document_access

log_document_access(
    tenant_id="acme-insurance",
    action="policy.lookup",
    document_id="policy_ins_001",
    user_id="agent-42",
    details="Queried via /api/v1/{tenant}/query",
)
```

It is disabled by default (`INSURANCE_AUDIT_LOGGING_ENABLED=false`) so local
development doesn't require extra setup, and writes newline-delimited JSON events to
`INSURANCE_AUDIT_LOG_PATH` (default `logs/insurance_audit.log`) when enabled. For
production, route these events into the existing `AuditLog` SQLAlchemy model in
`src/db/models.py` (or your centralized logging/SIEM pipeline) instead of a local
file — the event shape is designed to make that swap straightforward.

### 4.5 Data retention policy (documentation)

General, non-authoritative starting points for a data retention discussion with your
compliance team (concrete numbers vary by state, product line, and record type):

- **Policy records** — commonly retained for the life of the policy plus a number of
  years after termination/expiration (illustrative default in
  `config/insurance.env.example`: `INSURANCE_DATA_RETENTION_DAYS=2555`, i.e. ~7
  years — a placeholder, not a recommendation).
- **Claims records** — often retained longer than policy records, since claims can
  be reopened or disputed well after the policy period ends.
- **Health-insurance/PHI records** — HIPAA-adjacent retention expectations, and
  state-specific health-record retention rules, may require longer or different
  retention than non-health lines.
- **Minors** — some states extend retention/statute-of-limitations windows for
  records involving minors.
- **Deletion** — when a document is deleted from the primary store, ensure it's also
  removed from the vector index (Weaviate) and any cache (Redis) — stale embeddings
  that outlive the source-of-truth record are both a privacy risk and a source of
  inconsistent answers.

`INSURANCE_DATA_RETENTION_DAYS` is provided as a reference value for documentation
and future policy-enforcement tooling; this feature does not implement automatic
deletion.

---

## 5. Sample Insurance Queries and Responses

See [`docs/INSURANCE_EXAMPLES.md`](INSURANCE_EXAMPLES.md) for a full set of worked
examples (policy lookup, claims workflow, premium/coverage retrieval, compliance
questions) using the fictional sample data in `data/insurance/`.

Quick preview:

> **Q:** What is the status of claim MMI-CLM-20260214-0001-SAMPLE?
> **A:** The claim is under review, currently at the damage assessment stage
> (fictional sample data, source: `data/insurance/sample_claims.json`).

---

## 6. Related Documentation

- [`docs/INSURANCE_EXAMPLES.md`](INSURANCE_EXAMPLES.md) — worked examples and sample
  documents.
- [`config/insurance_models.yaml`](../config/insurance_models.yaml) — model config.
- [`config/insurance_prompts.yaml`](../config/insurance_prompts.yaml) — prompts.
- [`config/insurance.env.example`](../config/insurance.env.example) — environment
  variables.
- [`data/insurance/`](../data/insurance/) — fictional sample data.
- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) — overall system architecture.
- [`docs/DATA_SOURCES_AND_MODELS.md`](DATA_SOURCES_AND_MODELS.md) — general data
  source and model research (healthcare/insurance-adjacent).
