# Finance RAG Pipeline — Worked Examples

> **SAMPLE DATA — fictional, for testing/demo purposes only. Not real
> regulatory text, not investment advice, not reviewed by a compliance or
> legal professional.** All company/fund names below (e.g., "Meridian
> Capital Partners", "Northbridge Advisory Group", "Solara Biotech Inc.",
> "Cascade National Bank") are fictional placeholders invented for this
> repository. A real deployment must consult qualified legal/compliance
> counsel and official regulator publications.

This document shows worked query → context → answer examples for each
domain feature listed in `docs/FINANCE_RAG_GUIDE.md` Section 3, using the
synthetic sample data under `data/finance/` and the prompt configuration in
`config/finance_prompts.yaml`.

---

## 1. Regulatory Query Example (Regulatory Compliance Checking)

**Query:** "What is the general concept behind periodic disclosure
requirements for public companies?"

**Retrieved context** (`data/finance/regulation_summaries.json`,
`reg_summary_001`):
> General concept: Public companies are generally expected to file periodic
> reports (such as annual and quarterly reports) that disclose their
> financial condition, results of operations, and material events that could
> affect an investor's decision to buy, hold, or sell the company's
> securities. Illustrative example: 'Meridian Capital Partners' (a fictional
> company used for this example) would be expected to file an annual report
> summarizing its fiscal year results...

**Answer:**
> Public companies are generally expected to periodically disclose their
> financial condition and material events — for example through annual and
> quarterly reports — so investors have current information to make buy,
> hold, or sell decisions. (Source: regulation_summaries.json,
> reg_summary_001 — a fictional, simplified summary, not real SEC text.)
> This is general information, not legal advice.

---

## 2. Financial Product Info Retrieval Example

**Query:** "What are the principal risks of the Meridian Capital Partners
Balanced Growth Fund?"

**Retrieved context** (`data/finance/product_prospectuses.json`,
`prospectus_001`):
> Principal Risks (illustrative): market risk, interest rate risk, equity
> volatility risk, credit risk of bond issuers.

**Answer:**
> According to the fictional prospectus excerpt, the fund's principal risks
> include market risk, interest rate risk, equity volatility risk, and
> credit risk from its bond holdings. (Source: product_prospectuses.json,
> prospectus_001 — a fictional fund used for this example.) This is not
> investment advice — consult the actual fund's official prospectus and a
> licensed advisor before investing in any real product.

---

## 3. Compliance Checking Example (Compliance Document Search)

**Query:** "What does our fictional KYC onboarding policy say about
enhanced due diligence?"

**Retrieved context** (`data/finance/compliance_policies.json`,
`policy_template_001`):
> Apply enhanced due diligence for higher-risk profiles (e.g., politically
> exposed persons), per firm policy.

**Answer:**
> The fictional KYC onboarding policy template calls for enhanced due
> diligence to be applied to higher-risk customer profiles, such as
> politically exposed persons. (Source: compliance_policies.json,
> policy_template_001 — a fictional template for Meridian Capital Partners,
> a fictional firm.) This is a simplified illustrative template, not a
> complete or compliant policy — consult compliance counsel for actual
> policy design.

---

## 4. Risk Assessment Workflow Example

**Query:** "What's the difference between market risk and credit risk, and
which fictional sample document discusses trading controls related to
material nonpublic information?"

**Retrieved context** (`config/finance_prompts.yaml` few-shot example +
`data/finance/trading_rules.json`, `trading_rule_003`):
> Market risk is the risk of losses due to changes in market prices...
> Credit risk is the risk that a borrower or counterparty fails to meet its
> financial obligations... [and] Firms commonly maintain a restricted list
> or watch list of securities for which employee or firm trading is limited
> or monitored, often because the firm possesses or may possess material
> nonpublic information about the issuer.

**Answer:**
> Market risk arises from changes in market prices (rates, equities, FX),
> while credit risk arises from a counterparty failing to meet its
> obligations — both are core categories in a risk management framework.
> Separately, the fictional trading-rule sample `trading_rule_003` describes
> a general "restricted list" control: firms often limit or monitor employee
> trading in a name when the firm may possess material nonpublic information
> about that issuer (illustrated with fictional firm "Meridian Capital
> Partners" and fictional issuer "Solara Biotech Inc."). This is general
> information, not investment or legal advice.

---

## 5. Trading Rule Verification Example

**Query:** "Under the fictional pattern-day-trading example, how many day
trades in five business days would flag an account?"

**Retrieved context** (`data/finance/trading_rules.json`,
`trading_rule_001`):
> A fictional customer account at 'Northbridge Advisory Group' ... that
> executes four or more day trades in five business days, where those trades
> are more than 6% of total trades in that window, might be flagged as a
> pattern day trader under the firm's internal policy.

**Answer:**
> In the fictional illustrative example, four or more day trades within a
> rolling five-business-day window (where those trades exceed 6% of total
> trading activity in that window) would flag the account under the firm's
> internal pattern-day-trading policy. (Source: trading_rules.json,
> trading_rule_001 — fictional firm "Northbridge Advisory Group.") This is a
> simplified illustrative example, not the real regulatory threshold —
> confirm actual thresholds with your broker-dealer's compliance department.

---

## 6. KYC Info Lookup Example

**Query:** "What is KYC and why is it required?"

**Retrieved context** (`data/finance/finance_qa.json`, `finance_qa_001`):
> KYC (Know Your Customer) is the process a financial firm uses to verify a
> client's identity and understand their financial background and risk
> profile before and during a business relationship.

**Answer:**
> KYC is the process a financial firm uses to verify a client's identity and
> assess their financial background/risk profile, generally required as
> part of anti-money-laundering (AML) compliance obligations. (Source:
> finance_qa.json, finance_qa_001.) This is general information, not legal
> advice.

---

## 7. AML Check Example

**Query:** "What is a Suspicious Activity Report (SAR) and when might one be
filed, per our fictional AML policy template?"

**Retrieved context** (`data/finance/compliance_policies.json`,
`policy_template_002`):
> Route flagged transactions to a compliance analyst for manual review...
> escalate confirmed concerns for a suspicious activity report (SAR) filing
> decision.

**Answer:**
> Per the fictional AML transaction-monitoring policy template, a
> transaction is first automatically flagged by monitoring rules, then
> reviewed by a compliance analyst, and if concerns are confirmed it is
> escalated for a SAR filing decision. (Source: compliance_policies.json,
> policy_template_002 — fictional firm "Northbridge Advisory Group.") Any
> real lookup of a specific customer/account in this workflow should go
> through the audit-logging hook described in `docs/FINANCE_RAG_GUIDE.md`
> Section 6, and is not legal guidance on actual SAR obligations.

---

## 8. Investment Suitability Analysis Example

**Query:** "What factors go into a suitability assessment before
recommending a complex product like the Cascade National Derivatives Access
ETF?"

**Retrieved context** (`data/finance/compliance_policies.json`,
`policy_template_004` + `data/finance/product_prospectuses.json`,
`prospectus_003`):
> Capture the customer's stated risk tolerance, time horizon, liquidity
> needs, and investment experience. Compare the proposed product's
> risk/complexity profile against the customer's profile... [and] This
> product is generally intended for investors who understand options
> strategies; suitability should be assessed per firm policy before
> recommendation.

**Answer:**
> A suitability assessment generally weighs the customer's risk tolerance,
> time horizon, liquidity needs, and investment experience against the
> product's risk/complexity — and for a derivatives-linked product like the
> fictional Cascade National Derivatives Access ETF, the fictional
> prospectus itself flags that it's generally intended for investors who
> understand options strategies. (Sources: compliance_policies.json
> policy_template_004; product_prospectuses.json prospectus_003.) This is
> not investment advice — a real suitability determination must be made by a
> licensed professional per applicable rules.

---

## 9. Tax Implications Lookup Example

**Query:** "In general terms, why might the holding period of an investment
matter for tax purposes?"

**Retrieved context:** No bundled sample tax document exists by default in
this repository (see `docs/FINANCE_RAG_GUIDE.md` Section 3, item 9) — this
example shows the expected *fallback* behavior when no matching document is
retrieved.

**Answer:**
> I don't have enough information to answer this question from the
> currently ingested documents. In general, tax treatment can depend on how
> long an investment is held (e.g., short-term vs. long-term categories in
> some tax systems), but you should consult a qualified tax professional or
> the applicable tax authority's guidance for your specific situation — this
> is not tax advice.

This demonstrates the system prompt's required behavior from
`config/finance_prompts.yaml`: when retrieved context doesn't cover the
question, say so rather than fabricating an answer.

---

## Summary Table

| # | Feature | Sample source file(s) |
|---|---|---|
| 1 | Regulatory compliance checking | `data/finance/regulation_summaries.json` |
| 2 | Financial product info retrieval | `data/finance/product_prospectuses.json` |
| 3 | Compliance document search | `data/finance/compliance_policies.json` |
| 4 | Risk assessment workflow | `config/finance_prompts.yaml`, `data/finance/trading_rules.json` |
| 5 | Trading rule verification | `data/finance/trading_rules.json` |
| 6 | KYC info lookup | `data/finance/finance_qa.json` |
| 7 | AML checks | `data/finance/compliance_policies.json` |
| 8 | Investment suitability analysis | `data/finance/compliance_policies.json`, `data/finance/product_prospectuses.json` |
| 9 | Tax implications lookup (fallback behavior) | none bundled — illustrates "I don't have enough information" |
