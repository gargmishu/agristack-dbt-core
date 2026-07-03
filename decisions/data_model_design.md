# Domain Entity & Relational Data Model Design

**Framework Step:** Phase 0 · Step 0.2: Identify Entities, Tables & Table Names  
**Target Environment:** Authoritative Relational Database ([database_evaluation.md](./database_evaluation.md))  
**Related Documents:** 
- [roadmap.md](../roadmap.md)
- [flowchart.md](../design-specs/step3-guardrails/flowchart.md)
- [database_evaluation.md](./database_evaluation.md)

---

## 1. Goal

Analyze the multi-channel Zero-Trust DPI Orchestrator architecture ([flowchart.md](../design-specs/step3-guardrails/flowchart.md)) to deduce core domain entities. Apply database normalization (1-to-Many cardinality) to establish a **3-Entity Relational Data Model** separating telecom session lifecycle tracking, AI extraction retry loops, and authoritative business governance claim outcomes, establishing standardized `snake_case` physical table names as an authoritative data model design for downstream DDL schema generation.

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
  4. *Governance Routing Engine:* Evaluates `ai_confidence_score` and `eligibility_status` against a deterministic matrix to route traffic to Automated Payout Disbursement ($>95\%$ + eligible), Human Caseworker Review ($60\text{--}94\%$ or fuzzy ID), or Auto-Rejection ($<60\%$ or ineligible), before dispatching final confirmation receipts back via Layer 1 channels.

### Deduced Domain Entities (The 3-Table Relational Model)
To eliminate redundancy, preserve complete transactional auditability, and strictly separate AI extraction retry logs from authoritative business claims, we deduce three distinct relational entities:
1. **Parent Entity (Session Lifecycle Tracking):** An authoritative record representing the citizen's overall communication session from initial carrier signaling ingress to connection termination.
2. **Child Entity 1 (AI Extraction Retry Logs):** A granular record representing each sequential payload submission, AI extraction pass, and validation attempt occurring within that parent session loop.
3. **Child Entity 2 (Business & Governance Ledger):** An authoritative business record capturing the claims that successfully pass the Intake Validation Gate, recording OpenSPP case IDs, KISAN eligibility results, governance routing decisions, and disbursement/escalation transaction IDs.

---

## 3. Standardized Table Names & Attribute Design

> [!IMPORTANT]
> **Declarative Foreign Key Enforcement (1:N Cardinality)**
> In accordance with our database selection rationale in [database_evaluation.md](./database_evaluation.md), the database platform must enforce all 1-to-Many relational links using declarative foreign keys (e.g., `FOREIGN KEY (session_id) REFERENCES session_telemetry_log(session_id) ON DELETE CASCADE`). This prevents orphaned extraction records or business claims if a parent session is purged or archived.

The following `snake_case` table names and core attributes serve as the authoritative data model design for Step 0.4 schema DDL generation:

### Table 1: `session_telemetry_log` (Parent Entity)
Tracks carrier ingress boundaries, ANI identification, and session state transitions.

| Attribute Name | Data Type / Format | Primary / Foreign Key | Description & Architectural Mapping |
| :--- | :--- | :--- | :--- |
| `session_id` | `UUID` | **Primary Key (PK)** | Unique tracking identifier generated instantly upon network entry (Step 1 Initiation). |
| `tokenized_phone_hash` | `VARCHAR(64)` | — | SHA-256 hash of the ingested telecom ANI phone identifier, used to group carrier traffic analytically without storing PII on disk. |
| `ingress_channel` | `VARCHAR(20)` | — | The inbound channel pathway chosen by the citizen (`WHATSAPP`, `IVR_VOICE`, `USSD`). |
| `session_active` | `BOOLEAN` | — | `TRUE` if the session is actively processing or awaiting citizen correction inputs. |
| `session_status` | `VARCHAR(30)` | — | State machine termination flag (`ACTIVE`, `COMPLETED_SUCCESSFULLY`, `FAILED_GATEWAY_TIMEOUT`, `USER_HANGUP`, `ABORTED_INCOMPLETE`, `ROUTED_AWAY_GRIEVANCE`). |
| `created_at` | `TIMESTAMP` | — | Timestamp when the incoming SIP INVITE or webhook payload first registered. |
| `completed_at` | `TIMESTAMP` (Nullable) | — | Timestamp when the communication session permanently terminated. |

---

### Table 2: `session_extraction_details` (Child Entity 1: AI Retry Logs)
Tracks sequential payload processing, SLM entity parsing, and conversational retry loops.

| Attribute Name | Data Type / Format | Primary / Foreign Key | Description & Architectural Mapping |
| :--- | :--- | :--- | :--- |
| `payload_id` | `UUID` | **Primary Key (PK)** | Unique token tracking the specific network text packet or raw audio chunk received. |
| `session_id` | `UUID` | **Foreign Key (FK)** | Relational link anchoring this transaction directly back to `session_telemetry_log.session_id`. |
| `attempt_id` | `INTEGER` | — | Sequential loop counter ($1, 2, \dots, N$) tracking retry submissions within this session. |
| `raw_unstructured_text` | `TEXT` | — | Ingested text string from speech-to-text transcription or native WhatsApp webhook text. |
| `standardized_english_text` | `TEXT` (Nullable) | — | Normalized English translation generated downstream by the NMT translation layer. |
| `extraction_confidence` | `DECIMAL(4,3)` | — | Mathematical AI confidence score ($0.000 \text{ to } 1.000$) evaluating structured parsing precision. |
| `extracted_district` | `VARCHAR(100)` (Nullable) | — | Extracted regional administrative geographical zone boundary entity. |
| `extracted_crop_type` | `VARCHAR(100)` (Nullable) | — | Normalized agricultural crop matching foundational core data registry categories. |
| `extracted_reported_anomaly` | `VARCHAR(200)` (Nullable) | — | Extracted damage classification or pest vector reported by the citizen. |
| `processing_state` | `VARCHAR(20)` | — | Operational tracking flag (`STAGED`, `SUPERSEDED`, `COMMITTED`) identifying active retry rows. |

---

### Table 3: `application_governance_ledger` (Child Entity 2: Business Claim Outcomes)
Tracks authoritative business claim filings, registry eligibility checks, governance routing decisions, and financial clearing receipts.

| Attribute Name | Data Type / Format | Primary / Foreign Key | Description & Architectural Mapping |
| :--- | :--- | :--- | :--- |
| `claim_id` | `UUID` | **Primary Key (PK)** | Unique authoritative business record token generated only when an application payload successfully passes the Intake Validation Gate with all required entities present. |
| `session_id` | `UUID` | **Foreign Key (FK)** | Relational link back to `session_telemetry_log.session_id` (`ON DELETE CASCADE`). |
| `payload_id` | `UUID` | **Foreign Key (FK)** | Relational link back to the winning/committed attempt in `session_extraction_details.payload_id`. |
| `tokenized_identity_hash` | `VARCHAR(64)` | — | The SHA-256 hex digest of the citizen's identity number, generated in-memory. |
| `application_status` | `VARCHAR(30)` | — | Authoritative business claim lifecycle status (`FILED`, `APPROVED`, `REJECTED`, `UNDER_REVIEW`, `APPEALED`, `CLOSED`). |
| `openspp_case_id` | `VARCHAR(50)` (Nullable) | — | Social protection case tracking number generated when logging the claim in OpenSPP via `submit_application()`. |
| `eligibility_status` | `VARCHAR(30)` | — | Outcome of `eligibility_verify()` against KISAN cadastral records (`ELIGIBLE`, `INELIGIBLE`, `FUZZY_MATCH`). |
| `governance_decision` | `VARCHAR(30)` | — | Deterministic routing engine decision (`AUTOMATED_PAYOUT`, `CASEWORKER_REVIEW`, `AUTO_REJECTED`). |
| `rejection_reason` | `VARCHAR(255)` (Nullable) | — | Explicit explanation for denial (e.g., "KISAN Cadastral crop mismatch" or "AI extraction confidence < 60%"). |
| `approval_amount` | `DECIMAL(10,2)` (Nullable) | — | Monetary subsidy or payout amount approved for disbursement (e.g., `6000.00` INR). |
| `disbursement_transaction_id` | `VARCHAR(100)` (Nullable) | — | Financial clearing receipt (PFMS/APBS payment ID) or caseworker incident tracking ticket. |
| `caseworker_notes` | `TEXT` (Nullable) | — | Manual review notes, investigation findings, or incident logs added by a human casework officer during escalation. |
| `decided_at` | `TIMESTAMP` | — | Timestamp when the governance matrix evaluated the claim and dispatched notifications. |

> [!NOTE]
> **Identity Tokenization Placeholder**
> Attributes handling citizen PII verification and cryptographic hashing (e.g., `tokenized_identity_hash`) will be defined in **Step 0.3: Establish Zero-Trust Purge & Tokenization Protocols** and incorporated into this data model design prior to DDL script generation in Step 0.4.

---

## 4. Summary Verification Against Roadmap Step 0.2

| Requirement in [roadmap.md](../roadmap.md) Step 0.2 | Execution in This Design | Verification Status |
| :--- | :--- | :--- |
| Analyze `flowchart.md` to deduce domain entities | Deduced Parent Session Lifecycle, Child AI Extraction, and Business Governance Ledger entities. | ✅ Validated |
| Apply database normalization (1-to-Many cardinality) | Established 1:N relational links via `session_id` and `payload_id` FKs to isolate retry loops from business claims. | ✅ Validated |
| Separate parent lifecycle from child transactional logs | Separated `session_telemetry_log` (ingress) from `session_extraction_details` and `application_governance_ledger`. | ✅ Validated |
| Define standardized `snake_case` table names | Configured immutable names: `session_telemetry_log`, `session_extraction_details`, and `application_governance_ledger`. | ✅ Validated |
| Document as authoritative data model design for Step 0.4 | Established attribute tables, types, and FK constraints as architectural design for DDL scripts. | ✅ Validated |
