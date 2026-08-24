# Step 3.3: Layer 4 Orchestrator Brain & Three Evaluation Gates Architecture

## 1. Executive Summary & Orchestration Principles

This document defines the architectural specifications, state transitions, gatekeeping algorithms, and execution logic for **Phase 3, Step 3.3: Layer 4 Orchestrator Brain** within the AgriStack Zero-Trust DPI Orchestrator.

The Orchestrator Brain coordinates the end-to-end processing pipeline from normalized, zero-PII Layer 3 intake contracts (*Standardized Intake Payload*) through three deterministic evaluation gates, concluding in either straight-through automated benefit clearing, manual caseworker escalation, or deterministic automated rejection.

```
[ Layer 3: Normalized Zero-PII Intake Contract ]
                       │
                       ▼
 ┌─────────────────────────────────────────────────────────────┐
 │       GATE 1: INGRESS & STRUCTURE EVALUATION GATE           │
 │  - Audio vs. Text Modality Routing (Bhashini ASR/NMT)       │
 │  - Structured USSD/Menu Fast-Path Bypass (Score = 1.0)      │
 │  - Sovereign SLM Entity Extractor Execution                 │
 └─────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
 ┌─────────────────────────────────────────────────────────────┐
 │       GATE 2: INTAKE & INTENT VALIDATION GATE               │
 │  - Intent Classification (apply_subsidy vs status inquiry)  │
 │  - Mandatory Entity Completeness (District, Crop, Survey)   │
 │  - Multi-Turn Conversational Re-Prompt Loop (Attempts <= 3) │
 └─────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
 ┌─────────────────────────────────────────────────────────────┐
 │    GATE 3: DETERMINISTIC GOVERNANCE ROUTING MATRIX          │
 │  - DPI Cross-Matching (AgriStack Cadastral + MOSIP Token)   │
 │  - Anti-Double-Dipping Season Ledger Validation             │
 │  - Tri-State Governance Routing:                            │
 │    1. AUTO_APPROVE (Score >= 0.85 & Eligible & Unique)      │
 │    2. ROUTE_FOR_MANUAL_REVIEW (Score < 0.85 / Flagged)      │
 │    3. AUTO_REJECT (Ineligible / Duplicate Claim Detected)   │
 └─────────────────────────────┬───────────────────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
   [ Payment Rails ]   [ Caseworker Queue ]   [ Terminal Rejection ]
   (DisbursementStatus    (SPP-CASE Ticket)       (rejection_reason)
      = PENDING)
```

---

## 2. Gate 1: Ingress & Structure Evaluation Gate

### 2.1 Modality Dispatch & ASR/NMT Pipeline
* **Audio Ingress (IVR voice calls & WhatsApp voice notes):**
  * Transmits the pre-signed URL pointer to the Speech-to-Text Service (Bhashini ASR) to generate the vernacular text transcript.
  * If the audio stream is in an Indic regional dialect (e.g. Hindi `hi-IN`), dispatches to the Machine Translation Service (Bhashini NMT) to normalize domain entities while retaining vernacular nuances.
* **Text Ingress (WhatsApp text & SMS):**
  * Directs raw text into the SLM extraction pipeline if structured as free text.

### 2.2 Structured Fast-Path Menu Bypass
* When the intake structure is DTMF or menu selection:
  * **Zero-Inference Fast Path:** Completely bypasses GPU SLM NLU entity extraction (saving ~800ms inference latency and eliminating AI hallucinations).
  * **Deterministic Mapping:** Directs keypress sequences (e.g. `1*2*101` from USSD or WhatsApp numeric buttons) to deterministic lookup tables.
  * **Confidence Invariant:** Enforces confidence score $= 1.0$ and flags the payload as a structured menu bypass.

---

## 3. Gate 2: Intake & Intent Validation Gate

### 3.1 Intent Classification & Routing
* Evaluates the classified Application Intent:
  * `APPLY_SUBSIDY`: Initiates seasonal crop damage relief claim flow.
  * `CHECK_STATUS`: Directs query to read-only citizen status ledger lookup.
  * `SUBMIT_APPEAL`: Routes rejected claim context to caseworker appellate review queue.
  * `GRIEVANCE_REDIRECTION` / `SCHEME_INQUIRY`: Routes to read-only informational portal.

### 3.2 Mandatory Entity Completeness & Multi-Turn Correction Loops
* For `APPLY_SUBSIDY` claims, the system asserts the presence of mandatory domain entities:
  * `DISTRICT`
  * `CROP_NAME`
  * `SURVEY_NUMBER`
* **Multi-Turn Conversational Re-Prompt Logic:**
  * If any mandatory domain entity is missing and conversational attempts $< 3$:
    * Transitions state to `INFO_REQUESTED`.
    * Returns conversational re-prompt instruction requesting the specific missing field from the citizen.
  * If mandatory entities remain missing after $3$ attempts (attempts $\ge 3$):
    * Halts conversational loops to prevent drop-off fatigue.
    * Stages an escalation ticket into the District Caseworker Queue (`ROUTE_FOR_MANUAL_REVIEW`).

---

## 4. Gate 3: Deterministic Governance Routing Matrix

### 4.1 DPI Cross-Matching & Anti-Double-Dipping Checks
Gate 3 evaluates three independent verification criteria:
1. **Sovereign Identity Verification:** Confirms that the pseudonymous identity token exists and is valid in the sovereign identity registry (MOSIP / Aadhaar).
2. **Cadastral & Crop Landholding Match:** Cross-checks the citizen token, district, survey number, and declared crop against authoritative land records (AgriStack Registry).
3. **Anti-Double-Dipping Ledger Invariant:** Confirms that no approved claim exists for the tuple of `(tokenized_citizen_id, active_scheme_season)`.

### 4.2 Tri-State Governance Adjudication

| Governance Condition | Action | Application Status | Financial State | Generated Artifacts |
| :--- | :--- | :--- | :--- | :--- |
| $\text{Score} \ge 0.85 \land \text{Eligible} \land \text{No Duplicate}$ | `AUTO_APPROVE` | `APPROVED` | `PENDING` | `disbursement_txn_id = "TXN-YYYY-XXXXXX"` |
| $\text{Score} < 0.85 \lor \text{Adversarial} \lor \text{Attempts} \ge 3$ | `ROUTE_FOR_MANUAL_REVIEW` | `UNDER_REVIEW` | `None` (Bypassed) | `escalation_case_id = "SPP-CASE-YYYY-XXXXXX"` |
| $\text{Ineligible Record} \lor \text{Duplicate Active Claim}$ | `AUTO_REJECT` | `REJECTED` | `None` (Bypassed) | `rejection_reason` (Non-empty justification) |

---

## 5. Caseworker Lifecycle & Citizen Clarification Resolution

* **Officer Manual Adjudication:**
  * `MANUAL_APPROVE`: Assigns disbursement transaction ID, sets disbursement status to `PENDING`, and transitions application status to `APPROVED`.
  * `MANUAL_REJECT`: Records officer audit notes and mandatory rejection reason code, transitioning state to `REJECTED`.
  * `REQUEST_MORE_INFO`: Transitions application status to `INFO_REQUESTED`, opening the ticket for citizen conversational follow-up.
* **Citizen Clarification Resolution Loop:**
  * When a citizen replies to an open clarification inquiry, the Case Management Service captures the reply, attaches it to the active ticket, and transitions the case status back to `UNDER_REVIEW` (marked *"Clarification Received"*) for final caseworker decision.

---

## 6. Layer 4 Architectural Responsibilities

* **Claim Orchestrator Engine:** Coordinates the 3-gate execution cycle from intake ingestion to payout/caseworker staging.
* **Claim Adjudication Engine:** Enforces the deterministic Gate 3 rules matrix (Auto-Approve vs. Manual Review vs. Auto-Reject).
* **Case Management Service:** Manages incident tickets, officer adjudication workflows, audit trails, and citizen clarification loops.
