# Step 3.5: Adaptive Multichannel Confirmation Delivery Architecture

## 1. Executive Summary & Delivery Principles

This document defines the architectural specifications, message template bindings, channel formatting constraints, and outbound dispatch logic for **Phase 3, Step 3.5: Adaptive Multichannel Confirmation Delivery** in the Master DPI Architecture.

The Confirmation Delivery engine receives final governance determination outcomes, caseworker escalation tickets, or re-prompt instructions, formats channel-native receipts adapted to the citizen's originating ingress channel (`WhatsApp`, `IVR Voice`, `USSD`, `SMS`), and dispatches outbound notifications back to the citizen.

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: Governance Outcome / Escalation / Reprompt State  │
│  - Adjudication Outcome / Incident Review Ticket State      │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│    ADAPTIVE MULTICHANNEL CONFIRMATION DISPATCH ENGINE       │
│  - Template Resolver (Outcome + Channel + Language Locale)  │
│  - Speech Synthesizer TTS (for IVR Voice audio playback)    │
│  - Channel Adapter (WhatsApp Card / USSD 160-char / SMS)    │
└─────────────────────────────┬───────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
   [ WhatsApp ]         [ IVR Voice ]           [ USSD ]
 (Rich Markdown Card)  (TTS Audio Stream)  (GSM 160-char text)
```

---

## 2. Channel-Native Formatting & Invariants

### 2.1 WhatsApp Channel
* **Format:** Rich text markdown cards with emojis, clear scheme details, transactional identifiers (`disbursement_txn_id` or `escalation_case_id`), and next action guidance.
* **Payload Modality:** Text or rich interactive card structure.

### 2.2 IVR Voice Telephony
* **Format:** Synthesized vernacular spoken audio stream.
* **TTS Pipeline:** Transmits formatted text to the Sovereign Text-to-Speech (TTS) engine in the citizen's language locale (e.g., Hindi `hi-IN`) and returns a signed audio playback stream URL.

### 2.3 USSD Menu Signaling
* **Format:** Compact plain text string.
* **Constraint:** Strict **160-character ceiling** (GSM 7-bit standard constraint) to prevent network truncation or carrier frame fragmentation over SS7/SIGTRAN signaling.

### 2.4 Transactional SMS
* **Format:** Concise alphanumeric message summary with reference identifier and official toll-free helpline.

---

## 3. Governance Outcome Template Matrix

| Governance State / Action | WhatsApp Template | IVR Voice Spoken Template | USSD String (<160 chars) | SMS Template |
| :--- | :--- | :--- | :--- | :--- |
| **`AUTO_APPROVE` / `AUTOMATED_PAYOUT`** | *"🌾 AgriStack Relief Approved! Txn: {txn_id}. Benefit credited via DBT."* | *"Aapka fasal rahat aavedan swikrit ho gaya hai. Transaction sankhya hai {txn_id}."* | *"AgriStack: Claim Approved. Txn: {txn_id}. DBT transfer initiated."* | *"AgriStack: Claim Approved. Txn: {txn_id}. Benefit sent to linked bank account."* |
| **`ROUTE_FOR_MANUAL_REVIEW`** | *"📋 Claim Under Officer Review. Incident Ticket: {case_id}. Review in progress."* | *"Aapka mamla krishi adhikari ke paas jaanch ke liye bhej diya gaya hai. Ticket: {case_id}."* | *"AgriStack: Claim Under Review. Ticket: {case_id}. Officer will inspect."* | *"AgriStack: Claim Under Review. Case ID: {case_id}. Updates will follow via SMS."* |
| **`AUTO_REJECT`** | *"❌ Claim Rejected. Reason: {rejection_reason}. Dial 1800-180-1551 to appeal."* | *"Aapka aavedan aswikrit kar diya gaya hai. Karan hai: {rejection_reason}."* | *"AgriStack: Claim Rejected ({rejection_reason}). Helpline: 1800-180-1551."* | *"AgriStack: Claim Rejected ({rejection_reason}). Visit portal or call 1800-180-1551."* |
| **`REQUEST_MORE_INFO` / Re-prompt** | *"ℹ️ Missing Information: Please provide your {missing_entity} to proceed."* | *"Kripya apna {missing_entity} batayein taaki aavedan aage badhaya ja sake."* | *"AgriStack: Missing {missing_entity}. Reply with details."* | *"AgriStack: Clarification needed for {missing_entity}. Reply to update."* |

---

## 4. Architectural Responsibilities

* **Outbound Notification Models:** Define normalized contracts for notification requests, channel payloads, delivery statuses, and transmission receipts.
* **Adaptive Multi-Channel Notification Service:** Resolves localized templates, executes text-to-speech synthesis for voice telephony, and routes outbound messages to the appropriate carrier connectors.

---

## 5. Security & Privacy Invariants

1. **Zero-PII Outbound Invariant:** Outbound receipts reference only the `session_id`, `disbursement_txn_id`, or `escalation_case_id`. Unhashed citizen names, Aadhaar numbers, and bank account numbers are strictly omitted from confirmation strings.
2. **Idempotent Dispatch:** Dispatches are keyed by `session_id` to ensure at-most-once outbound messaging per state transition.

