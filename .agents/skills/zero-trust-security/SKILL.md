---
name: zero-trust-security
description: Zero-Trust security rules, in-memory PII tokenization protocols, adversarial prompt injection defense, fail-fast secret enforcement, and core system security invariants. Use whenever handling citizen identifiers, auth validation, prompt security, cryptographic operations, or security invariants.
---

# Zero-Trust Security & Privacy Invariants

This document defines the security architecture, in-memory tokenization protocols, prompt injection firewalls, and core platform invariants for AgriStack.

---

## 1. Zero-PII Storage & RAM-Only Tokenization Invariant

### 1.1 Mandatory In-Memory Tokenization
* **Aadhaar Act §29 & National Privacy Mandate**: Cleartext Personally Identifiable Information (MSISDN phone numbers, 12-digit Aadhaar UID numbers, cleartext names) is **strictly forbidden from touching persistent disk storage or database ledgers**.
* **Layer 2 Perimeter Tokenization**: One-way SHA-256 HMAC tokenization (`ZeroTrustIdentityTokenizer`) occurs strictly in volatile RAM at the Layer 2 ingestion boundary using a secret cryptographic pepper.
* **Downstream Contracts**: All Layer 3 and Layer 4 schemas must operate exclusively on pseudonymous 64-character lowercase hex tokens (`HmacCitizenToken`).

### 1.2 PII Purge Sentinel & Ingress Redaction
* Free-text message bodies (e.g. WhatsApp, SMS) must be passed through `PiiPurgeGuard.redact_all()` to replace cleartext phone numbers and Aadhaar UIDs with `[REDACTED]` before leaving Layer 2.
* `PiiPurgeGuard.assert_zero_pii()` must be asserted on all standardized intake payloads before handing off to Layer 3.

---

## 2. Fail-Fast Cryptographic Configuration

* **Never Hardcode Secrets**: Never define fallback cryptographic keys, pepper defaults, or placeholder bearer tokens in code.
* **Fail Fast on Missing Secrets**: If an environment-injected secret (e.g. `PEPPER_SECRET`, `APP_SECRET`, carrier bearer token) is missing or empty, fail fast immediately with an explicit exception (`ValueError` or `RuntimeError`). Never fall back to insecure default strings.

---

## 3. Adversarial Prompt Injection Defense & Confidence Zeroing

### 3.1 Perimeter Pre-Inspection
* `AdversarialPromptFirewall` inspects text inputs at the Layer 2 boundary against threat categories:
  * `SYSTEM_OVERRIDE`: Attempts to disregard instructions or safety bounds.
  * `ROLE_USURPATION`: Attempts to alter persona or claim administrative privilege.
  * `DELIMITER_HIJACKING`: Attempts to break structured formatting boundaries.
  * `DATABASE_INJECTION`: SQL / query injection patterns.
  * `PAYOUT_MANIPULATION`: Commands attempting to force approvals or change amounts.

### 3.2 Security Zeroing Invariant (`0.0` vs `0.40`)
* **`0.0` Confidence Score**: Strictly reserved for **Security Zeroing** on adversarial prompt injection attacks (`is_adversarial_attempt=True`). This immediately routes the claim to the security threat triage queue.
* **`0.40` Confidence Score**: Represents benign low model confidence or unparseable audio (ambient farm noise, dialect mismatch, transcription timeout). This routes safely to the standard caseworker review queue (`ROUTE_FOR_MANUAL_REVIEW`) without raising false security alarms.

---

## 4. Core System Invariants

1. **Identity Invariant**: Zero cleartext PII in Layer 3 and Layer 4 contracts.
2. **Auditability Invariant**: Every human manual adjudication must reference the escalation ticket ID (`SPP-CASE-YYYY-XXXXXX`) and carry officer audit notes (`review_notes`).
3. **Financial Clearing Invariant**: Payout transaction IDs (`disbursement_txn_id`) and status exist ONLY for approved outcomes; rejection reason codes exist ONLY for rejected outcomes. Financial states move forward monotonically (`PENDING` $\rightarrow$ `INITIATED` $\rightarrow$ `SUCCESS`/`FAILED`). Reversion is strictly forbidden.
4. **Anti-Double-Dipping Ledger Invariant**: Duplicate claims within the same `CropSeason` for an already-approved citizen token must be deterministically rejected (`DUPLICATE_CLAIM_ACTIVE_SEASON`).

---

## 5. Exhaustive Matrix & Parametrization Testing

* **100% Enum Coverage**: State machine models, validators, and routers must use `@pytest.mark.parametrize` across 100% of Enum members to verify required, optional, and forbidden fields for every state.
* **Timing-Safe Cryptographic Comparisons**: Webhook signature verification and bearer token checks must always use `secrets.compare_digest()` to prevent timing side-channel attack vectors.
