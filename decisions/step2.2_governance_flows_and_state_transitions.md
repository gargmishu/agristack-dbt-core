# Step 2.2: Governance Flows, State Transitions, and Disbursement Requirements

## 1. Executive Summary & Core Architectural Principles

This document defines the authoritative project requirements, state machines, workflow sequences, and validation contracts for the **Layer 4 Governance Engine & Sovereign DPI Benefit Disbursement Infrastructure** within AgriStack.

### Core Architectural Guarantees:
1. **Zero-PII Compliance:** Citizens are identified exclusively via 64-character SHA-256 HMAC tokens (`tokenized_citizen_id` / `tokenized_identity_hash`). Raw PII (Aadhaar numbers, cleartext phone numbers, unhashed names) is strictly prohibited across all governance schemas and database ledgers.
2. **Monotonic Forward-Only State Machines:** Financial clearing states (`DisbursementStatus`) move strictly forward (`PENDING` $\rightarrow$ `INITIATED` $\rightarrow$ `SUCCESS`/`FAILED`/`RETURNED`). Reversion (e.g. `INITIATED` $\rightarrow$ `PENDING`) is strictly forbidden to prevent double-dipping and duplicate payouts.
3. **Decoupled Governance vs. Financial Execution:** Governance decisions (`AUTO_APPROVE` / `AUTOMATED_PAYOUT` / `MANUAL_APPROVE`) mark the claim as **approved** and assign an internal idempotent tracking key (`disbursement_txn_id`) with `disbursement_status = PENDING`. The actual money movement over sovereign payment rails (NPCI APBS / PFMS) occurs asynchronously downstream, upon which the bank returns an external transaction reference / UTR (`bank_reference_id`).
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
                        ┌──────────────┐
                        │  SUBMITTED   │
                        └──────┬───────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         │ (High Confidence    │ (High Confidence    │ (Low Confidence /
         │  & Eligible)        │  & Ineligible /     │  Entity Discrepancy)
         │                     │  Double-Dip)        │
         ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│     APPROVED     │  │     REJECTED     │  │   UNDER_REVIEW   │───┐
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘   │
         │                     ▲                 ▲   │             │
         │                     │ (Citizen Reply  │   │             ▼
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
| **`INFO_REQUESTED`** | Caseworker requests missing details or clarification | `REQUEST_MORE_INFO` | `UNDER_REVIEW` |
| **`APPROVED`** | Claim approved automatically (eligible) or manually by officer | `AUTO_APPROVE`, `AUTOMATED_PAYOUT`, `MANUAL_APPROVE` | *(Terminal Application State; proceeds to clearing)* |
| **`REJECTED`** | Claim rejected automatically (ineligible/double-dip) or manually | `AUTO_REJECT`, `MANUAL_REJECT` | `APPEALED` |
| **`APPEALED`** | Citizen contests rejection | *None (Re-entering Queue)* | `UNDER_REVIEW`, `APPROVED`, `REJECTED` |

---

### 2.2 Financial Clearing State Machine (`DisbursementStatus`)

Financial clearing states track the execution of funds transfer over national clearing rails for **approved** claims only:

```
[ Claim Approved (AUTO_APPROVE / AUTOMATED_PAYOUT / MANUAL_APPROVE) ] ──> PENDING (Queued internally in batch ledger)
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

* **`PENDING` (Internal Queue):** Assigned when a claim is **approved** along with our internal `disbursement_txn_id`. Bridges the time gap while the approved claim waits for payment dispatch. Notice that rejected claims never enter the disbursement lifecycle.
* **`INITIATED` (Wire Dispatch):** Assigned when the transaction request is transmitted across system boundaries over NPCI APBS / PFMS rails using our internal `disbursement_txn_id` as the instruction idempotency key.
* **`SUCCESS` (Terminal Clearance):** Confirmed by bank callback (*Payment Clearing Callback Contract*) when funds reach the citizen account. Strictly requires the bank to return an external bank-generated transaction clearing ID / UTR (`bank_reference_id`).
* **`FAILED` / `RETURNED` (Terminal Failure):** Confirmed by bank callback when clearing fails (requires non-empty `failure_reason_code`, e.g., `ACCOUNT_BLOCKED`, `INVALID_IFSC`).

---

## 3. Detailed Workflow Specifications

### 3.1 Flow 1: Straight-Through Automated Processing (STP: Approval & Rejection)

Targeted at high-confidence (`>= 0.85`), zero-anomaly claims requiring instant automated adjudication without human intervention. High confidence can result in either an immediate automated **approval** or an immediate automated **rejection**.

```
[ Evaluation (Score >= 0.85) ] ───(Check Eligibility & Ledger)───┐
                                                                 │
      ┌──────────────────────────────────────────────────────────┴──────────────────────────────────────────────────────────┐
      ▼                                                                                                                     ▼
[ Outcome A: ELIGIBLE ]                                                                                      [ Outcome B: INELIGIBLE / DUPLICATE ]
      │                                                                                                                     │
      ├─► Emit Governance Outcome Decision (AUTO_APPROVE / AUTOMATED_PAYOUT)                                                ├─► Emit Governance Outcome Decision (AUTO_REJECT)
      ├─► Transition Application Status ➔ APPROVED                                                                          ├─► Transition Application Status ➔ REJECTED
      └─► Assign disbursement_txn_id & status = PENDING ──► [ Payment Rail ]                                                └─► Bypass Financial Clearing (No disbursement_txn_id)
```

1. **Confidence & Eligibility Evaluation:** The evaluation engine validates that `ai_confidence_score >= 0.85`. It then evaluates eligibility criteria (`eligibility_status`) and checks against `tokenized_identity_hash` in `application_governance_ledger` to verify the citizen has not already received an approved payout for the active season.
2. **Outcome A — Automated Approval (`APPROVED`):** If `eligibility_status == ELIGIBLE` and no duplicate claim exists:
   * Layer 4 emits the Governance Outcome Decision with `governance_action = AUTO_APPROVE` (or `AUTOMATED_PAYOUT`).
   * Application status transitions to **`APPROVED`**.
   * System assigns an internal idempotency tracking key `disbursement_txn_id = "TXN-YYYY-XXXXXX"` and initializes `disbursement_status = PENDING`.
   * The claim adjudicator issues `FORWARD_TO_AUTOMATED_PAYOUT_DISBURSEMENT` to trigger wire dispatch over the NPCI Aadhaar Payment Bridge.
3. **Outcome B — Automated Rejection (`REJECTED`):** If `eligibility_status == INELIGIBLE` OR a duplicate double-dipping claim is detected:
   * Layer 4 emits the Governance Outcome Decision with `governance_action = AUTO_REJECT` and populates a descriptive `rejection_reason`.
   * Application status transitions directly to **`REJECTED`**.
   * `disbursement_txn_id`, `disbursement_status`, and `escalation_case_id` remain `None`. The financial clearing flow is bypassed entirely.

---

### 3.2 Flow 2: Incident Staging & Manual Caseworker Review

Targeted at ambiguous, low-confidence ($<0.85$), or unparseable input claims.

```
[ Evaluation (<0.85 / Anomaly) ] ➔ [ Claim Adjudicator ] ➔ [ Incident Ticket Staging ]
                                                                             │
                                                                   (Creates SPP-CASE-YYYY-XXXXXX)
                                                                             │
                                                                             ▼
[ Application Decision Pipeline ] ◄─── (Submits Review) ◄─── [ Caseworker Review Dashboard ]
```

1. **Incident Staging:** System creates incident ticket `SPP-CASE-YYYY-XXXXXX` and emits the Caseworker Case Review Payload:
   * `unprocessed_input_content` carries raw citizen text/audio URL (**must not be empty**).
   * `extracted_entities` carries extracted parameters, but **may be empty `{}`** if AI extraction failed completely.
2. **Officer Adjudication:** Human officer inspects case in District Review Dashboard and submits the Caseworker Review Outcome Decision:
   * **Option A — `MANUAL_APPROVE`:** Must provide `approved_amount > 0.0` and `review_notes` (min length 5). System assigns `disbursement_txn_id` with `disbursement_status = PENDING`.
   * **Option B — `MANUAL_REJECT`:** Must provide `rejection_reason` and `review_notes`. Application transitions to `REJECTED`.
   * **Option C — `REQUEST_MORE_INFO`:** Must provide `review_notes` detailing missing info. Application transitions to **`INFO_REQUESTED`** so the system can re-engage the citizen over WhatsApp/USSD.
     * **Clarification Resolution (`INFO_REQUESTED` $\rightarrow$ `UNDER_REVIEW`):** When the citizen replies over their conversational channel with the requested details, the system captures the input, attaches it to the open escalation ticket (`SPP-CASE-YYYY-XXXXXX`), and transitions the status strictly back to **`UNDER_REVIEW`** (marked as *"Clarification Received"* in the caseworker dashboard) for final officer adjudication. Because an officer explicitly initiated the clarification inquiry against an open case, the claim remains in the caseworker queue until a terminal decision (`MANUAL_APPROVE` or `MANUAL_REJECT`) is reached.

---

### 3.3 Flow 3: Asynchronous Treasury Payment Clearing

```
[ Payment Rail Dispatcher ] ──(disbursement_txn_id instruction)──> [ NPCI / PFMS Gateway ]
                                                                            │
                                                          (Bank Clearing / UTR Generation)
                                                                            │
[ Governance Ledger ] ◄── (Payment Clearing Callback with bank_reference_id) ─┘
  └─ Sets SUCCESS (with bank_reference_id UTR) or FAILED (with failure_reason_code)
```

1. **Dispatch:** Payment worker queries approved claims where `disbursement_status == PENDING` and transmits batch instructions to NPCI / PFMS using our internal `disbursement_txn_id`, updating status to `INITIATED`.
2. **Callback Handling:** External bank rails send an asynchronous status callback (*Payment Clearing Callback Contract*):
   * Matches against our internal instructional order key `disbursement_txn_id`.
   * If `disbursement_status == SUCCESS`: Strictly requires the bank-generated external transaction ID / UTR (`bank_reference_id`). Sets `failure_reason_code = None`, confirming successful payout clearing.
   * If `disbursement_status in (FAILED, RETURNED)`: Requires non-empty `failure_reason_code` (e.g., `ACCOUNT_BLOCKED`, `INVALID_IFSC`, `NAME_MISMATCH`).

---

## 4. Workflow Payload Contracts & Idempotency Rationale

To adhere to architectural DRY principles and eliminate documentation drift, the authoritative canonical Pydantic model definitions, field type annotations, and conditional validation rules are centrally standardized in **[Step 2.0: Canonical Domain Contracts & Data Schema Design](./step2.0_canonical_domain_schemas.md)**.

### 4.1 Workflow to Domain Schema Mapping

Every governance state transition defined in Section 2 and executed via the workflows in Section 3 binds directly to a validated domain contract:

| Governance Workflow / Execution Flow | Canonical Data Schema Contract | Consuming Architectural Layer |
| :--- | :--- | :--- |
| **Flow 1: Straight-Through Processing** | *Governance Adjudication Outcome* | Layer 4 Orchestration Brain |
| **Flow 2: Incident Ticket Staging** | *Caseworker Case Review Contract* | Layer 4 Case Management Service |
| **Flow 2: Officer Adjudication** | *Caseworker Review Outcome Contract* | Layer 4 Case Management Service |
| **Flow 3: Treasury Payment Clearing** | *Disbursement Callback Contract* | Layer 4 Payment Rails Integration |

---

### 4.2 Financial Idempotency Rationale: `disbursement_txn_id` vs. `bank_reference_id`

During Flow 3 (Asynchronous Treasury Payment Clearing), financial reconciliation across sovereign bank rails requires separating internal instruction keys from external banking proofs:

* **`disbursement_txn_id` (Internal Instruction Order Key):** Generated internally by AgriStack when a claim is **approved** (at Layer 4 auto-approval or caseworker manual approval) *before* dispatch to the bank. Acts as AgriStack's internal idempotency key so payment instructions can be retried across network interruptions without creating duplicate payouts. This is **not** the bank transaction ID.
* **`bank_reference_id` (External Bank Transaction ID / UTR):** Generated autonomously by the bank / sovereign payment clearing rail (NPCI APBS or PFMS Treasury Gateway) upon financial wire clearing. Serves as the immutable bank-certified Unique Transaction Reference (UTR) or bank transaction ID for banking reconciliation and citizen payout receipts.

---

## 5. Security, Idempotency & Audit Traceability Matrix

| Feature | Enforcement Mechanism | Purpose |
| :--- | :--- | :--- |
| **Zero-PII Privacy** | SHA-256 HMAC Tokenization (`HmacCitizenToken`) | Guarantees Aadhaar / Phone numbers are never exposed in ledger tables. |
| **Double-Dipping Prevention** | Database `UNIQUE(tokenized_identity_hash, season)` & Pre-checkout check | Prevents citizens from receiving duplicate automated payouts in the same season. |
| **Idempotency vs. Bank Clearing** | Internal `disbursement_txn_id` vs. External Bank ID (`bank_reference_id` UTR) | Internal `disbursement_txn_id` guarantees retry idempotency without duplicate bank orders; external `bank_reference_id` is the bank-generated transaction ID providing proof of clearing. |
| **Audit Traceability** | `application_governance_ledger_history` append-only table | Records every state change, actor ID (`SYSTEM:{ver}` or Officer UUID), and justification notes. |
| **Strict Type Safety** | Pydantic `StrictBaseModel` & `str_strip_whitespace=True` | Automatically strips leading/trailing spaces and enforces strict type boundaries. |
