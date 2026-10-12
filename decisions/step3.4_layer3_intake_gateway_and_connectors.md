# Step 3.4: Channel Connectors & Layer 3 Intake Architecture

> Sequence authority: [roadmap.md](../roadmap.md).

## 1. Scope and Layer Boundaries

This record defines the channel-adaptation responsibilities of Layer 1 and the modality-processing responsibilities of Layer 3. Layer 2 is a separate security boundary governed by the [security and ingestion firewall architecture](./step3.2_security_and_ingestion_firewalls.md).

```text
  ┌────────────────────────────────────────────────────────────────────────┐
  │                 LAYER 1: CHANNEL EDGE CONNECTORS                       │
  │  - Validate carrier format and adapt transport                         │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼ (Raw Ingress Payloads)
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
  │                     [ GATE 1: MODALITY & STRUCTURE ]                   │
  │  - Public Agent API Surface (Perimeter Entrypoint & Workflow Facade)   │
  │  - Intake Entity Extractor (Modality Transcription & SLM Extraction)   │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼ (Extracted Domain Entity Contract)
  ┌────────────────────────────────────────────────────────────────────────┐
  │                 LAYER 4: DPI ORCHESTRATOR BRAIN                        │
  │  - Claim Governance Engine (Gate 2 Completeness -> Gate 3 Adjudication)│
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

## 4. Layer 3: Public Agent Intake Gateway Surface (Gate 1)

Layer 3 provides the public API facade and executes **Gate 1: Ingress Modality & Structure Gate** of the Three-Gate Governance Architecture:

### 4.1 Public Agent API
* Acts as the public intake surface bridging Layer 2 perimeter security, Layer 3 entity extraction (Gate 1), Layer 4 governance (Gates 2 & 3), and outbound delivery.
* Executes the end-to-end processing pipeline from carrier ingress to citizen confirmation delivery.

### 4.2 Gate 1: Intake Entity Extractor & Fast-Path Menu Bypass
The Intake Entity Extractor operationalizes **Gate 1**, converting standardized intake contracts into structured domain entity contracts based on interaction determinism:

| Structure Level / Modality | Ingress Type | Processing Path | Performance & Architectural Impact |
| :--- | :--- | :--- | :--- |
| **`MENU_SELECTION` / `DTMF_SELECTION`** | USSD (`*147#`), IVR Keypad (`1#`) | **Structured Bypass** (Deterministic Mapping) | Avoids model inference for validated menu choices; the contract uses a fixed confidence baseline of `1.0`, not a calibrated model score. **Saves ~800ms GPU inference latency** and completely eliminates AI hallucinations for deterministic menu choices (Confidence = 1.0) |
| **`FREE_TEXT` (Audio Modality)** | IVR Voice Calls, WhatsApp Audio | **Speech ASR + Sovereign SLM** | Transcribes audio via Speech-to-Text (Bhashini ASR) and parses domain parameters via Small Language Models. |
| **`FREE_TEXT` (Text Modality)** | WhatsApp Chat, SMS | **Sovereign SLM** | Parses unstructured regional language text into canonical domain parameters (`district`, `crop_name`, `survey_number`). |

---

## 5. Architectural Responsibilities Matrix

| Architectural Layer | Subsystem / Component | Primary Responsibilities |
| :--- | :--- | :--- |
| **Layer 1 Edge Connectors** | *Carrier Connectors (WhatsApp, IVR, USSD, SMS)* | Carrier webhook reception, modality validation, and outbound dispatch. |
| **Layer 2 Perimeter Security** | *Perimeter Security Gateway* | Carrier auth, rate-limiting, RAM-only tokenization, PII purge, threat inspection, and canonicalization. |
| **Layer 3 Public Intake API** | *Public Agent Gateway & Intake Entity Extractor* | **Gate 1:** Public intake submission API, speech transcription, USSD menu fast-path bypass, and SLM domain entity extraction. |
| **Layer 4 Governance Brain** | *Claim Governance Engine* | **Gates 2 & 3:** Mandatory completeness validation (`District`, `Crop Name`), multi-turn reprompting, deterministic policy adjudication, and disbursement staging. |
| **Domain Contracts** | *Canonical Ingress, Intake & Entity Contracts* | Raw ingress, standardized zero-PII intake, and extracted entity payload schemas. |
