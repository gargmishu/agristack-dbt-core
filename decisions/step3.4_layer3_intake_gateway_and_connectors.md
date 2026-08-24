# Step 3.4: Layer 3 Intake Gateway & Layer 1/2 Connectors Architecture

## 1. Executive Summary & Architectural Overview

This document defines the architectural specifications, transport ingestion lifecycle, and public API gateway contracts for **Phase 3, Step 3.4: Layer 3 Intake Gateway & Layer 2 Connectors** (and **Step 3.4.1: API Access Layer Architecture Decision**) of the AgriStack Zero-Trust DPI Orchestrator.

The ingress architecture decouples carrier transport protocols, perimeter security validation, and public agent intake evaluation:

```text
  ┌────────────────────────────────────────────────────────────────────────┐
  │                 LAYER 1: CHANNEL EDGE CONNECTORS                       │
  │  - WhatsApp Connector (Meta Cloud API / BSP Webhooks)                  │
  │  - IVR Voice Connector (SIP Trunk / Telephony Gateways)                │
  │  - USSD Menu Connector (SS7 / SIGTRAN Menu Signaling)                  │
  │  - SMS Gateway Connector (TRAI DLT Transactional SMS Webhooks)         │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼ (Raw Ingress Payloads: WhatsApp/IVR/USSD/SMS)
  ┌────────────────────────────────────────────────────────────────────────┐
  │                 LAYER 2: PERIMETER SECURITY & GATEWAY                  │
  │  - Carrier Transport Authenticator (HMAC-SHA256 Signatures & Tokens)   │
  │  - Ingress Rate Limiter (Per-Caller Token-Bucket Quota Sentinel)       │
  │  - Zero-Trust Identity Tokenizer (RAM-Only SHA-256 HMAC Pseudonymization)
  │  - PII Purge Sentinel (Zero Cleartext PII Invariant Check)             │
  │  - Adversarial Prompt Firewall (Prompt Injection & Threat Defense)     │
  │  - Ingress Payload Canonicalizer (Normalizes to Standardized Intake)   │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼ (Standardized Intake Contract)
  ┌────────────────────────────────────────────────────────────────────────┐
  │             LAYER 3: PUBLIC AGENT INTAKE GATEWAY SURFACE               │
  │  - Public Agent API Surface (Perimeter Entrypoint)                     │
  │  - Intake Payload Evaluator (Structure Level & NLU Bypass Evaluator)   │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼ (Evaluated Intake Context)
  ┌────────────────────────────────────────────────────────────────────────┐
  │                 LAYER 4: DPI ORCHESTRATOR BRAIN                        │
  │  - Claim Orchestration Engine (Gate 1 -> Gate 2 -> Gate 3 Pipeline)    │
  └────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Layer 1: Channel Edge Connectors

Edge connectors interface with carrier networks and external telecommunication providers, validating raw payload structures and bridging transport-level communications.

### 2.1 WhatsApp Connector
* **Transport Protocol:** HTTPS Webhooks (Meta Graph API / WhatsApp Cloud API & authorized BSPs).
* **Ingress Contract:** WhatsApp Ingress Contract.
* **Modality Invariant:** Strictly enforces mutual exclusivity between text messages and voice recordings.
* **Egress Dispatch:** Transmits formatted markdown notification cards and returns a carrier transmission acknowledgment receipt.

### 2.2 IVR Telephony Connector
* **Transport Protocol:** SIP Trunk / SS7 Telephony Gateway webhooks.
* **Ingress Contract:** IVR Voice Ingress Contract.
* **Audio Constraint:** Enforces valid signed audio URLs and duration boundaries between 1 and 600 seconds.
* **Egress Dispatch:** Dispatches pre-signed Bhashini TTS voice stream playback URLs.

### 2.3 USSD Menu Signaling Connector
* **Transport Protocol:** Cellular SS7 / SIGTRAN signaling frames.
* **Ingress Contract:** USSD Ingress Contract.
* **Shortcode & Digit Routing:** Validates routing shortcodes (e.g., `*147#`) and concatenated digit strings (e.g., `1*2*1`) bounded by menu depth calculations (max 64 characters).
* **Egress Dispatch:** Transmits compact text strings strictly bounded to 160 characters (GSM 7-bit standard).

### 2.4 SMS Connector
* **Transport Protocol:** TRAI DLT-registered transactional SMS webhooks.
* **Ingress Contract:** SMS Ingress Contract.
* **Validation:** Enforces E.164 phone formatting, non-empty cleartext body, and unique channel message identifier.
* **Egress Dispatch:** Dispatches concise status updates and toll-free helpline references.

---

## 3. Layer 2: Ingestion Perimeter & Canonicalization

Before raw carrier data enters Layer 3, the Perimeter Security Gateway executes perimeter controls:

1. **Carrier Authentication:** Verifies `X-Hub-Signature-256` HMAC signatures or Bearer tokens via constant-time comparison.
2. **Rate Limiting:** Tracks request allowances per caller identifier via a token-bucket algorithm.
3. **RAM-Only Tokenization:** Generates a 64-character SHA-256 HMAC digest from the caller's MSISDN using an injected cryptographic pepper (`AGRISTACK_PEPPER_SECRET`).
4. **PII Purge Sentinel:** Asserts zero raw phone numbers or Aadhaar numbers leak into downstream fields.
5. **Prompt Injection Inspection:** Scans text inputs for injection, jailbreak, and override patterns.
6. **Canonical Schema Normalization:** Transforms raw inputs into the canonical cross-channel contract (*Standardized Intake Payload*).

---

## 4. Layer 3: Public Agent Intake Gateway Surface

Layer 3 provides the public API facade and structural routing classification:

### 4.1 Public Agent API
* Acts as the public intake surface receiving the Standardized Intake Payload.
* Invokes the Intake Payload Evaluator to assess structural integrity before forwarding to the Layer 4 state machine.

### 4.2 Structural Evaluation & Fast-Path Menu Bypass
The Intake Evaluator inspects the payload structure level:

| Structure Level | Modality / Channel | Evaluation Outcome | Performance & Architectural Impact |
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
| **Carrier Auth & HMAC Signatures** | ❌ Complex: Difficult to verify Meta `X-Hub-Signature-256` or SIP headers in DB views. | ✅ **Native:** Custom cryptographic auth validator middleware. |
| **Dynamic Multimodal Routing** | ❌ Static: Cannot orchestrate Bhashini ASR, NMT translation, or SLM inference dynamically. | ✅ **Native:** Asynchronous service coordinating external AI and DPI microservices. |
| **Rate Limiting & Threat Defense** | ⚠️ Generic: Basic connection limits; lacks prompt injection inspection. | ✅ **Native:** Token-bucket limiter and regex threat firewall. |
| **Type Safety & Domain Contracts** | ⚠️ SQL-level constraints; lacks rich runtime validation models. | ✅ **Native:** Strict domain models with extra-field prohibition and custom validators. |

### Decision
**Adopt Option B: Thin Application-Layer Service.**
The zero-PII security mandate, cryptographic webhook verification, adversarial firewall scanning, and fast-path structured menu routing strictly require application-level execution in volatile RAM before any state persistence occurs.

---

## 6. Architectural Responsibilities Matrix

| Architectural Layer | Subsystem / Component | Primary Responsibilities |
| :--- | :--- | :--- |
| **Layer 1 Edge Connectors** | *Carrier Connectors (WhatsApp, IVR, USSD, SMS)* | Carrier webhook reception, modality validation, and outbound dispatch. |
| **Layer 2 Perimeter Security** | *Perimeter Security Gateway* | Carrier auth, rate-limiting, RAM-only tokenization, PII purge, threat inspection, and canonicalization. |
| **Layer 3 Public Intake API** | *Public Agent Gateway* | Public intake submission API, structure-level evaluation, and NLU bypass routing. |
| **Domain Contracts** | *Canonical Ingress & Intake Contracts* | Raw ingress and standardized zero-PII intake payload schemas. |
