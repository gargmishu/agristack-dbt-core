# Step 3.6: Live Service Integration & External Endpoint Adapters

## 1. Executive Summary & Architectural Motivation

This document defines the live service integration architecture, HTTP transport adapters, resiliency patterns, and zero-PII security rules for **Phase 3, Step 3.6: Live Service Integration** within the AgriStack Zero-Trust DPI Orchestrator.

Step 3.6 provides production-ready HTTP client adapters that connect internal service abstractions to live sovereign AI models (Bhashini Speech & Translation, Sovereign SLM) and authoritative national DPI registries (MOSIP Identity, AgriStack Land Records, OpenSPP Social Protection, NPCI/PFMS Payment Rails).

```
               [ Layer 3 / Layer 4 Domain Engines ]
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
 ┌──────────────────────┐              ┌──────────────────────┐
 │ Sovereign AI Clients │              │ Authoritative DPI    │
 │                      │              │ Registry Clients     │
 │ - Bhashini ASR/NMT   │              │ - MOSIP Token Auth   │
 │ - Sovereign SLM NLU  │              │ - AgriStack Cadastre │
 │ - Vernacular TTS     │              │ - OpenSPP Caseworker │
 │                      │              │ - NPCI/PFMS Clearing │
 └──────────┬───────────┘              └──────────┬───────────┘
            │ (Async HTTP / mTLS)                 │ (Async HTTP / mTLS)
            ▼                                     ▼
 ┌──────────────────────┐              ┌──────────────────────┐
 │ Live Cloud / Local   │              │ Sovereign National   │
 │ Sovereign Endpoints  │              │ DPI Digital Rails    │
 └──────────────────────┘              └──────────────────────┘
```

---

## 2. Core Integration Invariants & Resiliency Rules

1. **The Fallback Resilience Invariant:**
   When an external live service endpoint is unconfigured (`None`), unreachable (connection timeout), or returns a non-200 HTTP error, the service client gracefully falls back to deterministic local mock fixtures, guaranteeing system availability and deterministic testability.
2. **The Zero-PII Transport Invariant:**
   All outbound HTTP requests to external DPI endpoints must use 64-character SHA-256 HMAC identity tokens. Cleartext citizen identifiers (MSISDN, Aadhaar numbers, unhashed citizen names) are strictly forbidden in URL path parameters, query strings, headers, and request bodies.
3. **Strict Timeout Ceilings:**
   - AI Perception Services (ASR, NMT, SLM): 2.0-second connection & read timeout.
   - Authoritative DPI Registries (MOSIP, AgriStack, OpenSPP): 3.0-second timeout.
   - Financial Clearing Rails (NPCI, PFMS): 5.0-second timeout with idempotent transaction key tracking.
4. **Header Sanitization & Redaction:**
   All outbound API keys and Bearer tokens are injected via secure client configuration and strictly masked in all telemetry logs.

---

## 3. Sovereign AI Service Adapters

### 3.1 Speech & Translation Client (Bhashini ASR / NMT / TTS)
* **ASR Transcription:** Dispatches audio URLs to `/v1/asr/transcribe` with target language locale.
* **NMT Translation:** Dispatches regional vernacular text to `/v1/nmt/translate` for domain normalization.
* **TTS Synthesis:** Dispatches synthesized text to `/v1/tts/synthesize` to generate vernacular audio stream URLs.

### 3.2 Sovereign SLM Entity Extractor Client
* Dispatches sanitized, zero-PII conversational text to `/v1/extract` with structured JSON schema specifications.
* Injects structured prompt system rules requiring extraction confidence scores and standardized domain entity mappings (`district`, `crop_name`, `survey_number`).

---

## 4. Authoritative DPI Registry Adapters

### 4.1 MOSIP Identity Token Verification Client
* Queries `/v1/identity/verify` with the 64-character SHA-256 HMAC identity token.
* Returns verified eligibility and identity assurance indicators.

### 4.2 AgriStack Cadastral Land Registry Client
* Queries `/v1/land/cadastral/{district}/{survey_number}` with HMAC citizen tokens.
* Validates parcel ownership, crop sowing declaration, and seasonal entitlements.

### 4.3 OpenSPP Social Welfare Registry Client
* Dispatches incident tickets and caseworker review payloads to `/v1/cases/stage`.
* Synchronizes case statuses (`UNDER_REVIEW`, `APPROVED`, `REJECTED`, `INFO_REQUESTED`).

### 4.4 NPCI / PFMS Payment Rail Client
* Dispatches asynchronous disbursement requests to `/v1/payments/disburse` with idempotent `disbursement_txn_id`.
* Returns payment initiation confirmation receipts (`DisbursementStatus = PENDING` / `SUCCESS`).

---

## 5. Verification & Testing Matrix

1. **Live Adapter Connectivity Tests:** Validates successful HTTP request serialization, header injection, and JSON response parsing against simulated live endpoints.
2. **Graceful Mock Fallback Tests:** Verifies seamless fallback to deterministic fixtures when endpoints are unconfigured or simulate network timeouts.
3. **Zero-PII Transport Audits:** Asserts zero cleartext identifiers in outbound HTTP request payloads and headers.
4. **Timeout & Error Resilience Tests:** Confirms proper exception handling across HTTP 500, HTTP 503, and connection timeout scenarios.
