# Healthcare RAG Pipeline Guide

> **DISCLAIMER**: This guide describes general, educational design concepts for a
> healthcare-focused RAG (Retrieval-Augmented Generation) deployment. It is **not**
> legal, compliance, or medical advice. HIPAA compliance is a legal determination
> that depends on your organization's specific systems, contracts, and risk
> posture. Before deploying anything described here against real patient data,
> **consult qualified legal/compliance counsel and appropriate clinical
> professionals**. All sample data referenced from this guide (see
> [`data/healthcare/`](../data/healthcare/)) is synthetic and fictional.

## 1. Overview

This document describes how the `feature/healthcare-rag-pipeline` work extends
the base RAG system with healthcare-domain configuration, documentation, and
sample data. It is intentionally scoped as a **documentation + configuration +
sample-data** feature, not a full clinical ML/NLP system. It does not implement
medical diagnosis, prescribing, or any autonomous clinical decision-making.

The healthcare pipeline is meant to help a downstream implementer:

- Understand what healthcare-specific data sources typically feed a medical RAG
  system.
- Understand the compliance obligations (HIPAA, PHI handling) that come with
  processing health information.
- Have a starting configuration (models, prompts, drug reference data) that is
  tuned toward healthcare terminology and a conservative, safety-first tone.
- Have synthetic sample data and tests to validate the shape of that
  configuration without touching any real patient data.

## 2. Healthcare-Specific Data Sources

A production healthcare RAG deployment typically ingests data from sources
such as:

| Category | Examples | Notes |
|---|---|---|
| Medical guidelines / protocols | CDC clinical guidance, FDA drug labeling and safety communications | Ingest as licensed/permitted; do not redistribute copyrighted text verbatim without checking the source's license/terms |
| Clinical trial information | ClinicalTrials.gov study records | Public domain in the US; still verify current terms of use |
| Drug / medication databases | FDA National Drug Code (NDC) directory, DailyMed, formulary data | Often requires licensing for commercial derivative products (e.g. First Databank, Medi-Span) |
| Disease/condition information | Patient education material from public health agencies | Attribute the source; keep current, since guidance changes |
| Patient consent forms | Organization-specific templates | Must be reviewed by legal/compliance before real use |
| Medical procedure descriptions | Plain-language descriptions of common procedures | Educational only, not a substitute for informed consent conversations with a clinician |
| Healthcare regulations/compliance docs | HIPAA, HITECH, state privacy law summaries | Summaries only; not a substitute for legal review |
| Insurance coverage guidelines | Payer coverage policies, medical necessity criteria | Frequently payer- and plan-specific; treat as illustrative unless sourced live from the payer |

See [`data/healthcare/`](../data/healthcare/) for **synthetic** examples of each
category's shape, and `config/drug_database.yaml` for an illustrative
medication-reference configuration.

## 3. HIPAA Compliance Requirements (General Concepts)

HIPAA (the Health Insurance Portability and Accountability Act) applies to
"covered entities" (health plans, healthcare clearinghouses, most healthcare
providers) and their "business associates" when they create, receive,
maintain, or transmit Protected Health Information (PHI). At a high level,
three HIPAA rules are most relevant to a RAG system:

- **Privacy Rule** — governs how PHI may be used and disclosed, and gives
  patients rights over their own information (access, amendment, accounting
  of disclosures).
- **Security Rule** — requires administrative, physical, and technical
  safeguards for *electronic* PHI (ePHI): access controls, audit controls,
  integrity controls, and transmission security.
- **Breach Notification Rule** — requires notifying affected individuals (and
  sometimes HHS and media) after a breach of unsecured PHI, on a defined
  timeline.

If a RAG system ingests real patient data, is hosted or supported by a
third party, or feeds a covered entity's workflow, that third party is
likely a **Business Associate** and needs a signed **Business Associate
Agreement (BAA)** before any real PHI is processed (including by a
cloud/LLM API vendor). This applies to embeddings and vector stores too —
storing PHI in a vector database still makes that data ePHI.

> This section is a simplified orientation, not a compliance checklist. Actual
> HIPAA applicability and obligations must be assessed by qualified legal
> counsel for your specific deployment.

## 4. Protected Health Information (PHI) Handling

### 4.1 What counts as PHI

PHI is individually identifiable health information. HIPAA's Safe Harbor
de-identification standard lists 18 identifier categories that, if present
alongside health information, generally make it PHI, including (non-exhaustive):
name; geographic subdivisions smaller than a state; dates directly related to
an individual (birth date, admission date, etc., other than year); phone/fax
numbers; email addresses; Social Security numbers; medical record numbers;
health plan beneficiary numbers; account numbers; certificate/license
numbers; vehicle identifiers; device identifiers; URLs; IP addresses;
biometric identifiers; full-face photos; and any other unique identifying
number, characteristic, or code.

### 4.2 Handling principles used in this repo's sample design

- **Never** commit real PHI to source control, logs, caches, or vector
  indexes — including in this repository's sample/test data (all sample data
  here is synthetic, see the disclaimer at the top of this file).
- Treat vector embeddings and any derived representations of PHI as PHI
  themselves — encryption and access-control obligations follow the data.
  Search index metadata (e.g., document titles containing patient names)
  is a common accidental PHI leak point, even when access controls exist on
  the underlying content.
- Separate identity fields from clinical content where feasible
  (pseudonymization), and keep the mapping between them in a separate,
  tightly access-controlled store.
- Apply **data minimization**: only ingest/retain the fields actually needed
  to answer the target queries.
- Define and enforce a retention/deletion policy consistent with
  organizational and legal requirements.

### 4.3 De-identification / anonymization approach

Two general HIPAA-recognized approaches to de-identification (again, general
concepts — confirm applicability with counsel/a qualified statistician):

1. **Safe Harbor** — remove all 18 identifier categories listed in §4.1 (and
   have no actual knowledge that the remaining information could identify an
   individual).
2. **Expert Determination** — a qualified expert applies statistical/
   scientific methods to determine the risk of re-identification is very
   small, and documents that analysis.

For a RAG pipeline specifically, a practical de-identification flow usually
looks like:

```
raw document/text
     │
     ▼
[PHI detection]  -- pattern/NER-based detection of names, dates, MRNs, etc.
     │
     ▼
[Redaction / tokenization] -- replace identifiers with structured tokens
     │                          (e.g. [PATIENT_NAME_1], [DATE_1]) or
     │                          synthetic surrogates
     ▼
[Re-identification key, if needed] -- stored separately, access-controlled,
     │                                 encrypted, audited
     ▼
de-identified text → chunking → embedding → vector store
```

This repository does not ship a PHI-detection model (that is out of scope for
a docs/config feature); the flow above is a design reference for an
implementer wiring in a PHI-detection library or service.

## 5. Data Privacy & Security Measures

General technical controls to consider for a real deployment (design
guidance, not a guarantee of compliance):

- **Encryption in transit**: TLS 1.2+ for all service-to-service and
  client-to-service traffic (API, vector DB, object storage, database,
  cache).
- **Encryption at rest**: encrypt the document store (e.g., MinIO/S3),
  relational database, and vector database volumes; use envelope encryption
  / a managed KMS where possible so key rotation doesn't require re-encrypting
  all data manually.
- **Secrets management**: never store API keys, DB passwords, or encryption
  keys in source control or plaintext `.env` files in production — use a
  secrets manager (e.g., Vault, AWS Secrets Manager) and inject at runtime.
- **Network isolation**: place data stores in a private network/VPC with no
  public ingress; expose only the API gateway, behind authentication.
- **Role-based access control (RBAC)** — see §6.
- **Audit logging** — see §7.
- **Backups**: encrypted, access-controlled, and tested for restore; backups
  of PHI are still PHI.

## 6. Role-Based Access Control (RBAC) Design Notes

A healthcare deployment typically needs, at minimum, these role categories
(names illustrative; map to your organization's actual roles):

| Role | Example permissions |
|---|---|
| `clinician` | Query patient-relevant clinical content; view sources; cannot modify ingestion config |
| `care_coordinator` | Query non-clinical content (coverage, scheduling); limited PHI field visibility |
| `compliance_officer` | Read audit logs; manage consent records; cannot query clinical content directly |
| `data_engineer` | Manage ingestion pipelines and configuration; access to de-identified data only, not raw PHI, wherever feasible |
| `system_admin` | Manage infrastructure/accounts; access should still be logged and does not imply a right to view PHI content |

Design principles:

- **Least privilege** — grant the minimum scope needed for a role's job
  function.
- **Attribute/context-aware access** — e.g., a clinician can query records
  for their own patient panel, not the entire population ("minimum necessary"
  standard under HIPAA).
- **Break-glass access** — emergency access procedures should exist but must
  be logged and reviewed after the fact.
- **Periodic access review** — revoke stale accounts/roles on a schedule.

This repository's existing `src/security/` module is a placeholder for
tenant isolation and auth; RBAC enforcement for healthcare roles would extend
that module in a real implementation and is intentionally out of scope for
this docs/config-focused change.

## 7. HIPAA Audit Logging

The Security Rule requires audit controls that record and examine activity in
systems containing ePHI. At minimum, an audit trail entry for a PHI-adjacent
event (e.g., a query that touches clinical content, a document upload/view)
should capture:

- Timestamp (UTC)
- Actor (user/service identity, role) — not necessarily the patient
- Action (e.g., `query`, `document_view`, `document_upload`, `export`)
- Resource identifier (e.g., document ID, query ID) — avoid putting PHI
  content itself into the log
- Outcome (success/failure, and reason for failures like access-denied)
- Source (originating service/IP, for forensic purposes)

Audit logs themselves must be protected (append-only/tamper-evident where
possible, access-restricted, retained per policy) since they can reveal
sensitive access patterns.

This repo includes a **lightweight, illustrative** audit-logging hook at
[`src/security/healthcare_audit_log.py`](../src/security/healthcare_audit_log.py).
It demonstrates the shape of an audit event and writes structured JSON lines
to a local file — it is a design reference, **not** a production-grade,
tamper-evident audit system (a real deployment should use a centralized,
write-once log store such as a SIEM or an append-only cloud log service).

## 8. Consent Management Notes

- Track, per patient/record, what the individual has consented to (e.g.,
  treatment, use of data for a RAG-based assistant, research use) with an
  effective date and an expiration/revocation mechanism.
- Support consent **withdrawal**, and propagate withdrawal to downstream
  systems (e.g., stop including a record in future retrieval indexes).
- Keep a versioned history of consent forms presented to the patient (see the
  synthetic template at
  [`data/healthcare/consent_forms/patient_consent_template.md`](../data/healthcare/consent_forms/patient_consent_template.md)),
  since the language patients agreed to may change over time.
- Consent scope should be granular where feasible (e.g., "may use for direct
  care" vs. "may use for research/analytics") rather than one blanket
  consent flag.

## 9. Clinical Data Integration Guidelines

- **Source vetting**: prefer authoritative sources (CDC, FDA, NIH,
  ClinicalTrials.gov, professional medical societies) and record provenance
  (source, URL, retrieval date, version) with every ingested document.
- **Currency**: clinical guidance changes; store an effective/last-verified
  date on each document and prefer surfacing the most recent guidance,
  including in retrieval ranking.
- **Human review**: clinical content changes should go through a review step
  before being indexed for retrieval, especially for anything
  treatment/dosage-adjacent.
- **Traceability**: every answer generated from clinical content should cite
  its source document(s) (see the existing `include_sources` behavior in
  `config/prompts.yaml`, mirrored in `config/healthcare_prompts.yaml`).
- **Non-diagnostic framing**: prompts and UI copy should make clear the
  system provides informational content, not a diagnosis or personalized
  treatment plan, and should direct urgent concerns to a clinician or
  emergency services.

## 10. Related Files

- [`docs/HEALTHCARE_EXAMPLES.md`](HEALTHCARE_EXAMPLES.md) — example queries and flows
- [`config/healthcare_models.yaml`](../config/healthcare_models.yaml) — healthcare-oriented model configuration
- [`config/healthcare_prompts.yaml`](../config/healthcare_prompts.yaml) — medical-terminology-aware prompts
- [`config/drug_database.yaml`](../config/drug_database.yaml) — illustrative/synthetic medication reference config
- [`data/healthcare/`](../data/healthcare/) — synthetic sample data
- [`.env.healthcare.example`](../.env.healthcare.example) — sample environment variables for a healthcare deployment
- [`src/security/healthcare_audit_log.py`](../src/security/healthcare_audit_log.py) — lightweight audit logging hook (illustrative)

## 11. Limitations

This guide and the accompanying configuration/sample data are **not**:

- A certified HIPAA-compliant system or a compliance guarantee of any kind.
- Medical advice, and not reviewed by a licensed medical professional.
- A substitute for a real risk assessment, legal review, and (where
  applicable) a signed Business Associate Agreement before processing real
  patient data.

Treat everything here as a documented starting point for engineering design
discussions, not an implementation you can deploy against real PHI as-is.
