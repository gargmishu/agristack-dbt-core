# **Master Roadmap: Zero-Trust DPI Orchestrator**

**Methodology:** Inside-Out Agentic Development

## **Phase 0: The Ground Truth (Data & Security Architecture)**

* **Step 0.1: Choose the Database Infrastructure:** Evaluate and select a database provider that natively supports ACID relational integrity, declarative foreign keys, JSONB storage, automated REST API generation, and standard SQL windowing functions required for downstream analytical deduplication. Ensure the chosen database can operate within a permanent free tier while supporting millions of users in production.
* **Step 0.2: Identify Entities, Tables & Table Names:** Analyze the master architecture flowchart ([flowchart.md](./design-specs/step3-guardrails/flowchart.md)) to deduce domain entities. Apply database normalization (1-to-Many cardinality) to separate parent session lifecycle tracking (channel ingress, ANI phone numbers, connection states) from child transactional logs (sequential extraction attempts in conversational loops). Define standardized `snake_case` physical table names and document them as the immutable contract for Step 0.4.  
* **Step 0.3: Establish Zero-Trust Purge & Tokenization Protocols:** Analyze citizen data privacy mandates before schema creation. Identify where cleartext PII enters the ingress perimeter and define strict in-memory tokenization rules in volatile RAM and explicit memory purge protocols. Establish a non-negotiable rule that cleartext PII is strictly forbidden from touching persistent disk storage.  
* **Step 0.4: Design Table Schemas & Analytical Staging Rules:** Generate DDL script definitions (`schema.sql`) using the exact table names established in Step 0.2 and enforcing the zero-retention rules from Step 0.3 (physically omitting cleartext PII columns). Define SQL window partitioning queries (`QUALIFY ROW_NUMBER() OVER`) or `dbt-core` staging models to deduplicate multi-attempt user correction loops.

## **Phase 1: The Stack & Tooling Definition (The Agent's Rulebook)**

*Purpose: Explicitly define the environment boundaries, programming language, runtime, static analysis, and code quality rules to prevent syntax errors, type coercion bugs, or non-compliant code.*

* **Step 1.1: Choose Language, Runtime & AI Frameworks:** Select the core application runtime for gateways/connectors, the orchestration engine for state transitions, and local Small Language Model (SLM) frameworks for sovereign in-memory entity extraction.  
* **Step 1.2: Configure Environment Strictness & Code Quality Tools:** Configure strict code linting (Ruff), static type checking (`mypy --strict`), test framework execution (Pytest), and git pre-commit hooks ([runtime_strictness_linting.md](./decisions/runtime_strictness_linting.md)) to enforce strict code quality boundaries and environment sanity.

## **Phase 2: Modular Project Scaffolding & Domain Contracts**

*Purpose: Create the canonical data contracts and physical map of the project. The AI needs explicit domain models and folder structures anchoring each layer of the flowchart so it does not hallucinate data structures or module locations.*

* **Step 2.0: Define Canonical Domain Contracts & Standardized Schemas:** Define standardized domain enums (`src/models/enums.py`), the Pydantic v2 `StrictBaseModel` base model (`src/models/base.py`), and canonical inter-layer validation schemas ([canonical_domain_schemas.md](./decisions/canonical_domain_schemas.md)) with strict extra-field prohibition (`extra="forbid"`) to prevent malformed payload injection between system layers.
* **Step 2.1: Initialize Package Manager & Dependencies:** Generate the root dependency configuration file (`pyproject.toml`) and establish test framework runners.  
* **Step 2.2: Scaffold 4-Layer Architecture Structure:** Reference the master flowchart and generate skeleton files mapped strictly to the system layers:  
  * **Layer 1: Channel Edge Connectors** (Voice stream gateways, chat webhooks, USSD menu signaling) — e.g., IVR SIP gateway, WhatsApp webhook receiver, USSD session handler.
  * **Layer 2: API Access & Transport** (Auth, rate-limiting, schema validation, and canonicalization) — e.g., API gateway enforcing mTLS/JWT, ingress proxy with quotas, message-broker shim that validates and forwards canonical payloads to Layer 3.
  * **Layer 3: Public Agent Intake Gateway** — the API surface and intake layer that normalizes incoming events, performs intent validation, and forwards structured payloads to the brain.  
  * **Layer 4: Orchestrator Brain** (State machine and governance decision routing engines).  
  * **Service Abstractions:** Explicitly separate Foundational AI Blocks (speech-to-text, translation, text-to-speech, SLMs) from Authoritative DPI Registries (identity verification, agricultural land registries, social protection case staging, and payment rails).

  *Example Recommended Folder Tree:*  
  ```text
  project-root/
  ├── package.json
  └── src/
      ├── index.js                     <-- Module exports & entry point
      ├── intake/
      │   ├── PublicAgentIntakeApi.js  <-- (Layer 3: Public Agent Intake Gateway)
      │   └── IntakeValidator.js       <-- (Layer 3: Intent & Missing Entity Gate)
      ├── connectors/                  <-- (Layer 2: Gateways & Connectors)
      │   ├── WhatsAppConnector.js     <-- Text/Audio (.ogg) cleartext webhook
      │   ├── IvrConnector.js          <-- Voice stream (.wav) SIP gateway
      │   └── UssdConnector.js         <-- Menu signaling (*147#) bypass connector
      ├── orchestrator/                <-- (Layer 4: DPI Workflow Execution)
      │   ├── StateMachine.js          <-- Deterministic execution loop
      │   └── GovernanceRouter.js      <-- Decision matrix (Payout vs Review vs Reject)
      ├── services/                    <-- External Dependency Abstractions
      │   ├── ai/                      <-- Foundational & Sector AI Blocks
      │   │   ├── bhashiniService.js   <-- ASR, NMT Translation, and TTS blocks
      │   │   └── slmExtractor.js      <-- Local Ollama structured entity extractor
      │   └── dpi/                     <-- Authoritative DPI Registries
      │       ├── identityRegistry.js  <-- Aadhaar/MOSIP verification & hashing
      │       ├── agriRegistry.js      <-- AgriStack cadastral & crop cross-match
      │       ├── socialRegistry.js    <-- OpenSPP case lifecycle staging
      │       └── paymentRail.js       <-- NPCI APBS / Mojaloop disbursement
      └── models/                      <-- Data structures & DB layer
          └── StandardizedIntakePayload.js
  ```

  *Rationale: This exact split maps directly to the layers in the flowchart and dependency taxonomy, guaranteeing Separation of Concerns so that a bug in a WhatsApp connector won't break core governance routing or identity tokenization.*

## **Phase 3: Module / Component-Wise Implementation**

*Purpose: Build the actual logic inside the scaffolded files. Implement and test components sequentially from the inside out to avoid dangling wire dependencies and testing bottlenecks.*

* **Step 3.1: Foundational Mock Boundaries:** Build deterministic, locally testable functions returning fixed JSON responses for all external dependencies:  
  * **AI Blocks:** ASR transcription, NMT translation, TTS synthesis, and SLM structured entity extraction.  
  * **DPI Blocks:** Identity verification/tokenization, agricultural cadastral cross-matching, social benefit case staging, and automated payment clearing.  
* **Step 3.2: Security & Ingestion Firewalls:** Implement adversarial prompt injection filters and in-memory PII cleartext purge middlewares. Enforce rules that immediately set AI extraction confidence scores to `0.0` upon detecting adversarial override attempts.  
* **Step 3.3: Layer 4 Orchestrator Brain (The Three Evaluation Gates):** Implement the deterministic state machine governing workflow execution across three testable gates:  
  1. *Ingress & Structure Gate:* Audio vs. text routing; USSD structured menu bypass (hardcoding extraction confidence to `1.0`).  
  2. *Intake Validation Gate:* Evaluating extracted intents and missing entities, routing away non-claims, and triggering multi-attempt conversational correction loops when entities are missing.  
  3. *Deterministic Governance Routing Matrix:* Evaluating AI confidence scores and registry eligibility status to switch between Automated Payout ($>95\%$ + eligible), Human Caseworker Review ($60\text{--}94\%$ or fuzzy match), and Auto-Reject ($<60\%$ or ineligible).  
* **Step 3.4: Layer 3 Intake Gateway & Layer 2 Connectors:** Build the public intake API and implement channel-specific webhooks (WhatsApp, IVR voice, USSD) that normalize disparate carrier payloads into a unified, standardized JSON schema before submitting to Layer 3.  
* **Step 3.4.1: Decide API Access Layer Architecture:** Choose between a thin application-layer service and database-native endpoints, with the recommendation to prioritize a thin service for security, validation, and long-term maintainability.  
* **Step 3.5: Adaptive Multichannel Confirmation Delivery:** Implement the outbound dispatch engine that formats final transaction receipts (e.g., payment clearing numbers or caseworker escalation IDs) and transmits them natively back via the citizen's originating channel.  
* **Step 3.6: Live Service Integration:** Swap out Phase 3.1 deterministic mocks for live endpoints and sovereign cloud/local model connections.

### **Why this specific sequence? (Inside-Out vs. Outside-In)**

If we built "Outside-In" (Connectors $\rightarrow$ Gateway API $\rightarrow$ Brain $\rightarrow$ External Services), we would create massive roadblocks for the AI:

1. **The "Dangling Wire" problem:** If you ask an AI to build the WhatsApp connector first, it has no Gateway API to send the data to, so it will *hallucinate* a fake endpoint.  
2. **Testing Bottlenecks:** If you build the Brain before the Mocks, the Brain will try to call external services that don't exist yet, making it impossible to test if your core routing logic actually works until the very end of the project.

**The "Inside-Out" Strategy** solves this:

* **Mocks First (3.1 & 3.2):** We need fake, predictable data and security firewalls to test with so we aren't wasting money or fighting network timeouts.  
* **The Brain Second (3.3):** We build the core logic using those mocks. Every time the Brain calls a function, that function *already exists*.  
* **The Front Door Third (3.4 & 3.5):** Only after the brain works perfectly do we connect it to the unpredictable outside world.

## **Phase 4: Verification & End-to-End Simulation Matrix**

*Purpose: Validate the completed build against all branching paths, fallback loops, and security perimeters defined in the flowchart.*

* **Step 4.1: Channel Ingress & Convergence Simulation:** Test happy-path convergence across voice, chat, and USSD channels into the Layer 3 intake gateway.  
* **Step 4.2: Zero-Trust Tokenization & Purge Auditing:** Assert via automated memory and DB tests that cleartext PII is purged from RAM post-tokenization and never appears in database transaction logs or disk storage.  
* **Step 4.3: Governance Matrix & Conversational Loop Verification:** Execute end-to-end simulation suites verifying automated payout clearing, caseworker escalation routing, auto-rejection boundaries, and multi-attempt user correction loops.
