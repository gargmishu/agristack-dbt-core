# Domain Entity & Relational Data Model Design

**Framework Step:** Phase 0 · Step 0.2: Identify Entities, Tables & Table Names  
**Target Environment:** Authoritative Relational Database ([database_evaluation.md](./database_evaluation.md))  
**Related Documents:** 
- [roadmap.md](../roadmap.md)
- [flowchart.md](../design-specs/step3-guardrails/flowchart.md)
- [database_evaluation.md](./database_evaluation.md)

---

## 1. Goal

Analyze the multi-channel Zero-Trust DPI Orchestrator architecture ([flowchart.md](../design-specs/step3-guardrails/flowchart.md)) to deduce core domain entities. Apply database normalization (1-to-Many cardinality) to establish a **Entity Relational Data Model** separating telecom session lifecycle tracking, AI extraction retry loops, authoritative business governance claim outcomes, consent governance, and an immutable audit history, establishing standardized `snake_case` physical table names as the authoritative data model design for downstream DDL schema generation.

---

## 2. Architectural Analysis & Entity Deduction

In [flowchart.md](../design-specs/step3-guardrails/flowchart.md), the citizen ingestion pipeline traverses four distinct architectural layers before reaching database persistence:

* **Layer 1 (User Action & Channels):** Citizen interactions originate across heterogeneous communication channels: WhatsApp (voice notes/text), IVR telephony (voice calls), and USSD telco networks (`*147#` menu signaling).
* **Layer 2 (Gateways & Connectors):** Channel-specific webhooks and SIP connectors (Meta API, Telephony Gateways, USSD Connectors) extract raw carrier media (`.ogg`, `.wav`, or keystrokes) and normalize disparate carrier formatting into a **Unified Standardized JSON Payload** (`{type: "audio"}` or `{type: "text"}`).
* **Layer 3 (The Public Agent Intake Gateway):** Acts as the ingress firewall and validation portal. The Public Agent Intake API receives the standardized JSON payload from Layer 2, logs the initial session entry, and explicitly initiates the **Layer 4** DPI workflow.
* **Layer 4 (DPI Workflow Execution):** The orchestrator brain manages the complete decision lifecycle across four sequential phases:
  1. *AI Ingestion & Entity Extraction:* Evaluates `payload_type` from Layer 3. Audio streams are routed to Foundational AI Blocks for `speech_to_text()` transcription and NMT translation. Unstructured text is processed by a sovereign Small Language Model (SLM) via `structured_extract()` to parse domain entities (`district`, `crop_type`, `reported_anomaly`) and emit an `ai_confidence_score` (USSD menu presses bypass AI directly).
  2. *Intake Validation Gate:* Evaluates extracted intents and checks for `missing_entities`. Non-claims are routed away (e.g., grievance flow), missing entities trigger conversational correction loops (prompting the user), and valid applications proceed to registry verification.
  3. *DPI Registry Interconnect:* Runs `identity_verify()` (Aadhaar hashing), `eligibility_verify()` (KISAN cadastral check emitting `eligibility_status`), and `submit_application()` (logging the transaction case in OpenSPP).
  4. *Governance Routing Engine:* Evaluates `ai_confidence_score` and `eligibility_status` against a deterministic matrix to route traffic to Automated Payout Disbursement (>95% + eligible), Human Caseworker Review (60–94% or fuzzy ID), or Auto-Rejection (<60% or ineligible), before dispatching final confirmation receipts back via Layer 1 channels.

---

## 3. Deduced Domain Entities (The Relational Model)

To eliminate redundancy, preserve complete transactional auditability, and strictly separate AI extraction retry logs from authoritative business claims, we deduce the following relational entities:

1. **`session_telemetry_log` (Root Parent Entity)**  
   An authoritative record representing the citizen's overall communication session from initial carrier signaling ingress to connection termination. All other entities are traceable back to this root record.

2. **`session_extraction_details` (Child of `session_telemetry_log`)**  
   A granular record representing each sequential payload submission, AI extraction pass, and validation attempt occurring within that parent session loop. A single session can produce many extraction attempts (1:N).

3. **`application_governance_ledger` (Child of both `session_telemetry_log` and `session_extraction_details`)**  
   An authoritative business record capturing the claims that successfully pass the Intake Validation Gate. It holds two foreign keys: `session_id` (anchoring it to the root session for full-funnel analytics) and `payload_id` (anchoring it to the specific winning extraction attempt that drove the claim).

4. **`application_governance_ledger_history` (Audit Entity, Child of `application_governance_ledger`)**  
   An append-only historical log tracking every state change a claim undergoes. Populated automatically via PostgreSQL triggers — the application layer never writes to this table directly. Preserves the chronological lifecycle for SLA tracking and regulatory auditability.

5. **`consent_registry` (Policy / Consent Entity)**
   Stores consent records linked to a tokenized identifier. This table captures consent decisions (granted/revoked), scope, timestamp, source, consent version, expiry, and provenance metadata. Consent records must reference only tokenized IDs (never raw PII) so L3/L4 can enforce per-type policy before any registry or ledger write.

> [!IMPORTANT]
> **Declarative Foreign Key Enforcement (1:N Cardinality)**
> In accordance with our database selection rationale in [database_evaluation.md](./database_evaluation.md), the database platform must enforce all 1-to-Many relational links using declarative foreign keys (e.g., `FOREIGN KEY (session_id) REFERENCES session_telemetry_log(session_id) ON DELETE CASCADE`). This prevents orphaned extraction records or business claims if a parent session is purged or archived.

---

## 4. Physical Schema

The exact physical schema — including all column definitions, data types, ENUM values, indexes, analytics views, CHECK constraints, and architectural trade-off decisions — is documented in:

**→ [database_schema_design.md](./database_schema_design.md)**

---

## 5. Summary Verification Against Roadmap Step 0.2

| Requirement in [roadmap.md](../roadmap.md) Step 0.2 | Execution in This Design | Verification Status |
| :--- | :--- | :--- |
| Analyze `flowchart.md` to deduce domain entities | Deduced Root Parent Session, Child AI Extraction, Business Governance Ledger, and Audit History entities. | ✅ Validated |
| Apply database normalization (1-to-Many cardinality) | Established 1:N relational links via `session_id` and `payload_id` FKs to isolate retry loops from business claims. | ✅ Validated |
| Separate parent lifecycle from child transactional logs | Separated `session_telemetry_log` (ingress) from `session_extraction_details` and `application_governance_ledger`. | ✅ Validated |
| Define standardized `snake_case` table names | Configured immutable names: `session_telemetry_log`, `session_extraction_details`, `application_governance_ledger`, `application_governance_ledger_history`, and `consent_registry`. | ✅ Validated |
| Document as authoritative data model design for Step 0.4 | Conceptual entity model established here. Physical DDL details in [database_schema_design.md](./database_schema_design.md). | ✅ Validated |
