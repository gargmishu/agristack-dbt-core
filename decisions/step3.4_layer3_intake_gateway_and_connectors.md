# Step 3.4: Layer 3 Intake Gateway & Layer 1/2 Connectors Architecture

## 1. Executive Summary & Architectural Overview

This document defines the architectural specifications, transport ingestion lifecycle, and public API gateway contracts for **Phase 3, Step 3.4: Layer 3 Intake Gateway & Layer 2 Connectors** (and **Step 3.4.1: API Access Layer Architecture Decision**) of the AgriStack Zero-Trust DPI Orchestrator.

The ingress architecture decouples carrier transport protocols, perimeter security validation, and public agent intake evaluation:

```text
  ┌────────────────────────────────────────────────────────────────────────┐
  │                 LAYER 1: CHANNEL EDGE CONNECTORS                       │
  │  - WhatsAppConnector (Meta Cloud API / BSP Webhooks)                  │
  │  - IvrConnector      (SIP Trunk / Telephony Gateways)                 │
  │  - UssdConnector     (SS7 / SIGTRAN Menu Signaling)                   │
  │  - SmsConnector      (TRAI DLT Transactional SMS Webhooks)            │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼ (Raw Ingress Payloads: WhatsApp/IVR/USSD/SMS)
  ┌────────────────────────────────────────────────────────────────────────┐
  │                 LAYER 2: PERIMETER SECURITY & GATEWAY                  │
  │  - CarrierAuthValidator       (HMAC-SHA256 Signatures & Bearer Tokens) │
  │  - RateLimiter                (Per-Caller Token-Bucket Quota)          │
  │  - ZeroTrustIdentityTokenizer (RAM-Only SHA-256 HMAC Pseudonymization) │
  │  - PiiPurgeGuard              (Zero Cleartext PII Assertion Sentinel)  │
  │  - AdversarialPromptFirewall  (Prompt Injection & Jailbreak Defense)   │
  │  - PayloadCanonicalizer       (Normalizes to Standardized Intake JSON) │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼ (PublicAgentStandardizedIntakePayload)
  ┌────────────────────────────────────────────────────────────────────────┐
  │             LAYER 3: PUBLIC AGENT INTAKE GATEWAY SURFACE               │
  │  - PublicAgentApi             (Public Intake API Surface)              │
  │  - IntakePayloadEvaluator     (Structure Level & NLU Bypass Evaluator) │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼ (Prepared Intake Context)
  ┌────────────────────────────────────────────────────────────────────────┐
  │                 LAYER 4: DPI ORCHESTRATOR BRAIN                        │
  │  - ClaimOrchestrator          (Gate 1 -> Gate 2 -> Gate 3 Pipeline)    │
  └────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Layer 1: Channel Edge Connectors

Edge connectors interface with carrier networks and external telecommunication providers, validating raw payload structures and bridging transport-level communications.

### 2.1 WhatsApp Connector (`WhatsAppConnector`)
* **Transport Protocol:** HTTPS Webhooks (Meta Graph API / WhatsApp Cloud API & authorized BSPs).
* **Ingress Contract:** [`WhatsAppIngressPayload`](../src/data_models/raw_ingress/whatsapp_payload.py).
* **Modality Invariant:** Strictly enforces mutual exclusivity between text messages (`text_body`) and voice recordings (`audio_recording_url`, `audio_duration_seconds`).
* **Egress Dispatch:** Transmits formatted markdown notification cards and returns a `TransmissionAck` with a carrier message ID (`wamid`).

### 2.2 IVR Telephony Connector (`IvrConnector`)
* **Transport Protocol:** SIP Trunk / SS7 Telephony Gateway webhooks.
* **Ingress Contract:** [`IvrIngressPayload`](../src/data_models/raw_ingress/ivr_payload.py).
* **Audio Constraint:** Enforces valid signed audio URLs and duration boundaries between 1 and 600 seconds (`AudioDurationSeconds`).
* **Egress Dispatch:** Dispatches pre-signed Bhashini TTS voice stream playback URLs.

### 2.3 USSD Menu Signaling Connector (`UssdConnector`)
* **Transport Protocol:** Cellular SS7 / SIGTRAN signaling frames.
* **Ingress Contract:** [`UssdIngressPayload`](../src/data_models/raw_ingress/ussd_payload.py).
* **Shortcode & Digit Routing:** Validates routing shortcodes (e.g., `*147#`) and concatenated digit strings (e.g., `1*2*1`) bounded by menu depth calculations (max 64 characters).
* **Egress Dispatch:** Transmits compact text strings strictly bounded to 160 characters (GSM 7-bit standard).

### 2.4 SMS Connector (`SmsConnector`)
* **Transport Protocol:** TRAI DLT-registered transactional SMS webhooks.
* **Ingress Contract:** [`SmsIngressPayload`](../src/data_models/raw_ingress/sms_payload.py).
* **Validation:** Enforces E.164 phone formatting, non-empty cleartext body, and unique `channel_message_id`.
* **Egress Dispatch:** Dispatches concise status updates and toll-free helpline references.

---

## 3. Layer 2: Ingestion Perimeter & Canonicalization

Before raw carrier data enters Layer 3, [`IngestionFirewall`](../src/gateway/ingestion_firewall.py) and [`PayloadCanonicalizer`](../src/gateway/payload_canonicalizer.py) execute perimeter controls:

1. **Carrier Authentication:** [`CarrierAuthValidator`](../src/gateway/carrier_auth_validator.py) verifies `X-Hub-Signature-256` HMAC signatures or Bearer tokens.
2. **Rate Limiting:** [`RateLimiter`](../src/gateway/rate_limiter.py) tracks request allowances per caller identifier.
3. **RAM-Only Tokenization:** [`ZeroTrustIdentityTokenizer`](../src/gateway/zero_trust_identity_tokenizer.py) generates a 64-character SHA-256 HMAC digest (`HmacCitizenToken`) from the caller's MSISDN using `AGRISTACK_PEPPER_SECRET`.
4. **PII Purge Sentinel:** [`PiiPurgeGuard`](../src/gateway/pii_purge_guard.py) asserts zero raw phone numbers or Aadhaar numbers leak into downstream fields.
5. **Prompt Injection Inspection:** [`AdversarialPromptFirewall`](../src/gateway/adversarial_prompt_firewall.py) scans text inputs for injection and override patterns.
6. **Canonical Schema Normalization:** Transforms raw inputs into the canonical cross-channel contract: [`PublicAgentStandardizedIntakePayload`](../src/data_models/public_agent/standardized_intake_payload.py).

---

## 4. Layer 3: Public Agent Intake Gateway Surface

Layer 3 provides the public API facade and structural routing classification:

### 4.1 Public Agent API (`PublicAgentApi`)
* Acts as the intake surface receiving [`PublicAgentStandardizedIntakePayload`](../src/data_models/public_agent/standardized_intake_payload.py).
* Invokes [`IntakePayloadEvaluator`](../src/public_agent/intake_payload_evaluator.py) to assess structural integrity before forwarding to the Layer 4 state machine.

### 4.2 Structural Evaluation & Fast-Path Menu Bypass
[`IntakePayloadEvaluator`](../src/public_agent/intake_payload_evaluator.py) inspects the payload `structure_level`:

| Structure Level (`StructureLevel`) | Modality / Channel | Evaluation Outcome (`IntakeEvaluationResult`) | Performance & Architectural Impact |
| :--- | :--- | :--- | :--- |
| **`MENU_SELECTION` / `DTMF_SELECTION`** | USSD (`*147#`), IVR Keypad (`1#`) | `requires_nlu_extraction = False` (Structured Bypass) | **Saves ~800ms GPU inference latency** and completely eliminates AI hallucinations for deterministic menu choices. |
| **`FREE_TEXT`** | WhatsApp Chat, SMS, Voice Notes | `requires_nlu_extraction = True` (NLU Routing) | Directs unstructured regional language text to the SLM entity extraction pipeline. |
| **Empty / Whitespace** | Any | `is_valid = False` (Rejected) | Rejects malformed or whitespace-only inputs at the intake boundary. |

---

## 5. Step 3.4.1 Architectural Decision: Thin Application Service vs. Database-Native Endpoints

### Context & Options Considered

In Step 3.4.1, we evaluated two architectural paradigms for the API Access Layer:
1. **Option A: Database-Native Direct Endpoints (PostgREST / Supabase REST)**: Exposing database tables/views directly via auto-generated HTTP endpoints.
2. **Option B: Thin Application-Layer Gateway Service (FastAPI / Pydantic v2)**: Implementing a dedicated application service sitting between carrier connectors and internal orchestration services.

### Comparative Evaluation Matrix

| Architectural Dimension | Option A: Database-Native REST (PostgREST) | Option B: Thin Application Service (FastAPI) [SELECTED] |
| :--- | :--- | :--- |
| **Zero-Trust PII Tokenization** | ❌ Hard: Raw PII would reach database transport logs before in-memory hashing. | ✅ **Native:** In-memory RAM tokenization occurs *before* data touches disk or database. |
| **Carrier Auth & HMAC Signatures** | ❌ Complex: Difficult to verify Meta `X-Hub-Signature-256` or SIP headers in DB views. | ✅ **Native:** Custom cryptographic auth validator middleware (`CarrierAuthValidator`). |
| **Dynamic Multimodal Routing** | ❌ Static: Cannot orchestrate Bhashini ASR, NMT translation, or SLM inference dynamically. | ✅ **Native:** Asynchronous Python service coordinating external AI and DPI microservices. |
| **Rate Limiting & Threat Defense** | ⚠️ Generic: Basic connection limits; lacks prompt injection inspection. | ✅ **Native:** Token-bucket limiter (`RateLimiter`) and regex threat firewall (`AdversarialPromptFirewall`). |
| **Type Safety & Domain Contracts** | ⚠️ SQL-level constraints; lacks rich Pydantic v2 runtime validation models. | ✅ **Native:** Strict Pydantic v2 domain models with extra-field prohibition and custom validators. |

### Decision
**Adopt Option B: Thin Application-Layer Service.**
The zero-PII security mandate, cryptographic webhook verification, adversarial firewall scanning, and fast-path structured menu routing strictly require application-level execution in volatile RAM before any state persistence occurs.

---

## 6. Traceability Matrix & File Manifest

| Roadmap Component | Implementation File | Primary Responsibilities |
| :--- | :--- | :--- |
| **Layer 1 Edge Connectors** | [`src/connectors/whatsapp_connector.py`](../src/connectors/whatsapp_connector.py)<br>[`src/connectors/ivr_connector.py`](../src/connectors/ivr_connector.py)<br>[`src/connectors/ussd_connector.py`](../src/connectors/ussd_connector.py)<br>[`src/connectors/sms_connector.py`](../src/connectors/sms_connector.py) | Carrier webhook reception, modality validation, and outbound dispatch. |
| **Layer 2 Perimeter Security** | [`src/gateway/ingestion_firewall.py`](../src/gateway/ingestion_firewall.py)<br>[`src/gateway/carrier_auth_validator.py`](../src/gateway/carrier_auth_validator.py)<br>[`src/gateway/zero_trust_identity_tokenizer.py`](../src/gateway/zero_trust_identity_tokenizer.py)<br>[`src/gateway/pii_purge_guard.py`](../src/gateway/pii_purge_guard.py)<br>[`src/gateway/adversarial_prompt_firewall.py`](../src/gateway/adversarial_prompt_firewall.py)<br>[`src/gateway/payload_canonicalizer.py`](../src/gateway/payload_canonicalizer.py)<br>[`src/gateway/rate_limiter.py`](../src/gateway/rate_limiter.py) | Carrier auth, rate-limiting, RAM-only tokenization, PII purge, threat inspection, and canonicalization. |
| **Layer 3 Public Intake API** | [`src/public_agent/public_agent_api.py`](../src/public_agent/public_agent_api.py)<br>[`src/public_agent/intake_payload_evaluator.py`](../src/public_agent/intake_payload_evaluator.py) | Public intake submission API, structure-level evaluation, and NLU bypass routing. |
| **Domain Contracts** | [`src/data_models/raw_ingress/`](../src/data_models/raw_ingress/)<br>[`src/data_models/public_agent/`](../src/data_models/public_agent/) | Pydantic v2 raw ingress and standardized zero-PII intake payload schemas. |
