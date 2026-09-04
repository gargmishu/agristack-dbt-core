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
 │ - Connection Pool    │              │ - NPCI/PFMS Clearing │
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

### 2.1 Production Invariants

1. **Fail-Closed & Zero Mock Leakage in Production:**
   In production runtime environments, service clients must strictly communicate with live authoritative sovereign endpoints. If an authoritative registry (MOSIP, AgriStack, OpenSPP) or financial rail (NPCI/PFMS) is unreachable, times out, or returns a 5xx server error, the system must **fail closed**—raising service unavailable exceptions and routing claims to manual caseworker review. Falling back to local mock fixtures in production is strictly prohibited to prevent fraudulent payouts or invalid benefit determinations on simulated data.
2. **Fail-Fast Startup Configuration:**
   In production mode, all external endpoint URLs and authentication credentials are mandatory. If any required service endpoint or API key is unconfigured or blank, container startup fails immediately with an explicit configuration error, enforcing the Zero-Trust principle of never running with missing secrets or unconfigured endpoints.
3. **Persistent Singleton HTTP Connection Pooling:**
   Production workloads mandate a process-wide, persistent HTTP client connection pool with strict connection limits, keep-alive recycling, and reuse across requests. Ephemeral per-request HTTP client creation is prohibited in production to prevent socket file descriptor exhaustion (thousands of sockets in `TIME_WAIT`) and eliminate per-request TLS handshake latency overhead.
4. **The Zero-PII Transport Invariant:**
   All outbound HTTP requests to external DPI endpoints must use 64-character SHA-256 HMAC identity tokens. Cleartext citizen identifiers (MSISDN, Aadhaar numbers, unhashed citizen names) are strictly forbidden in URL path parameters, query strings, headers, and request bodies.
5. **Strict Timeout Ceilings:**
   - AI Perception Services (ASR, NMT, SLM): 2.0-second connection & read timeout.
   - Authoritative DPI Registries (MOSIP, AgriStack, OpenSPP): 3.0-second timeout.
   - Financial Clearing Rails (NPCI, PFMS): 5.0-second timeout with idempotent transaction key tracking.
6. **Header Sanitization & Redaction:**
   All outbound API keys and Bearer tokens are injected via secure client configuration and strictly masked in all telemetry logs.
7. **Static RPC Path Constants & Centralized Transport URL Resolution:**
   All sovereign service RPC endpoint paths are defined as static constants within each service adapter boundary. Path resolution, leading/trailing slash trimming, and base endpoint URL concatenation are delegated exclusively to the centralized HTTP transport layer. This eliminates ad-hoc string formatting, prevents double-slash routing defects, and provides a single locus of control for network path resolution across all DPI adapters.

### 2.2 Non-Production / Offline Simulation Invariant & Protocol Segregation

* **Protocol Segregation & Explicit Mock Implementations:**
  External service boundaries are structured via clean structural protocols. Live clients strictly encapsulate production HTTPS transport with mandatory credentials and persistent connection pooling—incorporating zero mock fallback logic. Non-production environments (local development, offline testing, CI/CD pipelines) utilize dedicated mock implementations providing deterministic simulation. Environment-aware factory functions bind the appropriate client implementation based on deployment mode, preventing any simulated data logic from existing within live client execution paths.

* **Three-Tier Credential Precedence & Test Isolation Policy:**
  Service adapter factory construction enforces a deterministic three-tier precedence model to balance production safety with agile local and CI testing:
  1. **Explicit Injected Coordinates (Tier 1):** When an explicit endpoint URL and authentication key are supplied directly to the service factory, a live transport client is constructed targeting those specific coordinates regardless of whether the broader environment demands live operation. This supports local stub and containerized mock server testing (such as HTTP stubbing proxies) during automated integration pipelines and development without requiring global production configurations.
  2. **Mandatory Production Runtime (Tier 2):** When operating in production mode (or when live transport is explicitly required), the factory resolves configuration from environment variables and fails fast with fatal configuration errors if endpoints or credentials are absent. Falling back to simulation in this mode is strictly prohibited.
  3. **Deterministic Offline Simulation (Tier 3):** When operating in development, test, or offline simulation mode without explicit credential arguments, the factory strictly yields deterministic in-memory mock adapters. Even if a developer's workstation environment variables happen to contain staging or production secrets, non-production workflows default to offline mock simulation unless explicitly overridden, guaranteeing zero accidental outbound network traffic and preventing flaky test execution during network disconnects.

### 2.3 Semantic Error Classification & Telemetry Boundaries

External service integration differentiates between infrastructure outages and invalid input payloads:

1. **Upstream Infrastructure Outages (HTTP 5xx, Network Timeouts, Connect Errors):**
   Classified as service availability failures (`retryable = true`, status 503). These represent genuine remote downtime or cluster saturation. Automated exponential backoff is permitted, and telemetry feeds external dependency availability metrics and SRE alerting thresholds.
2. **Upstream Response Contract & Schema Violations (HTTP 200 with Missing Fields or Malformed JSON):**
   Classified as response payload contract errors (`retryable = true`, status 502). These occur when an external endpoint accepts the request with `200 OK` but returns a payload violating the documented schema contract (e.g., missing transcript or missing entitlement flag). Unlike request failures, the fault lies with the upstream provider; retrying against another healthy cluster node may succeed. Telemetry routes these to upstream vendor contract SLA tracking.
3. **Client & Media Request Payload Validation Rejections (HTTP 400, 415, 422):**
   Classified as request payload errors (`retryable = false`, status 400). These occur when an external endpoint rejects our request due to corrupted audio files, unsupported codecs (e.g. non-GSM sample rates), or malformed parameters. Retrying the same input is strictly forbidden as it wastes bandwidth and guarantees failure. Telemetry routes these to intake quality monitoring and triggers conversational reprompts/clarifications rather than false SRE outage alerts.
4. **Authentication Rejections (HTTP 401, 403):**
   Classified as credential errors (`retryable = false`, status 502). Indicates expired tokens or invalid API keys; fails closed immediately without mock fallback.

---

## 3. Sovereign AI Service Adapters

### 3.1 Speech & Translation Client (Bhashini ASR / NMT / TTS)
* **ASR Transcription:** Dispatches audio URLs to `/v1/asr/transcribe` with target language locale.
* **NMT Translation:** Dispatches regional vernacular text to `/v1/nmt/translate` for domain normalization.
* **TTS Synthesis:** Dispatches synthesized text to `/v1/tts/synthesize` to generate vernacular audio stream URLs.
* **Architectural Rationale:** Evaluated against commercial cloud APIs (Google Cloud, AWS), frontier models (Whisper), and self-hosted models. Selected for strict DPDP Act 2023 compliance (100% sovereign data localization), 8kHz lossy GSM telephony acoustic grounding, and high-accuracy Indic agrarian lexicon (*Khasra, Khatauni, Patta, Bigha, Kist*). See: `decisions/step3.6_speech_and_translation_evaluation.md` for the full comparative trade-off matrix.
* **Production Boundary:** Mandatory endpoint URL and API key; persistent HTTP connection pool; raises service unavailable error on network or endpoint failure.

### 3.2 Sovereign SLM Entity Extractor Client
* Dispatches sanitized, zero-PII conversational text to `/v1/extract` with structured JSON schema specifications.
* Injects structured prompt system rules requiring extraction confidence scores and standardized domain entity mappings (`district`, `crop_name`, `survey_number`).
* **Production Boundary:** Mandatory endpoint URL and API key; persistent HTTP connection pool; raises service unavailable error on model outage.

---

## 4. Authoritative DPI Registry Adapters

### 4.1 MOSIP Identity Token Verification Client
* Queries `/v1/identity/verify` with the 64-character SHA-256 HMAC identity token.
* Returns verified eligibility and identity assurance indicators.
* **Production Boundary:** Mandatory endpoint URL and API key; persistent HTTP connection pool; fails closed on outage.

### 4.2 AgriStack Cadastral Land Registry Client
* Queries `/v1/land/cadastral/verify` with HMAC citizen tokens and land record identifiers.
* Validates parcel ownership, crop sowing declaration, and seasonal entitlements.
* **Production Boundary:** Mandatory endpoint URL and API key; persistent HTTP connection pool; fails closed on outage.

### 4.3 OpenSPP Social Welfare Registry Client
* Dispatches eligibility verification requests to `/v1/social/eligibility`.
* Synchronizes entitlement statuses across social protection schemes.
* **Production Boundary:** Mandatory endpoint URL and API key; persistent HTTP connection pool; fails closed on outage.

### 4.4 NPCI / PFMS Payment Rail Client
* Dispatches asynchronous disbursement requests to `/v1/payments/disburse` with idempotent `disbursement_txn_id`.
* Returns payment initiation confirmation receipts (`DisbursementStatus = PENDING` / `SUCCESS`).
* **Production Boundary:** Mandatory endpoint URL and API key; persistent HTTP connection pool; fails closed on clearing outage.

---

## 5. Verification & Testing Matrix

1. **Live Adapter Connectivity Tests:** Validates successful HTTP request serialization, header injection, and JSON response parsing against simulated live endpoints.
2. **Production Fail-Fast Configuration Audits:** Verifies that initializing services in production mode without required endpoint URLs or API keys raises immediate configuration errors.
3. **Production Fail-Closed Outage Audits:** Verifies that when external endpoints return 5xx errors or network timeouts in production mode, services raise service unavailable exceptions and never fall back to mock data.
4. **Production Authentication Failure Audits:** Verifies that HTTP 401/403 responses raise explicit authentication exceptions rather than falling back to mock fixtures.
5. **Persistent Connection Pool Tests:** Validates that the shared HTTP client singleton is properly reused, pool limits are enforced, and clean shutdown is supported.
6. **Mock Implementation Verification:** Verifies deterministic offline simulation via dedicated mock service classes in non-production environments.
7. **Zero-PII Transport Audits:** Asserts zero cleartext identifiers in outbound HTTP request payloads and headers.
