# Step 3.1: Foundational Mock Boundaries & Offline Simulation Infrastructure

## 1. Executive Summary & Architectural Motivation

This document establishes the design architecture, data structures, and deterministic simulation rules for **Phase 3, Step 3.1: Foundational Mock Boundaries** within the AgriStack Zero-Trust DPI Orchestrator.

### The "Inside-Out" Development Rationale
Building sophisticated orchestration workflows ("Outside-In"—Connectors $\rightarrow$ Gateway API $\rightarrow$ Brain $\rightarrow$ External Services) introduces severe engineering friction:
1. **The "Dangling Wire" Anti-Pattern:** Attempting to build or test the Layer 4 Orchestrator Brain without predictable backend service targets forces developmental guesswork and schema fragility.
2. **Eliminating Network & Latency Bottlenecks:** Real AI model execution (ASR translation, SLM extraction) and national DPI registry integrations involve HTTP latency, rate limits, and network volatility. Offline mocks guarantee sub-second, 100% deterministic test execution.
3. **Shift-Left Error Enforcement:** By controlling exact mock input triggers and fixture response mappings, we can systematically stress-test adversarial prompt injection defenses, multi-attempt conversational loops, and financial rejection boundaries without triggering real-world external API failures.

---

## 2. Foundational AI Block Simulation Abstractions

The AI Services module (`src/services/ai/`) provides zero-network, local RAM simulations for multi-lingual citizen engagement and sovereign NLU processing.

### 2.1 Speech & Translation Abstraction (`BhashiniService`)
* **Module:** `src/services/ai/bhashini_service.py`
* **Fixtures:** `src/services/ai/ai_mock_fixtures.py`
* **Capabilities:**
  * **ASR (Automatic Speech Recognition):** Maps simulated audio recording URL pointers to transcribed Indic language texts (e.g., Hindi `hi-IN` and English `en-IN` baseline subsidy claims).
  * **NMT (Neural Machine Translation):** Evaluates domain keywords (`kist`, `kharab`) to produce standardized target language processing representations.
  * **TTS (Text-to-Speech):** Synthesizes response strings into formatted mock audio file pointers (`MOCK_TTS_URL_TEMPLATE`).

### 2.2 Sovereign SLM Entity Extractor (`SlmExtractor`)
* **Module:** `src/services/ai/slm_extractor.py`
* **Fixtures:** `src/services/ai/ai_mock_fixtures.py`
* **Capabilities:**
  * Uses deterministic keyword rule tables (`MOCK_SLM_RULES` & `MockExtractionRule`) to convert unstructured text into validated Pydantic models (`ExtractedEntityPayload`).
  * Simulates distinct governance confidence scores across operational scenarios:
    * **High-Confidence Subsidy Claim:** Confidence score `0.96` (triggers automated payout candidate routing).
    * **Status Query:** Confidence score `0.92` (triggers read-only registry status checks).
    * **Missing Entity Correction Loop:** Confidence score `0.65` with missing mandatory parameters (triggers multi-attempt conversational dialogue loops in Step 3.3).
  * **Security Zeroing Invariant Detection:** Scans text against `ADVERSARIAL_INJECTION_KEYWORDS` (e.g., `"ignore previous"`, `"override"`, `"system prompt"`). Flagged attempts set `is_adversarial_attempt=True`, allowing downstream security firewalls (Step 3.2) to instantly zero out AI confidence scores (`0.0`).

---

## 3. Authoritative DPI Registry Simulation Abstractions

The DPI Services module (`src/services/dpi/`) simulates cross-matching and clearing operations against national digital public infrastructures without exposing cleartext PII or touching external networks.

### 3.1 Sovereign Identity Token Verification (`IdentityVerificationService`)
* **Module:** `src/services/dpi/identity_verification_service.py`
* **Fixtures:** `src/services/dpi/dpi_mock_fixtures.py`
* **Capabilities:**
  * Validates 64-character SHA-256 HMAC tokens against simulated zero-value tokens (`UNVERIFIED_IDENTITY_TOKEN_ZERO`) and unverified prefixes (`UNVERIFIED_IDENTITY_PREFIX`).
  * Enforces the **Identity Invariant**: no cleartext phone numbers, Aadhaar IDs, or names enter registry mock lookups.

### 3.2 AgriStack Cadastral & Crop Land Registry (`AgriRegistryService`)
* **Module:** `src/services/dpi/agri_registry_service.py`
* **Fixtures:** `src/services/dpi/dpi_mock_fixtures.py` (`MockCadastralParcel` & `MOCK_CADASTRAL_REGISTRY`)
* **Capabilities:**
  * Evaluates citizen identity tokens against simulated cadastral land records (`LAND-REC-1002`, `LAND-REC-2004`, `LAND-REC-3006`).
  * Verifies parcel ownership matching (district, taluka, village, survey number) and seasonal crop entitlements.

### 3.3 OpenSPP Social Welfare Registry (`SocialRegistryService`) & Internal Case Management (`CaseManagementService`)
* **External DPI Connector Module:** `src/services/dpi/social_registry_service.py` (`SocialRegistryService`)
  * Simulates external OpenSPP registry synchronization for incident review tickets (`SPP-CASE-YYYY-XXXXXX`) and social protection scheme eligibility queries.
  * Provides deterministic failure routing on simulated rejection prefixes (`MOCK_CASE_REJECT_PREFIX`) to verify error handling pathways in Layer 4 orchestrators.
* **Internal Caseworker Domain Service:** `src/services/caseworker/case_management_service.py` (`CaseManagementService`)
  * Coordinates internal caseworker queue staging, officer adjudication review processing (`CaseworkerReviewOutcomePayload`), and citizen clarification resolution loops (`INFO_REQUESTED` $\rightarrow$ `UNDER_REVIEW`).
  * Injects `SocialRegistryService` for external OpenSPP synchronization.

### 3.4 Sovereign Payment Rails (`PaymentRailService`)
* **Module:** `src/services/dpi/payment_rail_service.py`
* **Capabilities:**
  * Simulates asynchronous wire dispatch over NPCI APBS / PFMS Treasury clearing rails.
  * Emits final status callbacks (`DisbursementCallbackPayload`) adhering strictly to monotonic forward financial state transitions (`PENDING` $\rightarrow$ `INITIATED` $\rightarrow$ `SUCCESS`/`FAILED`).
  * Triggers deterministically simulated bank clearing rejections on test failure markers (`MOCK_PAYMENT_FAIL_TRIGGER`).

---

## 4. Verification & Step 3.2 Handoff Criteria

The completion of Step 3.1 requires:
1. All unit tests under `tests/services/ai/` and `tests/services/dpi/` passing with zero external network dependencies.
2. Complete MyPy strict static type checking and Ruff formatting compliance.
3. Stable mock interfaces ready for immediate consumer integration by **Step 3.2 (Security & Ingestion Firewalls)** and **Step 3.3 (Layer 4 Orchestrator Brain)**.
