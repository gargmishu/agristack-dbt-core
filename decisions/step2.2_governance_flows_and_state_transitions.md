# Step 2.2: Governance Flows, State Transitions, and Disbursement Requirements

## 1. Executive Summary & Core Architectural Principles

This document defines the authoritative project requirements, state machines, workflow sequences, and validation contracts for the **Layer 4 Governance Engine & Sovereign DPI Benefit Disbursement Infrastructure** within AgriStack.

### Core Architectural Guarantees:
1. **Zero-PII Compliance:** Citizens are identified exclusively via 64-character SHA-256 HMAC tokens (`tokenized_citizen_id` / `tokenized_identity_hash`). Raw PII (Aadhaar numbers, cleartext phone numbers, unhashed names) is strictly prohibited across all governance schemas and database ledgers.
2. **Monotonic Forward-Only State Machines:** Financial clearing states (`DisbursementStatus`) move strictly forward (`PENDING` $\rightarrow$ `INITIATED` $\rightarrow$ `SUCCESS`/`FAILED`/`RETURNED`). Reversion (e.g. `INITIATED` $\rightarrow$ `PENDING`) is strictly forbidden to prevent double-dipping and duplicate payouts.
3. **Decoupled Governance vs. Financial Execution:** Governance decisions (`AUTO_APPROVE` / `MANUAL_APPROVE`) finalize claim eligibility and assign an idempotent tracking key (`disbursement_txn_id`) with `disbursement_status = PENDING`. The actual money movement over sovereign payment rails (NPCI APBS / PFMS) occurs asynchronously downstream.
4. **Mandatory Audit Traceability:** Every manual human intervention requires a `reviewer_id` (Officer UUID) and non-whitespace `review_notes` carried into the `application_governance_ledger_history`.

---

## 2. State Machines & Transition Specifications

### 2.1 Application Lifecycle State Machine (`ApplicationStatus`)

The formal lifecycle of a claim in the governance ledger (`application_governance_ledger`):

```
                       ┌──────────────┐
                       │    DRAFT     │ <─────────────┐
                       └──────┬───────┘               │
                              │ Citizen Submits       │
                              ▼                       │
                       ┌──────────────┐               │
                       │  SUBMITTED   │               │
                       └──────┬───────┘               │ (REQUEST_MORE_INFO)
                              │                       │
         ┌────────────────────┴────────────────────┐   │
         │ (High Confidence / Eligible)            │ (Low Confidence / Discrepancy)
         ▼                                         ▼   │
┌──────────────────┐                     ┌──────────────────┐
│    FINALIZED     │                     │   UNDER_REVIEW   │───┘
└────────┬─────────┘                     └────────┬─────────┘
         │                                        │ (Caseworker Action)
         │                                        ├──────────────────────┐
         ▼                                        ▼                      ▼
┌──────────────────┐                     ┌──────────────────┐  ┌──────────────────┐
│   DISBURSEMENT   │                     │    FINALIZED     │  │     REJECTED     │
│    CHECKOUT      │                     └──────────────────┘  └────────┬─────────┘
└──────────────────┘                                                    │ Citizen Appeals
                                                                        ▼
                                                               ┌──────────────────┐
                                                               │     APPEALED     │
                                                               └──────────────────┘
```

| State | Trigger / Event | Associated `GovernanceDecision` | Next Valid States |
| :--- | :--- | :--- | :--- |
| **`DRAFT`** | Citizen creates claim or officer requests info | `REQUEST_MORE_INFO` | `SUBMITTED` |
| **`SUBMITTED`** | Citizen submits extraction payload | *None (Pending Evaluation)* | `FINALIZED`, `UNDER_REVIEW`, `REJECTED` |
| **`UNDER_REVIEW`** | AI confidence $<0.85$ or anomaly detected | `ROUTE_FOR_MANUAL_REVIEW` / `HUMAN_REVIEW` | `FINALIZED`, `REJECTED`, `DRAFT` |
| **`FINALIZED`** | Claims approved automatically or manually | `AUTO_APPROVE`, `AUTOMATED_PAYOUT`, `MANUAL_APPROVE` | *(Terminal Application State)* |
| **`REJECTED`** | Claims rejected automatically or manually | `AUTO_REJECT`, `MANUAL_REJECT` | `APPEALED` |
| **`APPEALED`** | Citizen contests rejection | *None (Re-entering Queue)* | `UNDER_REVIEW`, `FINALIZED`, `REJECTED` |

---

### 2.2 Financial Clearing State Machine (`DisbursementStatus`)

Financial clearing states track the execution of funds transfer over national clearing rails:

```
[ Decision Finalized ] ──> PENDING (Queued internally in batch ledger)
                               │
                               │ Payment Dispatcher transmits instruction over wire
                               ▼
                      INITIATED (Sent to NPCI APBS / PFMS Treasury Gateway)
                               │
                               │ Asynchronous Bank Settlement Callback
                               ▼
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
           SUCCESS          FAILED           RETURNED
```

* **`PENDING` (Internal Queue):** Assigned at decision finalization time (Step 09 or Caseworker Approval) along with `disbursement_txn_id`. Bridges the time gap while the claim waits for payment dispatch.
* **`INITIATED` (Wire Dispatch via `step_10`):** Executed by **`step_10_automated_payout_disbursement`** (or Treasury Integration Dispatcher) when the transaction request is transmitted across system boundaries over NPCI APBS / PFMS rails.
* **`SUCCESS` (Terminal Clearance):** Confirmed by bank callback (`DisbursementCallbackPayload`) when funds reach citizen account.
* **`FAILED` / `RETURNED` (Terminal Failure):** Confirmed by bank callback when clearing fails (requires non-empty `failure_reason_code`, e.g., `ACCOUNT_BLOCKED`, `INVALID_IFSC`).

> [!IMPORTANT]
> The transition from **`PENDING` $\rightarrow$ `INITIATED`** occurs explicitly during **`step_10`** execution. Backward transitions (e.g. `INITIATED` $\rightarrow$ `PENDING`) are strictly forbidden. If a network fault occurs during dispatch, the transaction is marked `FAILED` and re-initiated under a new idempotent transaction context.

---

## 3. Detailed Workflow Specifications

### 3.1 Flow 1: Straight-Through Automated Approval (STP)

Targeted at high-confidence, zero-anomaly claims requiring instant execution.

```
[ Citizen Ingress ] ➔ [ Step 04: Entity Extraction ] ➔ [ Step 08: Confidence Evaluation (>=0.85) ]
                                                                     │
                                                                     ▼
[ Step 10: Disbursement ] ◄─ (FORWARD_TO_AUTOMATED_PAYOUT) ◄─ [ Step 09: Governance Router ]
```

1. **Evaluation:** Step 08 validates `ai_confidence_score >= 0.85` and `eligibility_status == ELIGIBLE`.
2. **Double-Dipping Check:** System queries `tokenized_identity_hash` in `application_governance_ledger` to verify citizen has not already received an approved payout for the active season.
3. **Payload Generation:** Layer 4 emits `GovernanceOutcomePayload` with:
   * `governance_decision = AUTO_APPROVE` (or `AUTOMATED_PAYOUT`)
   * `disbursement_txn_id = "TXN-YYYY-XXXXXX"` (Idempotency tracking key)
   * `disbursement_status = PENDING` (or `INITIATED`)
   * `escalation_case_id = None`, `rejection_reason = None`, `review_notes = None`
4. **Execution:** Step 09 routes to `FORWARD_TO_AUTOMATED_PAYOUT_DISBURSEMENT` $\rightarrow$ Step 10 triggers NPCI Aadhaar Payment Bridge.

---

### 3.2 Flow 2: Incident Staging & Manual Caseworker Review

Targeted at ambiguous, low-confidence ($<0.85$), or unparseable input claims.

```
[ Step 08: Evaluation (<0.85 / Anomaly) ] ➔ [ Step 09 Router ] ➔ [ Step 11: Incident Ticket Staging ]
                                                                             │
                                                                   (Creates SPP-CASE-YYYY-XXXXXX)
                                                                             │
                                                                             ▼
[ Application Decision Pipeline ] ◄─── (Submits Review) ◄─── [ Caseworker Review Dashboard ]
```

1. **Staging (`Step 11`):** System creates incident ticket `SPP-CASE-YYYY-XXXXXX` and emits `CaseworkerCaseReviewPayload`:
   * `unprocessed_input_content` carries raw citizen text/audio URL (**must not be empty**).
   * `extracted_entities` carries extracted parameters, but **may be empty `{}`** if AI extraction failed completely.
2. **Officer Adjudication:** Human officer inspects case in District Review Dashboard and submits `CaseworkerReviewOutcomePayload`:
   * **Option A — `MANUAL_APPROVE`:** Must provide `approved_amount > 0.0` and `review_notes` (min length 5). System assigns `disbursement_txn_id` with `disbursement_status = PENDING`.
   * **Option B — `MANUAL_REJECT`:** Must provide `rejection_reason` and `review_notes`. Application transitions to `REJECTED`.
   * **Option C — `REQUEST_MORE_INFO`:** Must provide `review_notes` detailing missing info. Application transitions back to `DRAFT` so citizen can re-engage over WhatsApp/USSD.

---

### 3.3 Flow 3: Asynchronous Treasury Payment Clearing

```
[ Payment Rail Dispatcher ] ──(ISO 20022 / APBS Message)──> [ NPCI / PFMS Gateway ]
                                                                   │
                                                           (Bank Settlement)
                                                                   │
[ Governance Ledger ] ◄── (DisbursementCallbackPayload) ───────────┘
  └─ Sets SUCCESS or FAILED with failure_reason_code
```

1. **Dispatch:** Payment worker queries claims where `disbursement_status == PENDING` and transmits batch instructions to NPCI / PFMS, updating status to `INITIATED`.
2. **Callback Handling:** External bank rails send asynchronous status callback (`DisbursementCallbackPayload`):
   * Matches on `disbursement_txn_id`.
   * If `disbursement_status == SUCCESS`: Sets `failure_reason_code = None`, finalizes claim clearance.
   * If `disbursement_status in (FAILED, RETURNED)`: Requires non-empty `failure_reason_code` (e.g., `ACCOUNT_BLOCKED`, `INVALID_IFSC`, `NAME_MISMATCH`).

---

## 4. Canonical Model Contracts & Validation Rules

### 4.1 `GovernanceOutcomePayload` (`src/models/governance/governance_outcome_payload.py`)

Emitted when Layer 4 or Caseworker Adjudication finalizes a governance decision.

```python
class GovernanceOutcomePayload(StrictBaseModel):
    session_id: SessionId
    payload_id: ExtractionPayloadId
    ai_confidence_score: AiConfidenceScore
    eligibility_status: EligibilityStatus
    governance_decision: GovernanceDecision
    disbursement_txn_id: DisbursementTxnId | None = Field(
        None,
        description="Idempotency tracking key generated at approval time for AUTO_APPROVE / MANUAL_APPROVE / AUTOMATED_PAYOUT",
    )
    disbursement_status: DisbursementStatus | None = Field(
        None,
        description="Initialized to PENDING/INITIATED at decision time; updated to SUCCESS/FAILED/RETURNED upon bank callback",
    )
    escalation_case_id: EscalationCaseId | None = None
    rejection_reason: str | None = Field(None, description="Populated for AUTO_REJECT / MANUAL_REJECT")
    review_notes: str | None = Field(None, max_length=2000, description="Internal caseworker audit notes")
    decided_at: UtcTimestamp
```

#### Validation Rules:
* **`AUTO_APPROVE` / `AUTOMATED_PAYOUT`:** `disbursement_txn_id` **required**; `disbursement_status` **required** (`PENDING`/`INITIATED`); `rejection_reason`, `escalation_case_id`, `review_notes` **must be `None`**.
* **`MANUAL_APPROVE`:** `disbursement_txn_id` **required**; `disbursement_status` **required**; `escalation_case_id` **required** (`SPP-CASE-...`); `review_notes` **required** (non-whitespace); `rejection_reason` **must be `None`**.
* **`AUTO_REJECT`:** `rejection_reason` **required**; `disbursement_txn_id`, `disbursement_status`, `escalation_case_id`, `review_notes` **must be `None`**.
* **`MANUAL_REJECT`:** `rejection_reason` **required**; `escalation_case_id` **required**; `review_notes` **required** (non-whitespace); `disbursement_txn_id`, `disbursement_status` **must be `None`**.
* **`ROUTE_FOR_MANUAL_REVIEW` / `HUMAN_REVIEW` / `REQUEST_MORE_INFO`:** `escalation_case_id` **required**; `disbursement_txn_id`, `disbursement_status`, `rejection_reason` **must be `None`**.

---

### 4.2 `CaseworkerCaseReviewPayload` (`src/models/caseworker/case_review_payload.py`)

Emitted by Step 11 to stage an incident ticket into the Caseworker Review Dashboard.

```python
class CaseworkerCaseReviewPayload(StrictBaseModel):
    escalation_case_id: EscalationCaseId
    session_id: SessionId
    payload_id: ExtractionPayloadId
    tokenized_citizen_id: HmacCitizenToken
    application_intent: ApplicationIntent
    extracted_entities: dict[DomainEntityKey, str | float | int] = Field(
        default_factory=dict,
        description="Extracted domain parameters. May be empty ({}) if escalation was triggered by AI extraction failure.",
    )
    unprocessed_input_content: str = Field(..., max_length=5000, description="Raw citizen text or signed audio URL")
    escalation_reason: str = Field(..., max_length=512, description="Reason for escalation")
    staged_at: UtcTimestamp
```

#### Validation Rules:
* `escalation_case_id` **must** match pattern `^\w+-CASE-\d{4}-\d{6,}$`.
* `tokenized_citizen_id` **must** be an exact 64-character SHA-256 HMAC token (Zero-PII).
* `unprocessed_input_content` and `escalation_reason` **must not be empty or whitespace**.
* `extracted_entities` **is intentionally allowed to be empty `{}`** to support cases where AI extraction failed completely.

---

### 4.3 `CaseworkerReviewOutcomePayload` (`src/models/caseworker/review_outcome_payload.py`)

Submitted by human officers adjudicating an escalated ticket.

```python
class CaseworkerReviewOutcomePayload(StrictBaseModel):
    escalation_case_id: EscalationCaseId
    reviewer_id: str = Field(..., min_length=5, max_length=128, description="UUID or Officer ID")
    governance_decision: GovernanceDecision = Field(..., description="Must strictly be MANUAL_APPROVE, MANUAL_REJECT, or REQUEST_MORE_INFO")
    review_notes: str = Field(..., min_length=5, max_length=2000, description="Mandatory audit justification note")
    approved_amount: float | None = Field(None, ge=0.0, description="Populated for MANUAL_APPROVE")
    rejection_reason: str | None = Field(None, max_length=512, description="Populated for MANUAL_REJECT")
    decided_at: UtcTimestamp
```

#### Validation Rules:
* `governance_decision` **must** strictly be `MANUAL_APPROVE`, `MANUAL_REJECT`, or `REQUEST_MORE_INFO`.
* `review_notes` **is strictly mandatory** (min length 5, non-whitespace).
* **If `MANUAL_APPROVE`:** `approved_amount > 0.0` **required**; `rejection_reason` **must be `None`**.
* **If `MANUAL_REJECT`:** `rejection_reason` (non-whitespace) **required**; `approved_amount` **must be `None`**.
* **If `REQUEST_MORE_INFO`:** `approved_amount` and `rejection_reason` **must be `None`**.

---

### 4.4 `DisbursementCallbackPayload` (`src/models/disbursement/disbursement_payload.py`)

Asynchronous payment clearing callback received from PFMS / NPCI rails.

```python
class DisbursementCallbackPayload(StrictBaseModel):
    disbursement_txn_id: DisbursementTxnId
    disbursement_status: DisbursementStatus = Field(..., description="Updated clearing state: SUCCESS, FAILED, RETURNED")
    cleared_at: UtcTimestamp
    failure_reason_code: str | None = Field(None, max_length=256, description="Populated if status is FAILED or RETURNED")
```

#### Validation Rules:
* `disbursement_status` **must** be a terminal state (`SUCCESS`, `FAILED`, `RETURNED`).
* If status is `FAILED` or `RETURNED`: `failure_reason_code` **is strictly required** (non-whitespace).
* If status is `SUCCESS`: `failure_reason_code` **must be `None`**.

---

## 5. Security, Idempotency & Audit Traceability Matrix

| Feature | Enforcement Mechanism | Purpose |
| :--- | :--- | :--- |
| **Zero-PII Privacy** | SHA-256 HMAC Tokenization (`HmacCitizenToken`) | Guarantees Aadhaar / Phone numbers are never exposed in ledger tables. |
| **Double-Dipping Prevention** | Database `UNIQUE(tokenized_identity_hash, season)` & Pre-checkout check | Prevents citizens from receiving duplicate automated payouts in the same season. |
| **Idempotency Guarantee** | `disbursement_txn_id` generated at approval time | Allows asynchronous payment retries without creating duplicate bank transactions. |
| **Audit Traceability** | `application_governance_ledger_history` append-only table | Records every state change, actor ID (`SYSTEM:{ver}` or Officer UUID), and justification notes. |
| **Strict Type Safety** | Pydantic `StrictBaseModel` & `str_strip_whitespace=True` | Automatically strips leading/trailing spaces and enforces strict type boundaries. |
