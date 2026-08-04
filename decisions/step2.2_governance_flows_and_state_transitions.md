# Step 2.2: Governance Flows, State Transitions, and Disbursement Requirements

## 1. Executive Summary & Core Architectural Principles

This document defines the authoritative project requirements, state machines, workflow sequences, and validation contracts for the **Layer 4 Governance Engine & Sovereign DPI Benefit Disbursement Infrastructure** within AgriStack.

### Core Architectural Guarantees:
1. **Zero-PII Compliance:** Citizens are identified exclusively via 64-character SHA-256 HMAC tokens (`tokenized_citizen_id` / `tokenized_identity_hash`). Raw PII (Aadhaar numbers, cleartext phone numbers, unhashed names) is strictly prohibited across all governance schemas and database ledgers.
2. **Monotonic Forward-Only State Machines:** Financial clearing states (`DisbursementStatus`) move strictly forward (`PENDING` $\rightarrow$ `INITIATED` $\rightarrow$ `SUCCESS`/`FAILED`/`RETURNED`). Reversion (e.g. `INITIATED` $\rightarrow$ `PENDING`) is strictly forbidden to prevent double-dipping and duplicate payouts.
3. **Decoupled Governance vs. Financial Execution:** Governance decisions (`AUTO_APPROVE` / `MANUAL_APPROVE`) mark the claim as **approved** and assign an internal idempotent tracking key (`disbursement_txn_id`) with `disbursement_status = PENDING`. The actual money movement over sovereign payment rails (NPCI APBS / PFMS) occurs asynchronously downstream, upon which the bank returns an external transaction reference / UTR (`bank_reference_id`).
4. **Mandatory Audit Traceability:** Every manual human intervention requires a `reviewer_id` (Officer UUID) and non-whitespace `review_notes` carried into the `application_governance_ledger_history`.

---

## 2. State Machines & Transition Specifications

### 2.1 Application Lifecycle State Machine (`ApplicationStatus`)

The formal lifecycle of a claim in the governance ledger (`application_governance_ledger`):

```
                        ┌──────────────┐
                        │    DRAFT     │
                        └──────┬───────┘
                               │ Citizen Submits
                               ▼
                        ┌──────────────┐ <────────────────────────────────┐
                        │  SUBMITTED   │                                  │
                        └──────┬───────┘                                  │
                               │                                          │ (Citizen Reply:
         ┌─────────────────────┼─────────────────────┐                    │  Auto-Reevaluate)
         │                     │                     │                    │
         │ (High Confidence    │ (High Confidence    │ (Low Confidence /  │
         │  & Eligible)        │  & Ineligible /     │  Entity Discrepancy)│
         │                     │  Double-Dip)        │                    │
         ▼                     ▼                     ▼                    │
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│     APPROVED     │  │     REJECTED     │  │   UNDER_REVIEW   │───┐      │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘   │      │
         │                     ▲                 ▲   │             │      │
         │                     │ (Citizen Reply  │   │             ▼      │
         ▼                     │  to Open Ticket)│   │    ┌───────────────┴─┐
┌──────────────────┐           │                 └───┼────┤  INFO_REQUESTED │
│   DISBURSEMENT   │           │                     │    └─────────────────┘
│    CHECKOUT      │           │                     │ (Caseworker Action)
└──────────────────┘           │                     ├──────────────────────┐
                               │                     ▼                      ▼
                               │            ┌──────────────────┐  ┌──────────────────┐
                               └────────────┤     REJECTED     │  │     APPROVED     │
                                            └────────┬─────────┘  └──────────────────┘
                                                     │ Citizen Appeals
                                                     ▼
                                            ┌──────────────────┐
                                            │     APPEALED     │
                                            └──────────────────┘
```

| State | Trigger / Event | Associated `GovernanceAction` | Next Valid States |
| :--- | :--- | :--- | :--- |
| **`DRAFT`** | Citizen initiates claim (unsubmitted scratch state) | *None (Initial Creation)* | `SUBMITTED` |
| **`SUBMITTED`** | Citizen confirms claim via chat/voice/USSD; system commits extracted details to ledger | *None (Pending Evaluation)* | `APPROVED`, `REJECTED`, `UNDER_REVIEW` |
| **`UNDER_REVIEW`** | AI confidence $<0.85$ or anomaly detected | `ROUTE_FOR_MANUAL_REVIEW` / `HUMAN_REVIEW` | `APPROVED`, `REJECTED`, `INFO_REQUESTED` |
| **`INFO_REQUESTED`** | Caseworker requests missing details or clarification | `REQUEST_MORE_INFO` | `SUBMITTED`, `UNDER_REVIEW` |
| **`APPROVED`** | Claim approved automatically (eligible) or manually by officer | `AUTO_APPROVE`, `AUTOMATED_PAYOUT`, `MANUAL_APPROVE` | *(Terminal Application State; proceeds to clearing)* |
| **`REJECTED`** | Claim rejected automatically (ineligible/double-dip) or manually | `AUTO_REJECT`, `MANUAL_REJECT` | `APPEALED` |
| **`APPEALED`** | Citizen contests rejection | *None (Re-entering Queue)* | `UNDER_REVIEW`, `APPROVED`, `REJECTED` |

---

### 2.2 Financial Clearing State Machine (`DisbursementStatus`)

Financial clearing states track the execution of funds transfer over national clearing rails for **approved** claims only:

```
[ Claim Approved (AUTO_APPROVE / MANUAL_APPROVE) ] ──> PENDING (Queued internally in batch ledger)
                                                          │
                                                          │ Payment Dispatcher transmits instruction over wire
                                                          ▼
                                                 INITIATED (Sent to NPCI APBS / PFMS Treasury Gateway)
                                                          │
                                                          │ Asynchronous Bank Settlement Callback (Returns bank_reference_id)
                                                          ▼
                                         ┌────────────────┼────────────────┐
                                         ▼                ▼                ▼
                                      SUCCESS          FAILED           RETURNED
```

* **`PENDING` (Internal Queue):** Assigned when a claim is **approved** (via Step 09 automated evaluation or Caseworker Manual Approval) along with our internal `disbursement_txn_id`. Bridges the time gap while the approved claim waits for payment dispatch. Notice that rejected claims never enter the disbursement lifecycle.
* **`INITIATED` (Wire Dispatch via `step_10`):** Executed by **`step_10_automated_payout_disbursement`** (or Treasury Integration Dispatcher) when the transaction request is transmitted across system boundaries over NPCI APBS / PFMS rails using our internal `disbursement_txn_id` as the instruction idempotency key.
* **`SUCCESS` (Terminal Clearance):** Confirmed by bank callback (`DisbursementCallbackPayload`) when funds reach the citizen account. Strictly requires the bank to return an external bank-generated transaction clearing ID / UTR (`bank_reference_id`).
* **`FAILED` / `RETURNED` (Terminal Failure):** Confirmed by bank callback when clearing fails (requires non-empty `failure_reason_code`, e.g., `ACCOUNT_BLOCKED`, `INVALID_IFSC`).

> [!IMPORTANT]
> The transition from **`PENDING` $\rightarrow$ `INITIATED`** occurs explicitly during **`step_10`** execution. Backward transitions (e.g. `INITIATED` $\rightarrow$ `PENDING`) are strictly forbidden. If a network fault occurs during dispatch, the transaction is marked `FAILED` and re-initiated under a new idempotent transaction context.

---

## 3. Detailed Workflow Specifications

### 3.1 Flow 1: Straight-Through Automated Processing (STP: Approval & Rejection)

Targeted at high-confidence (`>= 0.85`), zero-anomaly claims requiring instant automated adjudication without human intervention. High confidence can result in either an immediate automated **approval** or an immediate automated **rejection**.

```
[ Citizen Ingress ] ➔ [ Step 04: Entity Extraction ] ➔ [ Step 08: Confidence Evaluation (>=0.85) ]
                                                                     │
                                          ┌──────────────────────────┴──────────────────────────┐
                                          ▼ (Eligible & No Double-Dip)                          ▼ (Ineligible or Double-Dip)
                     [ Step 09 Router: AUTO_APPROVE / AUTOMATED_PAYOUT ]   [ Step 09 Router: AUTO_REJECT ]
                                          │                                                     │
                                          ▼                                                     ▼
                            [ Application State: APPROVED ]                        [ Application State: REJECTED ]
                            [ Disbursement State: PENDING ]                        [ Disbursement: N/A (Terminated) ]
                                          │
                                          ▼
                      [ Step 10: Payment Dispatch (INITIATED) ]
```

1. **Confidence & Eligibility Evaluation:** Step 08 validates that `ai_confidence_score >= 0.85`. It then evaluates eligibility criteria (`eligibility_status`) and checks against `tokenized_identity_hash` in `application_governance_ledger` to verify the citizen has not already received an approved payout for the active season.
2. **Outcome A — Automated Approval (`APPROVED`):** If `eligibility_status == ELIGIBLE` and no duplicate claim exists:
   * Layer 4 emits `GovernanceOutcomePayload` with `governance_decision = AUTO_APPROVE` (or `AUTOMATED_PAYOUT`).
   * Application status transitions to **`APPROVED`**.
   * System assigns an internal idempotency tracking key `disbursement_txn_id = "TXN-YYYY-XXXXXX"` and initializes `disbursement_status = PENDING`.
   * Step 09 routes to Step 10 (`FORWARD_TO_AUTOMATED_PAYOUT_DISBURSEMENT`) to trigger the NPCI Aadhaar Payment Bridge.
3. **Outcome B — Automated Rejection (`REJECTED`):** If `eligibility_status == INELIGIBLE` OR a duplicate double-dipping claim is detected:
   * Layer 4 emits `GovernanceOutcomePayload` with `governance_decision = AUTO_REJECT` and populates a descriptive `rejection_reason`.
   * Application status transitions directly to **`REJECTED`**.
   * `disbursement_txn_id`, `disbursement_status`, and `escalation_case_id` remain `None`. The financial clearing flow is bypassed entirely.

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
   * **Option C — `REQUEST_MORE_INFO`:** Must provide `review_notes` detailing missing info. Application transitions to **`INFO_REQUESTED`** so the system can re-engage the citizen over WhatsApp/USSD.
     * **Clarification Resolution (`INFO_REQUESTED` $\rightarrow$ `UNDER_REVIEW`):** When the citizen replies over their conversational channel with the requested details, the system captures the input, attaches it to the open escalation ticket (`SPP-CASE-YYYY-XXXX`), and transitions the status directly back to **`UNDER_REVIEW`** (marked as *"Clarification Received"* in the caseworker dashboard) for final officer adjudication. Alternatively, if the new information allows automated straight-through processing, the system transitions it to **`SUBMITTED`** for automated re-evaluation.

---

### 3.3 Flow 3: Asynchronous Treasury Payment Clearing

```
[ Payment Rail Dispatcher ] ──(disbursement_txn_id instruction)──> [ NPCI / PFMS Gateway ]
                                                                            │
                                                          (Bank Clearing / UTR Generation)
                                                                            │
[ Governance Ledger ] ◄── (DisbursementCallbackPayload with bank_reference_id) ─┘
  └─ Sets SUCCESS (with bank_reference_id UTR) or FAILED (with failure_reason_code)
```

1. **Dispatch:** Payment worker queries approved claims where `disbursement_status == PENDING` and transmits batch instructions to NPCI / PFMS using our internal `disbursement_txn_id`, updating status to `INITIATED`.
2. **Callback Handling:** External bank rails send an asynchronous status callback (`DisbursementCallbackPayload`):
   * Matches against our internal instructional order key `disbursement_txn_id`.
   * If `disbursement_status == SUCCESS`: Strictly requires the bank-generated external transaction ID / UTR (`bank_reference_id`). Sets `failure_reason_code = None`, confirming successful payout clearing.
   * If `disbursement_status in (FAILED, RETURNED)`: Requires non-empty `failure_reason_code` (e.g., `ACCOUNT_BLOCKED`, `INVALID_IFSC`, `NAME_MISMATCH`).

---

## 4. Canonical Model Contracts & Validation Rules

### 4.1 `GovernanceOutcomePayload` (`src/models/governance/governance_outcome_payload.py`)

Emitted when Layer 4 automated evaluation or Caseworker Adjudication reaches an **approved** or **rejected** decision (or routes for manual review).

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

### 4.4 `DisbursementCallbackPayload` (`src/data_models/disbursement/disbursement_callback_payload.py`)

Asynchronous payment clearing callback received from PFMS / NPCI APBS sovereign payment rails.

#### Why two distinct transaction identifiers (`disbursement_txn_id` vs. `bank_reference_id`)?
* **`disbursement_txn_id` (Internal Instruction Order Key):** Generated internally by AgriStack when a claim is **approved** (at Layer 4 auto-approval or caseworker manual approval) *before* dispatch to the bank. Acts as AgriStack's internal idempotency key so payment instructions can be retried across network interruptions without creating duplicate payouts. This is **not** the bank transaction ID.
* **`bank_reference_id` (External Bank Transaction ID / UTR):** Generated autonomously by the bank / sovereign payment clearing rail (NPCI APBS or PFMS Treasury Gateway) upon financial wire clearing. Serves as the immutable bank-certified Unique Transaction Reference (UTR) or bank transaction ID for banking reconciliation and citizen payout receipts.

```python
class DisbursementCallbackPayload(StrictBaseModel):
    disbursement_txn_id: DisbursementTxnId = Field(..., description="Internal idempotency instruction key")
    bank_reference_id: str | None = Field(None, max_length=64, description="External banking UTR / clearing reference")
    disbursement_status: DisbursementStatus = Field(..., description="Updated clearing state: SUCCESS, FAILED, RETURNED")
    cleared_at: UtcTimestamp = Field(..., description="UTC timestamp of bank rail processing")
    failure_reason_code: str | None = Field(None, max_length=256, description="Populated if status is FAILED or RETURNED")
```

#### Validation Rules:
* `disbursement_status` **must** be a terminal clearing state (`SUCCESS`, `FAILED`, `RETURNED`).
* If status is `SUCCESS`: `bank_reference_id` (UTR) **is strictly required**; `failure_reason_code` **must be `None`**.
* If status is `FAILED` or `RETURNED`: `failure_reason_code` **is strictly required** (non-whitespace).

---

## 5. Security, Idempotency & Audit Traceability Matrix

| Feature | Enforcement Mechanism | Purpose |
| :--- | :--- | :--- |
| **Zero-PII Privacy** | SHA-256 HMAC Tokenization (`HmacCitizenToken`) | Guarantees Aadhaar / Phone numbers are never exposed in ledger tables. |
| **Double-Dipping Prevention** | Database `UNIQUE(tokenized_identity_hash, season)` & Pre-checkout check | Prevents citizens from receiving duplicate automated payouts in the same season. |
| **Idempotency vs. Bank Clearing** | Internal `disbursement_txn_id` vs. External Bank ID (`bank_reference_id` UTR) | Internal `disbursement_txn_id` guarantees retry idempotency without duplicate bank orders; external `bank_reference_id` is the bank-generated transaction ID providing proof of clearing. |
| **Audit Traceability** | `application_governance_ledger_history` append-only table | Records every state change, actor ID (`SYSTEM:{ver}` or Officer UUID), and justification notes. |
| **Strict Type Safety** | Pydantic `StrictBaseModel` & `str_strip_whitespace=True` | Automatically strips leading/trailing spaces and enforces strict type boundaries. |
