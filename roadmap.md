# **Master Roadmap: Zero-Trust DPI Orchestrator**

**Methodology:** Inside-Out Agentic Development

## **Phase 0: The Ground Truth (Data & Security Architecture)**

* **Step 0.1: Choose the Database Infrastructure:** Evaluate and select a database provider that natively supports ACID relational integrity, declarative foreign keys, JSONB storage, automated REST API generation, and standard SQL windowing functions required for downstream analytical deduplication. Ensure the chosen database can operate within a permanent free tier while supporting millions of users in production.
* **Step 0.2: Identify Entities, Tables & Table Names:** Derive the conceptual entities from approved business and persistence requirements. Apply database normalization (1-to-Many cardinality) to separate session lifecycle tracking from child extraction attempts and governance claims. Define the conceptual entity names and relationships before physical schema design.
* **Step 0.3: Establish Zero-Trust Purge & Tokenization Protocols:** Analyze citizen data privacy mandates before schema creation. Identify where cleartext PII enters the ingress perimeter and define strict in-memory tokenization rules in volatile RAM and explicit memory purge protocols. Establish a non-negotiable rule that cleartext PII is strictly forbidden from touching persistent disk storage.
* **Step 0.4: Design Table Schemas & Analytical Staging Rules:** Generate DDL script definitions (`schema.sql`) using the exact table names established in Step 0.2 and enforcing the zero-retention rules from Step 0.3 (physically omitting cleartext PII columns). Define SQL window partitioning queries (`QUALIFY ROW_NUMBER() OVER`) or `dbt-core` staging models to deduplicate multi-attempt user correction loops.

## **Phase 1: The Stack & Tooling Definition (The Agent's Rulebook)**

*Purpose: Explicitly define the environment boundaries, programming language, runtime, static analysis, and code quality rules to prevent syntax errors, type coercion bugs, or non-compliant code.*

* **Step 1.1: Choose Language, Runtime & AI Frameworks:** Select the core application runtime for gateways/connectors, the orchestration engine for state transitions, and local Small Language Model (SLM) frameworks for sovereign in-memory entity extraction.
* **Step 1.2: Enforce Code Quality & Environment Strictness:** Evaluate, select, and configure code linting, static type checking, test framework execution, and git pre-commit hooks to enforce strict code quality boundaries and environment sanity.

## **Phase 2: Modular Project Scaffolding & Domain Contracts**

*Purpose: Create the canonical data contracts and physical map of the project. The AI needs explicit domain models and folder structures anchoring each layer of the flowchart so it does not hallucinate data structures or module locations.*

* **Step 2.0: Define Canonical Domain Contracts & Standardized Schemas:** Define standardized domain enums, base validation models, and canonical inter-layer payload validation schemas using a Shift-Left Contract Truth Table methodology (mapping field constraints, non-empty text guards, state-matrix rules, and foreign key survival tracking before code generation) to prevent logical errors right from the outset across all system layers.
* **Step 2.1: Initialize Package Manager & Install All Dependencies (including Database Drivers & Local DB):** Generate the root dependency configuration file (`pyproject.toml`), declare and install all application dependencies (FastAPI, Pydantic v2, Uvicorn), database client drivers/libraries (e.g., PostgreSQL `asyncpg`/`psycopg`, ORM/query builder), set up the local database server/container environment, and establish static analysis and test framework runners (`pytest`, `mypy`, `ruff`).
* **Step 2.2: Scaffold 4-Layer Architecture Structure:** Reference the master flowchart and generate skeleton files mapped strictly to the system layers:
  * **Layer 1: Channel Edge Connectors** (Voice stream gateways, chat webhooks, USSD menu signaling) — e.g., IVR SIP gateway, WhatsApp webhook receiver, USSD session handler.
  * **Layer 2: API Access & Transport** (Auth, rate-limiting, schema validation, and canonicalization) — e.g., API gateway enforcing mTLS/JWT, ingress proxy with quotas, message-broker shim that validates and forwards canonical payloads to Layer 3.
  * **Layer 3: Public Agent Intake Gateway** — the API surface and intake layer that normalizes incoming events, performs intent validation, and forwards structured payloads to the brain.
  * **Layer 4: Orchestrator Brain** (State machine and governance decision routing engines).
  * **Service Abstractions:** Explicitly separate Foundational AI Blocks (speech-to-text, translation, text-to-speech, SLMs) from Authoritative DPI Registries (identity verification, agricultural land registries, social protection case staging, and payment rails).

  *Conceptual Subsystem Architecture:*

  | System Layer | Subsystem / Package | Architectural Responsibility |
  | :--- | :--- | :--- |
  | **Layer 1** | *Channel Edge Connectors* | Ingress protocol adapters for WhatsApp, IVR Voice, USSD, and SMS. |
  | **Layer 2** | *Perimeter Security Gateway* | Ingress signature authentication, token-bucket rate limiting, RAM-only HMAC tokenization, PII purge sentinel, prompt firewall, and canonicalization. |
  | **Layer 3** | *Public Agent Gateway* | Public agent intake API, speech transcription, USSD bypass, and SLM domain entity extraction. |
  | **Layer 4** | *Orchestration Brain* | 3-gate claim orchestration engine, tri-state policy adjudicator, and caseworker management. |
  | **Services** | *Sovereign AI Abstractions* | Bhashini Speech-to-Text (ASR), Machine Translation (NMT), Speech Synthesis (TTS), and Sovereign SLM Entity Extractor. |
  | **Services** | *Outbound Notification Engine* | Adaptive multi-channel template rendering, text-to-speech audio formatting, and egress dispatch. |
  | **Services** | *Authoritative DPI Registries* | MOSIP identity verification, AgriStack land record cross-matching, OpenSPP social case staging, and NPCI/PFMS payment rails. |
  | **Contracts**| *Domain Data Contracts* | Immutable, validated Pydantic schemas enforcing Zero-Trust invariants across all layers. |

  *Rationale: This exact split maps directly to the layers in the flowchart and dependency taxonomy, guaranteeing Separation of Concerns so that a bug in a WhatsApp connector won't break core governance routing or identity tokenization.*

## **Phase 3: Module / Component-Wise Implementation**

*Purpose: Build the actual logic inside the scaffolded files. Implement and test components sequentially from the inside out to avoid dangling wire dependencies and testing bottlenecks.*

* **Step 3.1: Foundational Mock Boundaries:** Build deterministic, locally testable functions returning fixed JSON responses for all external dependencies:
  * **AI Blocks:** ASR transcription, NMT translation, TTS synthesis, and SLM structured entity extraction.
  * **DPI Blocks:** Identity verification/tokenization, agricultural cadastral cross-matching, social benefit case staging, and automated payment clearing.
* **Step 3.2: Security & Ingestion Firewalls:** Implement adversarial prompt injection filters and in-memory PII cleartext purge middlewares. Enforce rules that immediately set AI extraction confidence scores to `0.0` upon detecting adversarial override attempts.
* **Step 3.3: Layer 4 Orchestrator Brain:** Implement the deterministic governance workflow over the extracted domain entity contract: intent and completeness validation with bounded clarification loops, followed by policy adjudication and approve/review/reject routing. The canonical confidence threshold and state transitions are owned by the governance decisions.
* **Step 3.4: Layer 3 Intake Gateway & Layer 2 Connectors:** Build the public intake API and implement channel-specific (WhatsApp, IVR voice, USSD) ingress adapters hat produce the standardized intake contract and extracted domain entity contract consumed by Layer 4.
* **Step 3.5: Adaptive Multichannel Confirmation Delivery:** Implement the outbound dispatch engine that formats final transaction receipts (e.g., payment clearing numbers or caseworker escalation IDs) and transmits them natively back via the citizen's originating channel.
* **Step 3.6: Live Service Integration:** Swap out Phase 3.1 deterministic mocks for live endpoints and sovereign cloud/local model connections.

### **Why this specific sequence? (Inside-Out vs. Outside-In)**

If we built "Outside-In" (Connectors => Gateway API => Brain => External Services), we would create massive roadblocks for the AI:

1. **The "Dangling Wire" problem:** If you ask an AI to build the WhatsApp connector first, it has no Gateway API to send the data to, so it will *hallucinate* a fake endpoint.
2. **Testing Bottlenecks:** If you build the Brain before the Mocks, the Brain will try to call external services that don't exist yet, making it impossible to test if your core routing logic actually works until the very end of the project.

**The "Inside-Out" Strategy** solves this:

* **Mocks First (3.1 & 3.2):** We need fake, predictable data and security firewalls to test with so we aren't wasting money or fighting network timeouts.
* **The Brain Second (3.3):** We build the core logic using those mocks. Every time the Brain calls a function, that function *already exists*.
* **The Front Door Third (3.4 & 3.5):** Only after the brain works perfectly do we connect it to the unpredictable outside world.

## **Phase 4: Verification & End-to-End Simulation Matrix**

*Purpose: Validate the completed build against all branching paths, fallback loops, outbound channels, and security perimeters defined in the flowchart.*

* **Step 4.1: Multichannel Ingress & Modality Convergence:** Test happy-path convergence across all four ingress channels (Voice/IVR, WhatsApp, USSD, and SMS) into the Layer 3 Public Agent intake gateway across audio and text modalities.
* **Step 4.2: Security Firewall & Zero-Trust PII Auditing:** Execute automated security test suites to verify:
  * Carrier authentication (HMAC/Bearer) and rate-limiting quota enforcement.
  * Adversarial prompt injection defense (asserting AI extraction confidence is neutralized to `0.0`).
  * In-memory RAM zero-PII purge and automated assertions verifying no cleartext PII touches disk or database transaction logs.
* **Step 4.3: Three-Gate Governance & Conversational Loop Verification:** Execute end-to-end simulation suites verifying:
  * Ingress & Structure Gate (audio routing vs. USSD bypass).
  * Intake Validation Gate (missing entity detection and multi-attempt correction loops capped at 3 attempts).
  * Deterministic Governance Routing Matrix (Automated Payout [$\ge 0.85$] vs. Caseworker Review [$< 0.85$] vs. Auto-Rejection).
* **Step 4.4: Outbound Confirmation & Financial Callback Verification:** Validate native outbound receipt delivery back through the originating channel (WhatsApp, SMS, IVR TTS, USSD) and verify asynchronous payment clearing callbacks (NPCI APBS / PFMS Treasury).
* **Step 4.5: Database Persistence & Analytical Deduplication:** Verify relational database persistence against `schema.sql` and test analytical deduplication queries (`QUALIFY ROW_NUMBER() OVER`) on multi-attempt conversational logs.
