# Security, Privacy & Vulnerability Disclosure Policy

## 1. Zero-Trust Security Invariants

**AgriStack DBT Core** is designed for sovereign Direct Benefit Transfer (DBT) and agricultural relief workflows where citizen privacy and financial integrity are non-negotiable. The architecture enforces four mandatory security invariants:

1. **Volatile RAM-Only PII Tokenization:** Raw citizen identifiers (Aadhaar numbers, Farmer IDs, mobile phone numbers) are converted into 64-character one-way SHA-256 HMAC pseudonyms at the Layer 2 Perimeter Security Gateway before any downstream language model, workflow engine, log sink, or database is invoked.
2. **In-Memory PII Purge Guard:** Free-text transcripts are scrubbed of residual personal identifiers in volatile memory, and runtime assertions reject any contract containing unredacted PII patterns.
3. **Adversarial Prompt & Content Firewall:** Untrusted voice transcripts and text inputs are scanned at the perimeter for prompt injection, system-instruction overrides, and illegal/manipulative payloads prior to entity extraction.
4. **Append-Only Audit Trail:** Governance state transitions are recorded automatically via relational database triggers into an append-only audit history table (`application_governance_ledger_history`) protected by `BEFORE UPDATE` and `BEFORE DELETE` database abort triggers.

---

## 2. Reporting a Vulnerability or Safety Issue

If you discover a security vulnerability, a PII redaction bypass, a prompt-injection vector, or a policy adjudication flaw, **do not open a public issue containing exploit details.**

Instead, please report it through one of the following channels:
1. **GitHub Private Vulnerability Reporting (Preferred):** Submit a confidential report via [`https://github.com/gargmishu/agristack-dbt-core/security/advisories/new`](https://github.com/gargmishu/agristack-dbt-core/security/advisories/new).
2. **Direct Maintainer Contact:** Contact the repository owner (**Mishu Garg**) via GitHub profile contact links (`https://github.com/gargmishu`).

### Response SLA
* **Acknowledgment:** Within **48 hours** of submission.
* **Triage & Severity Assessment:** Within **5 business days**.
* **Remediation & Patch Release:** Critical PII or adjudication bypasses are prioritized for patch release within **7 days** of verification.
