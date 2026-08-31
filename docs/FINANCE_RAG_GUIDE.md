# Finance Industry RAG Pipeline Guide

> **SAMPLE / REFERENCE DOCUMENTATION** — This guide, and every sample document,
> config file, and code hook it references, is fictional/demo material for
> testing and documentation purposes only. Nothing here is real regulatory
> text, real investment advice, or a certified compliance program. A real
> finance deployment must be reviewed and signed off by qualified legal,
> compliance, and security professionals before handling real customer or
> regulatory data.

## 1. Overview

This guide documents how to configure and reason about a **finance industry
profile** of the RAG pipeline: regulatory/compliance document retrieval,
financial product information lookup, trading-rule verification, and related
domain queries. It is intentionally a **docs + config + sample-data** feature
— it does not add a new ML model or compliance engine. It builds on top of
the existing RAG pipeline (`src/rag/`, `src/search/`, `src/ingestion/`)
using finance-specific configuration and sample data.

Related files:
- `config/finance_models.yaml` — finance-optimized model profile (follows the
  format of `config/models.yaml`).
- `config/finance_prompts.yaml` — finance system prompt, terminology list,
  and few-shot examples (follows the format of `config/prompts.yaml`).
- `config/regulations.yaml` — regulatory body and topic reference data used
  to tag/route finance documents and queries.
- `config/finance.env.example` — sample environment variables for a finance
  deployment.
- `data/finance/` — synthetic sample data (regulation summaries, product
  prospectuses, trading rules, compliance policy templates, Q&A pairs).
- `src/compliance/audit_log.py` — lightweight audit-logging hook (see
  Section 6).
- `docs/FINANCE_EXAMPLES.md` — worked query examples across each domain
  feature below.

## 2. Finance-Specific Data Sources (Scope)

A finance deployment of this RAG pipeline is expected to ingest documents
such as:

| Category | Examples |
|---|---|
| Regulatory documents | SEC filings/guidance, FINRA rule notices, OCC bulletins |
| Financial product documentation | stock/bond/derivative product sheets, prospectuses |
| Trading rules & regulations | settlement rules, pattern-day-trading rules, best execution |
| Compliance guidelines/policies | KYC/AML policies, suitability policies, restricted lists |
| Risk management frameworks | market/credit/liquidity/operational risk frameworks |
| Financial reporting standards | GAAP, IFRS reference material |
| Investment prospectuses | mutual fund, ETF, bond offering prospectuses |
| Tax guidance documents | general tax-treatment reference material |
| KYC/AML policies & procedures | onboarding, due diligence, transaction monitoring |

This repository ships **synthetic samples** of each category under
`data/finance/` (see Section 5) so the pipeline and tests have something
concrete to ingest and query, without touching real regulatory data.

## 3. Domain-Specific Features

These are documented capabilities of the finance profile, built from the
existing generic RAG pipeline plus finance configuration/prompting — this
feature does **not** add new ML models or a rules engine:

1. **Regulatory compliance checking** — retrieval-augmented Q&A over
   `config/regulations.yaml` and `data/finance/regulation_summaries.json`,
   using `config/finance_prompts.yaml`'s system prompt to avoid fabricated
   citations.
2. **Financial product info retrieval** — retrieval over
   `data/finance/product_prospectuses.json`.
3. **Trading rule verification** — retrieval over
   `data/finance/trading_rules.json`.
4. **Compliance document search** — retrieval over
   `data/finance/compliance_policies.json`.
5. **Risk assessment queries** — retrieval over risk-framework terminology in
   `config/finance_prompts.yaml` (`financial_terminology.risk_terms`) and any
   ingested risk-framework documents.
6. **Investment suitability analysis** — retrieval over the suitability
   policy template in `data/finance/compliance_policies.json`, always paired
   with the "not investment advice" reminder from the system prompt.
7. **KYC info lookup** — retrieval over KYC content in
   `data/finance/compliance_policies.json` and `data/finance/finance_qa.json`.
8. **AML checks** — retrieval over AML content in the same sample sets, plus
   the audit-logging hook in Section 6 for any lookup involving a specific
   customer/account.
9. **Tax implications lookup** — retrieval over general tax-guidance
   reference material an operator ingests (no synthetic tax data is bundled
   by default; add documents under `data/finance/` following the same JSON
   shape and disclaimer pattern).

See `docs/FINANCE_EXAMPLES.md` for worked examples of each.

## 4. Regulatory Compliance Requirements

> The following is a general, non-authoritative summary written for this
> project's documentation. It is not legal or compliance guidance. Always
> consult the regulator's official publications and qualified counsel.

### SEC / FINRA considerations
- **No fabricated citations**: the finance system prompt
  (`config/finance_prompts.yaml`) explicitly instructs the model to say when
  a specific rule/citation isn't present in retrieved context rather than
  guessing — this matters because a fabricated regulatory citation is worse
  than no answer.
- **Recordkeeping**: SEC/FINRA-regulated firms are commonly subject to
  record-retention obligations for communications and books/records
  (illustratively referenced by the long default retention window in
  `config/finance.env.example`'s `FINANCE_AUDIT_LOG_RETENTION_DAYS`). A real
  deployment must set retention per its actual regulatory obligations, not
  this repo's placeholder default.
- **Suitability**: any response touching investment recommendations should
  carry the "not investment advice" disclaimer configured via
  `response_format.include_advice_disclaimer` in `config/finance_prompts.yaml`.

### Financial data security / encryption
- Sensitive financial data (account numbers, SSNs/TINs, transaction detail)
  must be encrypted **at rest** (database/object storage volume encryption)
  and **in transit** (TLS). These are infrastructure-layer controls; the
  `FINANCE_ENCRYPTION_AT_REST_REQUIRED` / `FINANCE_ENCRYPTION_IN_TRANSIT_REQUIRED`
  flags in `config/finance.env.example` document the *intent*, they do not
  themselves implement encryption.
- PII should be masked wherever full values aren't required (see
  `mask_sensitive_text()` in `src/compliance/audit_log.py`, which masks
  SSN-shaped and long account-number-shaped sequences before writing any
  audit preview).

### Audit trail / logging requirements
- Every finance query that touches a specific customer/account should be
  logged with: timestamp, user id, tenant id, role, a masked query preview,
  and the ids of documents returned — never the full query text or raw
  sensitive values. See `FinanceAuditLogger` in `src/compliance/audit_log.py`.
- Audit logs themselves should be append-only and access-controlled; the
  logger fails safe (a log write failure returns `False` rather than raising
  into the request path) so audit logging can never take down a user-facing
  query, but failures should be alerted on (`FinanceAuditLogger.write_failures`).

### Sensitive financial information handling
- Treat account numbers, SSNs/TINs, and full transaction detail as sensitive
  by default. Prefer masked/partial values in responses and logs (e.g.,
  "account ending 4321") unless the specific query requires the full value
  for the user's own record lookup and the requester is authorized.
- Do not include sensitive values in prompts/logs beyond what's needed to
  answer the query.

## 5. Sample Data & Test Data

All sample data lives under `data/finance/` and is JSON, each file carrying
a top-level `disclaimer` key plus a list of records:

| File | Content |
|---|---|
| `regulation_summaries.json` | 5 synthetic SEC/FINRA/OCC/FinCEN-style regulation summaries (concepts described in our own words, not real rule text) |
| `product_prospectuses.json` | 3 fictional financial product prospectus excerpts (fund, bond, ETF) |
| `trading_rules.json` | 4 fictional trading-rule concept write-ups (day trading, settlement, restricted list, best execution) |
| `compliance_policies.json` | 4 fictional compliance policy templates (KYC onboarding, AML monitoring, data handling, suitability review) |
| `finance_qa.json` | 8 finance Q&A examples covering the domain features in Section 3 |

Every company/fund name in the sample data is a fictional placeholder (e.g.,
"Meridian Capital Partners", "Northbridge Advisory Group", "Solara Biotech
Inc.", "Cascade National Bank") explicitly labeled as fictional in the text,
and every CUSIP/account/ticker is a clearly fake placeholder value.

## 6. Compliance & Regulatory Design Notes

These are **design notes**, not a certified implementation, intended to
orient engineers extending this feature toward production readiness.

### Audit logging
See `src/compliance/audit_log.py` (`FinanceAuditLogger`). Design: append-only
JSON Lines, masked previews only, fail-safe writes. Configured via
`FINANCE_AUDIT_LOGGING_ENABLED`, `FINANCE_AUDIT_LOG_PATH`, and
`FINANCE_AUDIT_LOG_RETENTION_DAYS` in `config/finance.env.example`.

### Role-based access control (RBAC)
Illustrative roles (`config/finance.env.example`: `FINANCE_RBAC_ROLES`):
`analyst`, `compliance_officer`, `auditor`, `admin`. Design intent:
- `analyst`: query finance documents, no access to raw PII fields.
- `compliance_officer`: query + view audit logs for their tenant.
- `auditor`: read-only access to audit logs across tenants (for real audits).
- `admin`: configuration changes only, not routine query access.

This repository does not implement role enforcement (no auth layer changes
were made) — this section documents the intended role model for whoever
wires it into the existing `src/security/` tenant-isolation layer.

### Data encryption for PII/financial data
See Section 4's "Financial data security / encryption" above. Application
flags (`FINANCE_ENCRYPTION_AT_REST_REQUIRED`, etc.) document intent; actual
encryption must be implemented at the infrastructure layer (encrypted
Postgres/MinIO volumes, TLS termination at the load balancer/ingress).

### Regulatory audit trail
Audit log entries (Section "Audit logging" above) form the basis of a
regulatory audit trail: who queried what, when, and which documents were
returned. A production system should also log configuration changes
(model swaps, prompt changes) with the same append-only pattern.

### SOX / SOC2 compliance logging
SOX and SOC2 both generally expect change-management and access-logging
evidence. The audit-log hook's structured, append-only design is meant to be
a starting point for that evidence trail (e.g., feed it into a SIEM or
log-aggregation system), not a complete SOX/SOC2 control set.

### GLBA privacy compliance
The Gramm-Leach-Bliley Act (GLBA), in general concept, expects financial
institutions to explain their data-sharing practices and safeguard customer
financial information. Practical implications for this pipeline: minimize
what's logged (Section "Audit logging"), mask sensitive values by default,
and restrict access via RBAC (above).

### Transaction monitoring
Out of scope for this docs/config feature as an implemented system, but
`data/finance/compliance_policies.json`'s AML policy template and
`config/regulations.yaml`'s `kyc_aml` topic entry describe the general
pattern (automated flagging → analyst review → SAR decision → retention)
that a real transaction-monitoring integration would follow.

## 7. Getting Started

```bash
# Copy finance env sample into your own .env-based config as needed
cat config/finance.env.example

# Point the pipeline at the finance model/prompt profile (illustrative):
export LLM_MODEL=qwen_32b_finance
export FINANCE_PROMPTS_CONFIG_PATH=config/finance_prompts.yaml

# Sample data is ready to ingest under data/finance/
ls data/finance/
```

See `docs/FINANCE_EXAMPLES.md` for worked query examples.
