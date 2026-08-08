# Step 3.3: Layer 4 Orchestrator Brain & Three Evaluation Gates Architecture

## 1. Executive Summary & Orchestration Principles

This document defines the architectural specifications, state transitions, gatekeeping algorithms, and execution logic for **Phase 3, Step 3.3: Layer 4 Orchestrator Brain** within the AgriStack Zero-Trust DPI Orchestrator.

The Orchestrator Brain coordinates the end-to-end processing pipeline from normalized, zero-PII Layer 3 intake contracts ([PublicAgentStandardizedIntakePayload](../src/data_models/public_agent/standardized_intake_payload.py)) through three deterministic evaluation gates, concluding in either straight-through automated benefit clearing, manual caseworker escalation, or deterministic automated rejection.

```
[ Layer 3: Normalized Zero-PII Intake Payload ]
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
* **`PayloadType.AUDIO` (IVR voice calls & WhatsApp voice notes):**
  * Transmits the pre-signed URL pointer (`unprocessed_input_content`) to `BhashiniService.transcribe_audio()` to generate the vernacular text transcript.
  * If the audio stream is in an Indic regional dialect (e.g. `hi-IN`), dispatches to `BhashiniService.translate_text()` to normalize domain entities while retaining vernacular nuances.
* **`PayloadType.TEXT` (WhatsApp text & SMS):**
  * Directs raw text into the SLM extraction pipeline if `structure_level == StructureLevel.FREE_TEXT`.

### 2.2 Structured Fast-Path Menu Bypass
* When `structure_level in (StructureLevel.DTMF_SELECTION, StructureLevel.MENU_SELECTION)`:
  * **Zero-Inference Fast Path:** Completely bypasses GPU SLM NLU entity extraction (saving ~800ms inference latency and eliminating AI hallucinations).
  * **Deterministic Mapping:** Directs keypress sequences (e.g. `1*2*101` from USSD or WhatsApp numeric buttons) to deterministic lookup tables.
  * **Confidence Invariant:** Hardcodes `ai_confidence_score = 1.0` and sets `is_structured_menu_bypass = True`.

---

## 3. Gate 2: Intake & Intent Validation Gate

### 3.1 Intent Classification & Routing
* Evaluates the classified `ApplicationIntent`:
  * `APPLY_SUBSIDY`: Initiates seasonal crop damage relief claim flow.
  * `CHECK_STATUS`: Directs query to read-only citizen status ledger lookup.
  * `SUBMIT_APPEAL`: Routes rejected claim context to caseworker appellate review queue.
  * `GRIEVANCE_REDIRECTION` / `SCHEME_INQUIRY`: Routes to read-only informational portal.

### 3.2 Mandatory Entity Completeness & Multi-Turn Correction Loops
* For `APPLY_SUBSIDY` claims, the system asserts the presence of mandatory domain entities:
  * `DomainEntityKey.DISTRICT`
  * `DomainEntityKey.CROP_NAME`
  * `DomainEntityKey.SURVEY_NUMBER`
* **Multi-Turn Conversational Re-Prompt Logic:**
  * If any mandatory domain entity is missing and conversational `attempt_count < 3`:
    * Transitions state to `INFO_REQUESTED`.
    * Returns conversational re-prompt instruction (`TRIGGER_CHANNEL_REPROMPT_INGRESS`) requesting the specific missing field from the citizen.
  * If mandatory entities remain missing after $3$ attempts (`attempt_count >= 3`):
    * Halts conversational loops to prevent drop-off fatigue.
    * Stages an escalation ticket into the District Caseworker Queue (`ROUTE_FOR_MANUAL_REVIEW`).

---

## 4. Gate 3: Deterministic Governance Routing Matrix

### 4.1 DPI Cross-Matching & Anti-Double-Dipping Checks
Gate 3 evaluates three independent verification criteria:
1. **Sovereign Identity Verification:** `IdentityVerificationService.verify_identity_token(tokenized_citizen_id) == True`.
2. **Cadastral & Crop Landholding Match:** `AgriRegistryService.verify_land_record(tokenized_citizen_id, land_record_id) == True`.
3. **Anti-Double-Dipping Ledger Invariant:** Confirms that no approved claim exists for `(tokenized_citizen_id, active_scheme_season)`.

### 4.2 Tri-State Governance Adjudication

| Governance Condition | Action (`GovernanceAction`) | Application Status | Financial State (`DisbursementStatus`) | Generated Artifacts |
| :--- | :--- | :--- | :--- | :--- |
| $\text{Score} \ge 0.85 \land \text{Eligible} \land \text{No Duplicate}$ | `AUTO_APPROVE` / `AUTOMATED_PAYOUT` | `APPROVED` | `PENDING` | `disbursement_txn_id = "TXN-YYYY-XXXXXX"` |
| $\text{Score} < 0.85 \lor \text{Adversarial} \lor \text{Attempts} \ge 3$ | `ROUTE_FOR_MANUAL_REVIEW` | `UNDER_REVIEW` | `None` (Bypassed) | `escalation_case_id = "SPP-CASE-YYYY-XXXXXX"` |
| $\text{Ineligible Record} \lor \text{Duplicate Active Claim}$ | `AUTO_REJECT` | `REJECTED` | `None` (Bypassed) | `rejection_reason` (Non-empty justification) |

---

## 5. Caseworker Lifecycle & Citizen Clarification Resolution

* **Officer Manual Adjudication (`CaseworkerReviewOutcomePayload`):**
  * `MANUAL_APPROVE`: Assigns `disbursement_txn_id`, sets `disbursement_status = PENDING`, transitions application status to `APPROVED`.
  * `MANUAL_REJECT`: Records officer audit notes and mandatory `rejection_reason`, transitioning to `REJECTED`.
  * `REQUEST_MORE_INFO`: Transitions application status to `INFO_REQUESTED`, allowing citizen conversational reply.
* **Citizen Clarification Resolution Loop:**
  * When a citizen replies to an open clarification inquiry, `CaseManagementService.resolve_citizen_clarification()` captures the reply, attaches it to the active ticket, and transitions the case status back to `UNDER_REVIEW` (marked *"Clarification Received"*) for final caseworker decision.

---

## 6. Implementation Architecture & Module Split

```text
src/orchestrator/
├── __init__.py                 <-- Package exports
├── state_machine.py           <-- Core 3-Gate State Machine & Execution Loop
├── governance_router.py       <-- Decision Matrix Evaluator (Auto Approve/Reject/Review)
└── case_management_service.py <-- Internal Escalation Staging & Clarification Loops
```
