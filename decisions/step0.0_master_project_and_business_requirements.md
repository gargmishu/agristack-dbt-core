# Step 0.0: AgriStack DBT Core — Master Project & Business Requirements Specification

## 1. Executive Summary & Core Project Mandate

### 1.1 Project Vision & Purpose
**AgriStack Direct Benefit Transfer Core (`agristack-dbt-core`)** is an enterprise-grade, sovereign social benefit disbursement, governance routing, multi-channel conversational ingestion, zero-trust PII tokenization, and automated payment clearance engine.

The system automates direct benefit transfers (DBT) for agricultural schemes (e.g., PM-KISAN, Disaster Relief, Seasonal Crop Loss Compensation) across India by integrating sovereign Digital Public Infrastructure (DPI) rails—including MOSIP Identity, AgriStack Land Registries, OpenSPP Social Protection, and NPCI Aadhaar Payment Bridge System (APBS).

### 1.2 Governing Mandate & Legal Basis
* **Governing Agency:** State Department of Agriculture & Farmer Welfare / Ministry of Social Welfare.
* **Legal Mandate:** Sovereign Seasonal Relief & DBT Payment Authorization Order, 2023 / Social Protection Act § 12.3.
* **Audit & Retention Policy:** 5-year immutable audit log retention; institutional authority remains with sovereign government entities.

### 1.3 Core Business Principles & Non-Negotiable Rules
1. **Zero-PII Privacy (Zero-Disk RAM Masking):** Citizens are identified exclusively via 64-character SHA-256 HMAC tokens (`tokenized_phone_hash`, `tokenized_identity_hash`). Raw PII (Aadhaar, cleartext MSISDN, unhashed names) is strictly forbidden across all database ledgers and persistent schemas.
2. **Double-Dipping Fraud Prevention:** Before issuing an approval, the system enforces a database-level check on `(tokenized_identity_hash, scheme_season)` to guarantee a citizen cannot claim duplicate payouts in the same season.
3. **Monotonic Forward-Only Financial State Machine:** Financial clearing states (`DisbursementStatus`) move strictly forward (`PENDING` $\rightarrow$ `INITIATED` $\rightarrow$ `SUCCESS`/`FAILED`/`RETURNED`). Reversion (e.g. `INITIATED` $\rightarrow$ `PENDING`) is strictly forbidden to prevent double-payouts.
4. **Decoupled Governance vs. Financial Clearance:** Governance decisions (`AUTO_APPROVE` / `MANUAL_APPROVE`) finalize claim eligibility and issue an idempotent tracking key (`disbursement_txn_id`) with `disbursement_status = PENDING`. Downstream payment dispatchers execute bank clearing asynchronously over NPCI/PFMS rails.
5. **100% Audit Traceability:** Every manual human caseworker action requires an Officer UUID (`reviewer_id`) and non-whitespace justification notes (`review_notes`) recorded in an append-only audit ledger (`application_governance_ledger_history`).

---

## 2. Multi-Channel Ingress & Conversational Experience Requirements (Layer 1)

### 2.1 Supported Ingress Channels
The platform provides a unified, inclusive interface catering to farmers of all digital literacy levels:

| Channel Type | Interface / Protocol | Input Format | Audio / Processing Profile |
| :--- | :--- | :--- | :--- |
| **`IVR_VOICE`** | SIP Trunk / SS7 Gateways (`SIP_TRUNK_BSNL_HAR_08`) | Vernacular Speech Streams | Mono 16kHz 16-bit PCM; Agricultural Background Noise Attenuation |
| **`WHATSAPP`** | Meta WhatsApp Business API | Text & Voice Notes | Natural Language Text / Signed Audio URLs |
| **`USSD`** | SS7 / SIGTRAN Carrier Gateway | DTMF / Structured Menu Strings | Compact Key-Value Payloads (`ussd_collected_payload`) |
| **`WEB_PORTAL` / `MOBILE_APP`** | HTTPS REST API / Gateway | JSON Payloads | Structured Application Payloads |

### 2.2 Vernacular Speech & Language Processing Pipeline
For `IVR_VOICE` and `WHATSAPP` channels, raw input undergoes multi-stage AI translation:
1. **Speech-to-Text Transcription:** Converts regional acoustic streams into written vernacular script using Bhashini ASR (e.g., Hindi `hi-IN`).
2. **Text Translation & Normalization:** Translates local idioms, regional dialects (e.g., Regional Haryanvi Hindi), and agricultural terminology into standardized administrative English using Bhashini NMT.
3. **Adversarial Ingestion Safeguard:** If acoustic anomalies or prompt injection patterns are detected, security interceptors force the extraction confidence score to `0.00`, routing the session to human review.

### 2.3 Conversational Re-Prompt & Drop-off Prevention
* **Adaptive Re-prompt Loop:** If AI extraction confidence is low ($<0.85$) and attempts $< 3$, governance evaluation triggers conversational re-prompts through the Outbound Notification Engine, re-prompting the citizen over WhatsApp/SMS for missing or ambiguous fields.
* **Drop-off Prevention Index:** Partial index `idx_active_session_resume` on `session_telemetry_log` allows citizens who disconnect mid-conversation to resume their active session seamlessly within a 10-minute window.
* **USSD Hard Fallback:** USSD sessions cannot execute multi-turn re-prompts; low-confidence USSD claims route immediately to Caseworker Incident Staging.

---

## 3. Zero-Trust Security, Privacy & Consent Requirements (Layer 2)

### 3.1 Zero-PII Tokenization Architecture
To comply with sovereign data privacy regulations (DPDP Act / GDPR principles):
* **hashing_algorithm:** SHA-256 with environment-injected salt & pepper (`ENV_INJECTED_SYSTEM_PEPPER_KEY`).
* **RAM Masking:** Raw identifiers (Aadhaar / MSISDN) are held in volatile RAM only during tokenization and zero-masked before writing telemetry to disk.
* **Token Format:** `tokenized_citizen_id` and `tokenized_identity_hash` must be exact 64-character hex strings.

### 3.2 Consent Registry & Provenance Audit (`consent_registry`)
Before any citizen data is processed or cross-matched against registries:
1. **Explicit Opt-in:** Requires explicit channel-native consent (WhatsApp button click "I Accept", IVR DTMF digit `1`, USSD digit `1`).
2. **Session-Bound Expiration:** Consent is valid for the active session and automatically expires after 10 minutes (`expires_at = NOW() + INTERVAL '10 minutes'`).
3. **Consent Scope:** `IDENTITY_VERIFICATION` and `DATA_PROCESSING`.
4. **Non-PII Provenance Metadata:** Captures consent method, policy version, device fingerprint, and confirmation receipt without storing raw IP addresses or PII.
5. **Revocation Rights:** Citizens or system triggers can set `consent_status = REVOKED` with `revocation_reason` (`EXPLICIT_USER_REVOCATION`, `NATURAL_EXPIRATION`).

---

## 4. Analytical Data Transformation & Deduplication (Layer 3)

### 4.1 Analytics Staging Compaction
When citizens re-engage across multiple conversational attempts, multi-turn inputs generate intermediate state mutations.

* **Target Analytics Model:** `stg_session_extraction_details`
* **Compaction Logic:** Compiles and materializes the latest accepted extraction payload (`COMMITTED` state), filtering out `SUPERSEDED` attempts before sovereign registry cross-matching.
* **Deduplication Guarantee:** Ensures downstream matching queries operate strictly on clean, compacted citizen assertions.

---

## 5. Sovereign DPI Registry Cross-Matching & Staging (Layer 4)

### 5.1 SLM Entity Extraction
Localized Small Language Model extracts structured domain parameters:
* `district_name` (e.g., `"Karnal"`)
* `crop_type` (e.g., `"Paddy / Wheat"`)
* `survey_number` / `cadastral_plot_id`
* `reported_anomaly` / `crop_loss_percentage`
* `claimed_amount`

### 5.2 Federated AgriStack Registry Matching
Cross-examines citizen assertions against federated sovereign registries:
* **Strict Geographic Boundary Intersection:** Verifies parcel boundaries, land ownership deed, and seasonal crop survey data.
* **Output:** `registry_match_flag = true/false` and `cadastral_plot_id`.

### 5.3 OpenSPP Social Benefits Staging
When `registry_match_flag == true`, verified parameters are staged into the OpenSPP Social Protection Platform core registry, generating a unique `openspp_case_id`.

---

## 6. Governance Routing, Adjudication & Ledger Requirements (Layer 5)

### 6.1 Threshold Evaluation Gate
The rules engine evaluates claim criteria against state policy gates:

```text
evaluation_passed = (ai_confidence_score >= 0.85) and (registry_match_flag == True)
```

```
                       ┌──────────────────────────────┐
                       │ Threshold Evaluation Gate    │
                       └──────────────┬───────────────┘
                                      │
               ┌──────────────────────┴──────────────────────┐
               │ evaluation_passed == true                   │ evaluation_passed == false
               ▼                                             ▼
┌──────────────────────────────┐              ┌──────────────────────────────┐
│  Claim Policy Adjudicator    │              │  Claim Policy Adjudicator    │
│  (FORWARD_TO_AUTOMATED_PAYOUT│              │(FORWARD_TO_INCIDENT_STAGING) │
└──────────────┬───────────────┘              └──────────────┬───────────────┘
               │                                             │
               ▼                                             ▼
┌──────────────────────────────┐              ┌──────────────────────────────┐
│  Automated Payout Rails      │              │ Incident Ticket Staging      │
│   (NPCI APBS / PFMS Rail)    │              │ (SPP-CASE-2026-XXXX)         │
└──────────────────────────────┘              └──────────────┬───────────────┘
                                                             │
                                                             ▼
                                              ┌──────────────────────────────┐
                                              │ Caseworker Review Dashboard  │
                                              │ (MANUAL_APPROVE / REJECT /   │
                                              │    REQUEST_MORE_INFO)        │
                                              └──────────────────────────────┘
```

---

### 6.2 Governance Decisions & Payload Validation Contracts

#### A. Governance Determination Contract
Emitted when Layer 4 Orchestrator or Caseworker Adjudication finalizes a governance decision.

| Contract Attribute | Type / Constraints | Description |
| :--- | :--- | :--- |
| `session_id` | UUID string | Ingress communication session identifier |
| `payload_id` | Extraction Payload ID | Pointer to the accepted entity extraction payload |
| `ai_confidence_score` | Float ($0.0 \dots 1.0$) | Weighted confidence score from SLM extraction |
| `eligibility_status` | Enum (`ELIGIBLE`, `INELIGIBLE`, `REQUIRES_FURTHER_REVIEW`, `UNKNOWN`) | Verified eligibility state against DPI registries |
| `governance_action` | Enum (`AUTO_APPROVE`, `MANUAL_APPROVE`, `AUTO_REJECT`, `MANUAL_REJECT`, `REQUEST_MORE_INFO`, `ROUTE_FOR_MANUAL_REVIEW`, `AUTOMATED_PAYOUT`, `HUMAN_REVIEW`) | Final governance action determined by policy matrix |
| `disbursement_txn_id` | Idempotency Key (Optional) | Unique transaction ID generated at approval time |
| `disbursement_status` | Enum (Optional) | Initial clearing state (`PENDING` / `INITIATED`) |
| `escalation_case_id` | Case Ticket ID (Optional) | Human review incident ID (`SPP-CASE-YYYY-XXXXXX`) |
| `rejection_reason` | String (Optional) | Non-empty rationale for rejections |
| `review_notes` | String (Optional, max 2000 chars) | Internal caseworker audit rationale |
| `evaluated_at` | UTC Timestamp | Adjudication completion timestamp |

##### Decision Validation Matrix:
1. **`AUTO_APPROVE` / `AUTOMATED_PAYOUT` (Zero-Touch Straight-Through Processing):**
   * `disbursement_txn_id` **required** (Idempotency key).
   * `disbursement_status` **required** (`PENDING` or `INITIATED`).
   * `rejection_reason`, `escalation_case_id`, `review_notes` **must be `None`**.
2. **`MANUAL_APPROVE` (Human-in-the-Loop Approval):**
   * `disbursement_txn_id` **required** (Generated by treasury adapter).
   * `disbursement_status` **required** (`PENDING` or `INITIATED`).
   * `escalation_case_id` **required** (`SPP-CASE-YYYY-XXXXXX`).
   * `review_notes` **required** (Non-empty, non-whitespace audit rationale).
   * `rejection_reason` **must be `None`**.
3. **`AUTO_REJECT` (Automated Rejection):**
   * `rejection_reason` **required**.
   * `disbursement_txn_id`, `disbursement_status`, `escalation_case_id`, `review_notes` **must be `None`**.
4. **`MANUAL_REJECT` (Human-in-the-Loop Rejection):**
   * `rejection_reason` **required**; `escalation_case_id` **required** (`SPP-CASE-...`).
   * `review_notes` **required** (Non-empty, non-whitespace audit rationale).
   * `disbursement_txn_id`, `disbursement_status` **must be `None`**.
5. **`ROUTE_FOR_MANUAL_REVIEW` / `HUMAN_REVIEW` / `REQUEST_MORE_INFO`:**
   * `escalation_case_id` **required** (`SPP-CASE-YYYY-XXXXXX`).
   * `disbursement_txn_id`, `disbursement_status`, `rejection_reason` **must be `None`**.

---

#### B. Caseworker Case Review Contract
Emitted during Caseworker Incident Staging to push case context to the District Officer Dashboard.

| Contract Attribute | Type / Constraints | Description |
| :--- | :--- | :--- |
| `escalation_case_id` | Case Ticket ID (`\w+-CASE-\d{4}-\d{6,}`) | Unique incident case ticket ID |
| `session_id` | UUID string | Parent communication session ID |
| `payload_id` | Extraction Payload ID | Pointer to the original extraction payload |
| `tokenized_citizen_id` | SHA-256 HMAC Token (64 hex chars) | Zero-PII citizen pseudonym |
| `application_intent` | Intent Enum | Target scheme intent |
| `extracted_entities` | Key-Value Mapping | Extracted domain parameters (allowed to be `{}` if AI extraction failed) |
| `unprocessed_input_content` | String (max 5000 chars) | Raw citizen text or signed audio URL pointer |
| `escalation_reason` | String (max 512 chars) | Non-empty reason for human escalation |
| `staged_at` | UTC Timestamp | Ticket creation timestamp |

##### Validation Rules:
* `escalation_case_id` **must** match pattern `^\w+-CASE-\d{4}-\d{6,}$`.
* `tokenized_citizen_id` **must** be an exact 64-character SHA-256 HMAC token.
* `unprocessed_input_content` and `escalation_reason` **must not be empty or whitespace**.
* `extracted_entities` **is intentionally allowed to be empty `{}`** so that sessions where AI extraction failed completely can still be staged for human review based on `unprocessed_input_content`.

---

#### C. Caseworker Review Outcome Contract
Submitted by a human officer adjudicating an escalated incident ticket.

| Contract Attribute | Type / Constraints | Description |
| :--- | :--- | :--- |
| `escalation_case_id` | Case Ticket ID | Target incident case ticket identifier |
| `reviewer_id` | String (5–128 chars) | Reviewing Officer UUID or Government ID |
| `governance_action` | Enum (`MANUAL_APPROVE`, `MANUAL_REJECT`, `REQUEST_MORE_INFO`) | Officer adjudication action |
| `review_notes` | String (5–2000 chars) | Mandatory non-whitespace audit rationale |
| `approved_amount` | Float ($\ge 0.0$, Optional) | Approved disbursement amount (required for `MANUAL_APPROVE`) |
| `rejection_reason` | String (max 512 chars, Optional) | Non-empty rejection justification (required for `MANUAL_REJECT`) |
| `reviewed_at` | UTC Timestamp | Officer review completion timestamp |

##### Validation Rules:
* `governance_action` **must** strictly be `MANUAL_APPROVE`, `MANUAL_REJECT`, or `REQUEST_MORE_INFO`.
* `review_notes` **is strictly mandatory** (min length 5, non-whitespace).
* **If `MANUAL_APPROVE`:** `approved_amount > 0.0` **required**; `rejection_reason` **must be `None`**.
* **If `MANUAL_REJECT`:** `rejection_reason` (non-whitespace) **required**; `approved_amount` **must be `None`**.
* **If `REQUEST_MORE_INFO`:** `review_notes` **must** detail requested missing fields; `approved_amount` and `rejection_reason` **must be `None`**.

---

## 7. Financial Disbursement & Payment Clearing Rail Requirements (Layer 6)

### 7.1 Treasury Payment Clearance Flow
* **Target Clearing Rail:** National Payments Corporation of India (NPCI) Aadhaar Payment Bridge System (APBS) / Public Financial Management System (PFMS) Treasury Gateway.
* **Idempotency Key:** `disbursement_txn_id` generated at decision finalization time to prevent duplicate bank transfers during retries.
* **Wire Execution:** The Treasury Integration Dispatcher executes the transition from **`PENDING` $\rightarrow$ `INITIATED`** when transmitting the ISO 20022 / APBS payment message across system boundaries to NPCI/PFMS clearing rails.
* **Initial State:** `disbursement_status = PENDING` (queued internally) $\rightarrow$ `INITIATED` (dispatched over wire).

### 7.2 Asynchronous Payment Clearing Callback Contract
Received from PFMS / NPCI rails when bank settlement completes or fails:

| Contract Attribute | Type / Constraints | Description |
| :--- | :--- | :--- |
| `disbursement_txn_id` | Idempotency Key (8–128 chars) | Unique internal payment order ID |
| `bank_reference_id` | String (max 64 chars, Optional) | External banking UTR / clearing reference (required on `SUCCESS`) |
| `disbursement_status` | Enum (`SUCCESS`, `FAILED`, `RETURNED`) | Terminal financial clearing state |
| `cleared_at` | UTC Timestamp | Gateway settlement timestamp |
| `failure_reason_code` | String (max 256 chars, Optional) | Banking failure reason code (required on `FAILED` or `RETURNED`) |

#### Callback Validation Rules:
1. `disbursement_status` **must** be a terminal state (`SUCCESS`, `FAILED`, `RETURNED`).
2. **If `FAILED` or `RETURNED`:** `failure_reason_code` **is strictly required** (non-whitespace, e.g., `ACCOUNT_BLOCKED`, `INVALID_IFSC`, `NAME_MISMATCH`).
3. **If `SUCCESS`:** `bank_reference_id` (UTR) **is strictly required** and `failure_reason_code` **must be `None`**.

#### Callback Validation Rules:
1. `disbursement_status` **must** be a terminal state (`SUCCESS`, `FAILED`, `RETURNED`).
2. **If `FAILED` or `RETURNED`:** `failure_reason_code` **is strictly required** (non-whitespace, e.g., `ACCOUNT_BLOCKED`, `INVALID_IFSC`, `NAME_MISMATCH`).
3. **If `SUCCESS`:** `bank_reference_id` (UTR) **is strictly required** and `failure_reason_code` **must be `None`**.

---

## 8. Relational Database Schema & Ledger Architecture

```sql
-- Core Telemetry Log
CREATE TABLE session_telemetry_log (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tokenized_phone_hash VARCHAR(64) NOT NULL,
    ingress_channel ingress_channel_type NOT NULL,
    session_status session_status_enum NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Extraction Details Ledger
CREATE TABLE session_extraction_details (
    payload_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES session_telemetry_log(session_id),
    attempt_id INT NOT NULL DEFAULT 1,
    unstructured_vernacular_text TEXT,
    standardized_english_text TEXT,
    extraction_confidence DECIMAL(4, 3) CHECK (extraction_confidence >= 0.000 AND extraction_confidence <= 1.000),
    extracted_district VARCHAR(100),
    extracted_crop_type VARCHAR(100),
    reported_anomaly VARCHAR(200),
    processing_state processing_state_enum NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_session_attempt UNIQUE (session_id, attempt_id)
);

-- Governance Ledger (Finalized Claims)
CREATE TABLE application_governance_ledger (
    claim_id UUID PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES session_telemetry_log(session_id),
    payload_id UUID NOT NULL REFERENCES session_extraction_details(payload_id),
    tokenized_identity_hash VARCHAR(64) NOT NULL,
    application_status application_status_enum NOT NULL,
    claimant_eligibility_status eligibility_status_enum NOT NULL,
    governance_action governance_action_enum,
    evaluated_at TIMESTAMPTZ,
    disbursement_status disbursement_status_enum,
    governance_metadata JSONB DEFAULT '{}'::jsonb,

    CONSTRAINT chk_approval_requires_amount CHECK (
        governance_action NOT IN ('AUTO_APPROVE', 'AUTOMATED_PAYOUT', 'MANUAL_APPROVE') OR (governance_metadata ? 'approval_amount')
    ),
    CONSTRAINT chk_rejection_requires_reason CHECK (
        governance_action NOT IN ('AUTO_REJECT', 'MANUAL_REJECT') OR (governance_metadata ? 'rejection_reason')
    )
);

-- Append-Only Audit Trail
CREATE TABLE application_governance_ledger_history (
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    claim_id UUID NOT NULL REFERENCES application_governance_ledger(claim_id) ON DELETE CASCADE,
    previous_application_status application_status_enum NULL,
    new_application_status application_status_enum NOT NULL,
    governance_action governance_action_enum,
    actor_id VARCHAR(100) NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Fast Resume Partial Index
CREATE INDEX idx_active_session_resume
ON session_telemetry_log (tokenized_phone_hash, created_at DESC)
WHERE session_status = 'ACTIVE';
```

---

## 9. Compliance, Type Safety & System Verification Matrix

| Requirement | Implementation Component | Verification Standard |
| :--- | :--- | :--- |
| **Strict Type Safety** | Pydantic `StrictBaseModel` & `str_strip_whitespace=True` | Ruff + Mypy strict type checking; pytest model validation. |
| **Error Format Standard** | RFC 7807 Problem Details (`application/problem+json`) | Validated API error handlers hiding internal stack traces. |
| **Deduplication Compaction** | dbt-core `stg_session_extraction_details` model | Executable `dbt run` compilation clearing multi-attempt mutations. |
| **Automated Test Suite** | Unit tests in `tests/data_models/` | `pytest` 100% pass rate across all schema contracts. |
