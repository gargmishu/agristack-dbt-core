# Domain Entity & Relational Data Model Design

**Framework Step:** Phase 0 · Step 0.2: Identify Entities, Tables & Table Names
**Target Environment:** Authoritative Relational Database
**Related Documents:**
- [roadmap.md](../roadmap.md)
- [step0.0_master_project_and_business_requirements.md](./step0.0_master_project_and_business_requirements.md)
- [step0.1_database_evaluation.md](./step0.1_database_evaluation.md)
- The Phase 0 security requirements.

---

## 1. Goal

Analyze the multi-channel Zero-Trust DPI Orchestrator architecture to deduce core domain entities. Apply database normalization (1-to-Many cardinality) to establish an **Entity Relational Data Model** separating telecom session lifecycle tracking, AI extraction retry loops, authoritative business governance claim outcomes, consent governance, and an immutable audit history, establishing standardized `snake_case` physical table names as the authoritative data model design for downstream DDL schema generation.

---

## 2. Architectural Analysis & Entity Deduction

The citizen ingestion pipeline traverses four distinct architectural layers before reaching database persistence:

* **Layer 1 (User Action & Channels):** Citizen interactions originate across heterogeneous communication channels: WhatsApp (voice notes/text), IVR telephony (voice calls), and USSD telco networks (`*147#` menu signaling).
* **Layer 2 (Gateways & Connectors):** Channel-specific webhooks and SIP connectors (Meta API, Telephony Gateways, USSD Connectors) extract raw carrier media (`.ogg`, `.wav`, or keystrokes) and normalize disparate carrier formatting into a **Unified Standardized JSON Payload** (`{type: "audio"}` or `{type: "text"}`).
* **Layer 3 (The Public Agent Intake Gateway):** Acts as the ingress firewall and validation portal. The Public Agent Intake API receives the standardized JSON payload from Layer 2, logs the initial session entry, and explicitly initiates the **Layer 4** DPI workflow.
* **Layer 4 (DPI Workflow Execution):** The orchestrator brain manages the complete decision lifecycle across four sequential phases:
  1. *AI Ingestion & Entity Extraction:* Evaluates `payload_type` from Layer 3. Audio streams are routed to Foundational AI Blocks for speech-to-text transcription and NMT translation. Unstructured text is processed by a sovereign Small Language Model (SLM) via structured entity extraction to parse domain entities (`district`, `crop_type`, `reported_anomaly`) and emit an `ai_confidence_score` (USSD menu presses bypass AI directly).
  2. *Intake Validation Gate:* Evaluates extracted intents and checks for missing domain entities. Non-claims are routed away (e.g., grievance flow), missing entities trigger conversational correction loops (prompting the user), and valid applications proceed to registry verification.
  3. *DPI Registry Interconnect:* Performs sovereign identity verification using an authorized identity-verification flow, cadastral entitlement checks (emitting `eligibility_status`), and application staging in the designated case-management registry.
  4. *Governance Routing Engine:* Evaluates `ai_confidence_score` and `eligibility_status` against a deterministic matrix to route traffic to Automated Payout Disbursement ($\text{Score} \ge 0.85$ + eligible), Human Caseworker Review ($\text{Score} < 0.85$ or anomaly), or Auto-Rejection (ineligible or duplicate), before dispatching final confirmation receipts back via Layer 1 channels.

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
> In accordance with the database selection rationale in [step0.1_database_evaluation.md](./step0.1_database_evaluation.md), the database platform must enforce all 1-to-Many relational links using declarative foreign keys (e.g., `FOREIGN KEY (session_id) REFERENCES session_telemetry_log(session_id) ON DELETE CASCADE`). This prevents orphaned extraction records or business claims if a parent session is purged or archived.

---

## 4. Physical Schema

The exact physical schema—including column definitions, data types, enumerations, indexes, analytics views, and constraints—is derived from this conceptual model during the separate schema-design work.

---

## 5. Summary Verification Against Phase 0 Step 0.2

| Requirement | Execution in This Design | Verification Status |
| :--- | :--- | :--- |
| Analyze the intake flow to deduce domain entities | Deduced Root Parent Session, Child AI Extraction, Business Governance Ledger, and Audit History entities. | ✅ Validated |
| Apply database normalization (1-to-Many cardinality) | Established 1:N relational links via `session_id` and `payload_id` FKs to isolate retry loops from business claims. | ✅ Validated |
| Separate parent lifecycle from child transactional logs | Separated `session_telemetry_log` (ingress) from `session_extraction_details` and `application_governance_ledger`. | ✅ Validated |
| Define standardized `snake_case` table names | Configured immutable names: `session_telemetry_log`, `session_extraction_details`, `application_governance_ledger`, `application_governance_ledger_history`, and `consent_registry`. | ✅ Validated |
| Document as authoritative conceptual model | Entity names and relationships established here; physical database definitions derive from this model. | ✅ Validated |
