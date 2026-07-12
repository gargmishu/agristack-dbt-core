# Schema Architecture Decisions Log

**Context:** This document outlines the architectural decisions, rationale, and considered alternatives for the schema design in the Agristack DBT Core project.

---

## 1. Tables Overview

To eliminate redundancy and separate session telemetry from business outcomes, the schema is normalized into three authoritative tables:

1. **`session_telemetry_log` (Parent Entity):** Tracks the overall citizen communication session from ingress to termination.
2. **`session_extraction_details` (Child of `session_telemetry_log`):** Tracks granular retry loops, NLP text extractions, and AI confidence scores for every payload submitted during a session.
3. **`application_governance_ledger` (Child of `session_extraction_details` & `session_telemetry_log`):** Tracks the final business claim, eligibility status, routing decision, and financial payout lifecycle once an extraction is successfully committed.
4. **`application_governance_ledger_history` (Audit Entity):** An append-only historical log tracking every state change a claim undergoes, preserving the chronological lifecycle for SLA tracking.

---

## 2. Table designs

### 2.1 Columns Needed & Data Types

#### `session_telemetry_log`
| Column | Data Type | Rationale / Constraint |
| :--- | :--- | :--- |
| `session_id` | `UUID` | Primary Key. UUID chosen to prevent sequence enumeration and support distributed ingestion. |
| `tokenized_phone_hash` | `VARCHAR(64)` | Stores SHA-256 hash to satisfy Zero-PII requirements on disk. |
| `ingress_channel` | `ingress_channel_type` | Native Postgres `ENUM` (`WHATSAPP`, `IVR_VOICE`, `USSD`). |
| `session_status` | `session_status_enum` | Native Postgres `ENUM` (`ACTIVE`, `PENDING`, `COMPLETED`, `ABANDONED`, `TIMEOUT`) for strict state transition enforcement. |
| `session_active` | `BOOLEAN` | Generated column based on `session_status = 'ACTIVE'`. |
| `created_at` | `TIMESTAMPTZ` | Standard timezone-aware timestamp for session start. |
| `completed_at` | `TIMESTAMPTZ` | Standard timezone-aware timestamp for session termination. |

#### `session_extraction_details`
| Column | Data Type | Rationale / Constraint |
| :--- | :--- | :--- |
| `payload_id` | `UUID` | Primary Key. |
| `session_id` | `UUID` | Foreign Key referencing `session_telemetry_log` with `ON DELETE CASCADE`. |
| `attempt_id` | `INTEGER` | Tracks retry sequence number (`CHECK (attempt_id > 0)`). |
| `raw_unstructured_text` | `TEXT` | Original text input received from the user. |
| `standardized_english_text` | `TEXT` | NMT-translated and standardized English text for processing. |
| `extraction_confidence` | `DECIMAL(4, 3)` | Precision decimal constrained between `0.000` and `1.000`. |
| `extracted_district` | `VARCHAR(100)` | Bounded string capturing NER model output for the district. |
| `crop_type` | `VARCHAR(100)` | Bounded string capturing NER model output for the crop. |
| `anomaly` | `VARCHAR(200)` | Bounded string capturing identified anomalies. |
| `processing_state` | `processing_state_enum` | Native Postgres `ENUM` (`STAGED`, `SUPERSEDED`, `COMMITTED`) to handle overwrites. |

#### `application_governance_ledger`
| Column | Data Type | Rationale / Constraint |
| :--- | :--- | :--- |
| `claim_id` | `UUID` | Primary Key representing a formally filed claim. |
| `session_id` | `UUID` | Foreign Key anchoring the claim back to the parent telemetry log. |
| `payload_id` | `UUID` | Foreign Key anchoring the claim back to the specific extraction attempt. |
| `tokenized_identity_hash` | `VARCHAR(64)` | SHA-256 hash of the National ID / Identity. |
| `application_status` | `application_status_enum` | Native Postgres `ENUM` (`DRAFT`, `SUBMITTED`, `UNDER_REVIEW`, `FINALIZED`, `REJECTED`, `APPEALED`). |
| `claimant_eligibility_status`| `eligibility_status_enum` | Native Postgres `ENUM` (`PENDING_VERIFICATION`, `ELIGIBLE`, `INELIGIBLE`). |
| `governance_decision` | `governance_decision_enum` | Native Postgres `ENUM` (`AUTO_APPROVE`, `AUTO_REJECT`, `ROUTE_FOR_MANUAL_REVIEW`, `REQUEST_MORE_INFO`). |
| `decided_at` | `TIMESTAMPTZ` | Standard timezone-aware timestamp capturing the exact moment the governance decision was executed. |
| `disbursement_status` | `disbursement_status_enum` | Native Postgres `ENUM` (`PENDING`, `INITIATED`, `SUCCESS`, `FAILED`, `RETURNED`) tracking the financial clearing state. |
| `governance_metadata` | `JSONB` | Flexible payload for sparse edge-case data (rejection reasons, notes). |

#### `application_governance_ledger_history`
| Column | Data Type | Rationale / Constraint |
| :--- | :--- | :--- |
| `history_id` | `UUID` | Primary Key. |
| `claim_id` | `UUID` | Foreign Key referencing `application_governance_ledger` (`ON DELETE CASCADE`). |
| `previous_application_status` | `application_status_enum` | The state of the claim *before* the update. **Constraint:** Must allow `NULL` (required for the initial `DRAFT` insert). |
| `new_application_status` | `application_status_enum` | The state of the claim *after* the update. |
| `governance_decision` | `governance_decision_enum` | The action that triggered this state change. |
| `actor_id` | `VARCHAR(100)` | The entity responsible for the change (`SYSTEM:v1.2` or the human agent's UUID). |
| `changed_at` | `TIMESTAMPTZ` | Standard timezone-aware timestamp of the exact moment the transition occurred. |


### 2.2. Enum Value Definitions Reference

To ensure strict data integrity and predictable routing, the following native Postgres `ENUM` types have been defined with these exact possible values:

#### Telemetry & Extraction Enums
*   **`ingress_channel_type`**: `WHATSAPP`, `IVR_VOICE`, `USSD`
*   **`session_status_enum`**: `ACTIVE`, `PENDING`, `COMPLETED`, `ABANDONED`, `TIMEOUT`
*   **`processing_state_enum`**: 
    *   `STAGED` (Initial NLP extraction pending confirmation)
    *   `SUPERSEDED` (User corrected the AI; old payload is archived)
    *   `COMMITTED` (Final accepted extraction used for the claim)

#### Governance & Ledger Enums
*   **`application_status_enum`**: `DRAFT`, `SUBMITTED`, `UNDER_REVIEW`, `FINALIZED`, `REJECTED`, `APPEALED`
*   **`eligibility_status_enum`**: `PENDING_VERIFICATION`, `ELIGIBLE`, `INELIGIBLE`
*   **`governance_decision_enum`**: `AUTO_APPROVE`, `AUTO_REJECT`, `ROUTE_FOR_MANUAL_REVIEW`, `REQUEST_MORE_INFO`, `MANUAL_APPROVE`, `MANUAL_REJECT`
*   **`disbursement_status_enum`**: `PENDING`, `INITIATED`, `SUCCESS`, `FAILED`, `RETURNED`

### 2.3 Governance Metadata JSONB Schema

While `governance_metadata` is a flexible `JSONB` column, we enforce strict payload expectations, both at the application layer and at the database layer using Postgres `CHECK` constraints based on the specific `governance_decision`. To guarantee a 100% strict audit trail, every terminal decision (approval or rejection) must log an actor and a rationale. For automated decisions, `reviewer_id` must be populated with the system identifier (e.g., `SYSTEM:v1.2.0`).

| Target Key | Data Type | Status/Decision Trigger | Requirement Level | Purpose & Architectural Context |
| :--- | :--- | :--- | :--- | :--- |
| `rejection_reason` | `string` | `AUTO_REJECT` <br> `MANUAL_REJECT` | **Required (If Rejected)** | Captures the specific policy/ML flag or human justification that caused rejection. |
| `approval_amount` | `number` | `AUTO_APPROVE` <br> `MANUAL_APPROVE` | **Required (If Approved)** | Calculated financial payload for the citizen, triggering disbursement. |
| `reviewer_id` | `string` | `AUTO_APPROVE` / `AUTO_REJECT` <br> `MANUAL_APPROVE` / `MANUAL_REJECT` <br> `ROUTE_FOR_MANUAL_REVIEW` | **Required (If Approved/Rejected)** <br> *(Optional if Routing)* | Guarantees an audit trail for every final decision. Uses Human UUID (for manual) or `SYSTEM:{version}` (for auto). |
| `review_notes` | `string` | `AUTO_APPROVE` / `AUTO_REJECT` <br> `MANUAL_APPROVE` / `MANUAL_REJECT` <br> `ROUTE_FOR_MANUAL_REVIEW` | **Required (If Approved/Rejected)** <br> *(Optional if Routing)* | Mandatory justification for the decision. Free-text for humans, or structured rules-engine output for `SYSTEM`. |
| `missing_info_fields` | `array[string]` | `REQUEST_MORE_INFO` | Recommended | Fields citizen must provide (e.g., `["bank_ifsc"]`). |
| `fraud_flag_code` | `string` | `AUTO_REJECT` <br> `MANUAL_REJECT` | **Required (If Rejection is Fraud)** | Required *only* if the `rejection_reason` indicates a security violation (e.g., 'SUSPECTED_FRAUD'). Ensures the backend provides the specific investigative code (e.g., 'SPOOFED_GPS'). |
| `disbursement_txn_id`| `string` | *Disbursement Init.* | **Required (If Disbursed)** | Payment gateway transaction ID. |

### 2.4. State Machine Mapping: Application Status vs. Governance Decision

**Note on State Relationship:** `application_status` and `governance_decision` work in tandem but serve different purposes. `application_status` tracks *where* the claim is in its lifecycle, while `governance_decision` tracks *what action* was taken to move it there. 

#### Bidirectional Flow Mapping

| `application_status_enum` | Associated `governance_decision_enum` | Lifecycle Rationale & State Transition |
| :--- | :--- | :--- |
| **`DRAFT`** | `REQUEST_MORE_INFO` <br>*(or N/A)* | **System/Reviewer Action:** A decision of `REQUEST_MORE_INFO` halts processing and typically kicks the application back to `DRAFT` so the citizen can provide missing details. (Note: Initial drafts are user-created, requiring no backend decision). |
| **`SUBMITTED`** | *None (Pending)* | **User Action:** This state is triggered by the citizen submitting the payload. It acts as a holding queue awaiting the *next* `governance_decision`. |
| **`UNDER_REVIEW`** | `ROUTE_FOR_MANUAL_REVIEW` | **System Action:** The rules engine could not confidently auto-approve or auto-reject, issuing a `ROUTE_FOR_MANUAL_REVIEW` decision to transition the claim to the human review queue. |
| **`FINALIZED`** | `AUTO_APPROVE` <br> `MANUAL_APPROVE` | **System/Human Action:** The rules engine or human reviewer validated all criteria successfully, issued an `AUTO_APPROVE` or `MANUAL_APPROVE` decision, finalizing the application toward disbursement. |
| **`REJECTED`** | `AUTO_REJECT` <br> `MANUAL_REJECT` | **System/Human Action:** The system or human detected fraud, anomalies, or strict ineligibility, closing the application loop. |
| **`APPEALED`** | *None (Pending)* | **User Action:** Triggered by the citizen contesting a `REJECTED` status. Awaiting a new `governance_decision`. |

#### System Decision Impact Summary
* **`AUTO_APPROVE` / `MANUAL_APPROVE`** ➔ Transitions the application to **`FINALIZED`**.
* **`AUTO_REJECT` / `MANUAL_REJECT`** ➔ Transitions the application to **`REJECTED`**.
* **`ROUTE_FOR_MANUAL_REVIEW`** ➔ Transitions the application to **`UNDER_REVIEW`**.
* **`REQUEST_MORE_INFO`** ➔ Transitions the application to **`DRAFT`**.

---

## 3. How Indexes Were Chosen

Indexes were designed based on expected query access patterns from real-time API gateways and downstream `dbt-core` analytical models. We prioritize read-heavy performance while maintaining a lean index set to minimize write overhead on high-frequency ingestion.

1. **`idx_active_session_resume` (`tokenized_phone_hash`, `created_at DESC`) `WHERE session_status = 'ACTIVE'`**
   - *Table:* **session_telemetry_log**
   - *Type:* **Partial Index**
   - *Business Reason:* **Citizen Experience & Drop-off Prevention.** Ensures a seamless, zero-lag conversational experience on WhatsApp. If the chatbot takes too long to fetch conversation history before replying, citizens will get frustrated and abandon the application process.
   - *Technical Rationale:* When a user re-engages, the API must find their most recent **`ACTIVE`** session in milliseconds. By indexing `session_status`, we explicitly filter out immutable or stale states, forcing the system to start a fresh, clean session if the previous one is not active. Here is exactly why each non-active state must *never* be resumed:
     - **`COMPLETED` (Immutability):** Once a session is completed, its payload has already been successfully committed to the governance ledger to generate a formal claim. Resuming it would append new extraction data to an already finalized or under-review application, breaking the immutability of the ledger.
     - **`TIMEOUT` (Stale Context):** A timeout occurs when a user exceeds the allowable response window. If the bot asks a question and the citizen replies days later, the context is entirely stale. Ignoring this state forces a hard reset (a fresh session), preventing the bot from misinterpreting a new message as an out-of-context answer to an old question.
     - **`ABANDONED` (Explicit User Intent):** This state triggers when a user explicitly opts out of the current flow (e.g., texting "Cancel" or "Stop"). Resuming an abandoned session violates the user's explicit command to kill the process. Ignoring it ensures their next message starts with a clean slate.
     - **`PENDING` (System Lock):** Unlike the terminal states, `PENDING` is a transitional state indicating the session is waiting on an asynchronous system action (e.g., waiting for an OTP to generate or a rate-limit to clear). The bot is not ready to process unstructured text yet. The resume index ignores it until the backend bottleneck clears and safely transitions it to `ACTIVE`.
     - **Performance Impact:** 
         - **Massive Space Savings (Storage):** The index footprint shrinks by 99% because historical sessions are excluded.
         - **Zero Write Overhead for Terminal States (Write Impact):** When a session transitions to `COMPLETED`, Postgres removes it from the index tree. This prevents database bloat and ensures `INSERT` and `UPDATE` operations remain fast over time.
         - **Lightning Fast Retrieval (Read Impact):** By completely ignoring 99% of a user's historical conversational rows, the database returns the single live thread in milliseconds, which is critical for real-time chatbot responsiveness.
2. **`idx_session_extraction_session_attempt` (`session_id`, `attempt_id DESC`)**
   - *Table:* **session_extraction_details**
   - *Business Reason:* **Data Accuracy & Payout Integrity.** Citizens frequently correct the AI (e.g., "No, I meant 5 acres, not 50"). This ensures the business only ever processes the final, citizen-approved payload, preventing incorrect financial disbursements.
   - *Technical Rationale:* Facilitates window functions (`ROW_NUMBER()`) and fast retrieval of the most recent extraction attempt within a specific session.
   - *Analytics Impact:* DBT models deduplicate payload history using this index. By natively storing `attempt_id` in descending order, we eliminate the need for expensive "filesort" operations when partitioning millions of extraction attempts.
3. **`idx_application_governance_session` (`session_id`, `decided_at DESC`)**
   - *Table:* **application_governance_ledger**
   - *Business Reason:* **Operational Visibility.** Leadership needs daily funnel dashboards showing the exact drop-off rate between a citizen starting a WhatsApp chat and receiving a finalized claim. This index makes building those daily executive dashboards possible.
   - *Technical Rationale:* Optimizes analytical joins between the final governance outcomes and the parent session telemetry logs (`session_id`). It pre-sorts by `decided_at` to instantly surface the latest decision if a claim was appealed.
   - *Analytics Impact:* By acting as a direct lookup map, this index prevents the database from scanning the entire historical ledger when joining data. This drastically reduces query time and ensures daily incremental DBT runs remain highly performant.
4. **`idx_governance_identity_lookup` (`tokenized_identity_hash`, `decided_at DESC`)**
   - *Table:* **application_governance_ledger**
   - *Business Reason:* **Fraud Prevention & Customer Service.** Strictly prevents "double-dipping" by ensuring a single citizen cannot receive duplicate payouts in the same season, while also allowing the chatbot to instantly answer the most common support question: "What is the status of my claim?"
   - *Technical Rationale:* The primary lookup vector for fraud validation and real-time API status checks. 
   - *Performance Impact:* 
     - **Fraud Prevention:** Before the rules engine processes a new extraction, it must query `tokenized_identity_hash` to ensure the citizen hasn't already received an `AUTO_APPROVE` payout this season (Double-dipping prevention).
     - **Status API:** Allows the real-time chatbot to execute sub-second lookups when a citizen asks "What is the status of my claim?" without scanning the entire governance ledger.
5. **`idx_governance_history_claim_time` (`claim_id`, `changed_at DESC`)**
   - *Table:* **application_governance_ledger_history**
   - *Business Reason:* **SLA Tracking & Accountability.** Allows management to measure operational bottlenecks, such as exactly how many days a claim sits in the manual review queue before an agent touches it, ensuring the program meets legal disbursement timelines.
   - *Technical Rationale:* Optimizes window functions and chronological sorting for state-transition analysis.
   - *Analytics Impact:* Enables downstream analysts to calculate "Time-in-State" metrics (e.g., SLA tracking for how long claims sit in the `UNDER_REVIEW` queue before transitioning to `FINALIZED`) without bogging down the database.

---

## 4. How Views Were Chosen

In accordance with DBT best practices, we utilize views to handle JSON unpacking, deduplication, and denormalization, protecting downstream BI tools (like Tableau or Metabase) from the underlying relational complexity.

### 4.1. `staging_committed_extractions` (Deduplication Filter)
- *Business Reason:* **Single Source of Truth for Reporting.** Ensures business reports and financial reconciliations only reflect the final, citizen-approved data. This prevents embarrassing or costly metric inflation caused by double-counting AI errors or user retries.
- *Technical Rationale:* A session can have multiple extraction attempts if the citizen corrects the AI (e.g., attempt 1 is `SUPERSEDED`, attempt 2 is `COMMITTED`). Downstream BI tools only care about the final valid extraction that drove the business claim.
- *Implementation:* Instead of using computationally expensive window functions like `ROW_NUMBER()`, this view acts as a simple, high-performance filter: `SELECT * FROM session_extraction_details WHERE processing_state = 'COMMITTED'`. This leverages our state machine to instantly isolate the winning payloads.

### 4.2. `staging_flattened_governance_ledger` (JSON Unpacking)
- *Business Reason:* **Self-Serve Analytics.** Empowers non-technical business analysts and product managers to easily build their own reports (e.g., summing up total approval amounts or graphing top rejection reasons) in tools like Tableau or PowerBI, without needing a data engineer to write complex JSON SQL queries for them.
- *Technical Rationale:* While `JSONB` provides engineering flexibility for sparse metadata, BI tools and data analysts struggle to query nested JSON natively. 
- *Implementation:* This view unpacks the `governance_metadata` column into strongly typed, top-level relational columns (e.g., `(governance_metadata->>'approval_amount')::numeric AS approval_amount`). This abstracts the JSON complexity within the data warehouse, presenting a traditional flat table to downstream consumers.
  - **Schema Contract:** This view intentionally acts as a gatekeeper. If backend engineers dynamically add new keys to the `JSONB` payload, they will not automatically appear in downstream BI tools until a data engineer explicitly maps them in this view. This protects dashboards from breaking due to unexpected schema changes while preserving backend agility.

### 4.3. `citizen_journey_funnel` (The Wide Table / OBT)
- *Business Reason:* **Executive Visibility & Conversion Tracking.** Gives leadership a unified, instantaneous view of the end-to-end citizen journey. It allows product managers to immediately answer questions like "Where exactly are citizens dropping off?" or "What is our true end-to-end conversion rate?" without waiting days for custom data requests.
- *Technical Rationale:* Executives and product managers need to track conversion funnels (e.g., "How many WhatsApp ingress sessions resulted in an Auto-Approved wheat claim?"). Doing a three-way join in a BI tool is slow and error-prone.
- *Implementation:* This denormalized "One Big Table" (OBT) creates a perfectly flat, one-to-one relationship by left-joining `session_telemetry_log` to `staging_committed_extractions`, and finally to `staging_flattened_governance_ledger`. By joining the staging views rather than raw tables, it guarantees exactly one row per citizen interaction with all JSON metadata fully unpacked.

---

## 5. Specific Architectural Trade-off Decisions

### Decision 5.1: Storage Strategy for Sparse Metadata (The Hybrid Approach)
**Context:** The governance ledger tracks highly variable and mutually exclusive fields. For example, an `APPROVED` application has an `approval_amount`, while a `REJECTED` application has a `rejection_reason`. We needed a storage strategy that balances type safety, performance, and operational agility.

**Options Evaluated:**
*   **Option A: Individual Standard Columns.** Mapping every attribute to a separate column
    *   *Pros:* Database-level type enforcement and maximum query performance.
    *   *Cons:* High Sparsity (creates a massive "NULL matrix" of empty columns for mutually exclusive states) and schema rigidity. Adding new business fields requires formal `ALTER TABLE` migrations, which causes operational bottlenecks (requiring DBA reviews and cross-environment deployments), risks temporarily locking the production database, and leads to long-term schema bloat.
*   **Option B: Protocol Buffers (Protobuf as `BYTEA`).** Compiling a strict schema into a binary blob
    *   *Pros:* Absolute type safety and highly compact storage.
    *   *Cons:* "Database Blindness" (Postgres cannot natively query inside the blob) and it breaks SQL-based analytics like DBT.
*   **Option C: Pure JSONB.** Storing everything in a single flexible JSON column
    *   *Pros:* Extreme flexibility with no migrations, eliminates NULL sparsity, and allows native SQL JSON extraction for DBT.
    *   *Cons:* Lack of native type enforcement and a larger storage footprint.

**Decision: The Hybrid Approach**
We elected to store core routing state fields (`governance_decision`, `application_status`) as standard relational columns, while storing all variable edge-case data in a unified `governance_metadata JSONB` column. 

**Rationale:**
*   **Operational Agility:** The policy team can dynamically introduce new metadata keys without database migrations or downtime.
*   **Best of Both Worlds:** We maintain high-performance B-tree indexing and strict type safety for the routing engine, while pushing volatile, unpredictable edge-case data into the flexible JSONB payload.

### Decision 5.2: Single v/s Split JSONB for approval/rejection metadata
**Context:** Now that we established using JSONB for sparse data, we evaluated whether to split this into distinct JSONB columns based on state (e.g., `approval_metadata JSONB` and `rejection_metadata JSONB`).
**Decision:** We elected to store all sparse variables in a single, unified `governance_metadata JSONB` column. 
**Rationale:**
*   **Avoiding the "NULL Matrix":** Splitting columns by state guarantees empty, dead columns for every row. Furthermore, other states like `UNDER_REVIEW` (which tracks `reviewer_id`) or `DRAFT` (which tracks `missing_info`) would require even more column splits, leading to severe schema bloat.
*   **Downstream Analytics (DBT) Ergonomics:** A single column allows data engineers to query `governance_metadata` directly. Splitting columns would force analysts to write complex `COALESCE(approval_metadata, rejection_metadata, ...)` logic in every staging model to find the relevant payload.
*   **Context Accumulation Across State Transitions:** Claims are not static. An application might enter `UNDER_REVIEW` (logging a `reviewer_id`) and later be `REJECTED` (logging a `rejection_reason`). A unified JSONB acts as an accumulating document that preserves the entire lifecycle context without overwriting or jumping between columns.
*   **Constraint Enforcement:** We ensure database-level safety (e.g., ensuring an approved claim *must* have an amount) via Postgres `CHECK` constraints (e.g., `CHECK (governance_decision != 'AUTO_APPROVE' OR (governance_metadata ? 'approval_amount'))`), granting strict safety without the structural downsides of split columns.

### Decision 5.3: Enforcing Types within JSONB
**Context:** `JSONB` accepts any valid JSON structure, meaning a developer could accidentally insert a string into a field expecting an integer.
**Decision:** While application-layer validation (Pydantic/Zod) is the primary defense, we added lightweight SQL `CHECK` constraints (e.g., `jsonb_typeof(governance_metadata->'approval_amount') = 'number'`) directly to the `schema.sql` definition as an un-bypassable database safety net.

### Decision 5.4: Storing Core Routing Logic as Native Enums vs. VARCHARs
**Context:** The system needs strict guarantees around valid states for routing (`governance_decision`), application lifecycle (`application_status`), telemetry phases (`session_status`), and financial clearing (`disbursement_status`).
**Decision:** We chose to implement all state-machine fields as native Postgres `ENUM` types rather than `VARCHAR` columns with `CHECK` constraints. 
**Rationale:** While `VARCHAR` is more portable across different SQL dialects, native Postgres `ENUM`s provide superior type safety, occupy far less disk space (4 bytes vs text length), and ensure clean application-layer integration by mapping perfectly to strict Pydantic or SQLAlchemy enum classes.

### Decision 5.5: Leaving `rejection_reason` as a Flexible String
**Context:** We evaluated whether `rejection_reason` (inside the `JSONB`) should be restricted to a strict database `ENUM`.
**Decision:** We left it as a flexible string check (`jsonb_typeof = 'string'`). Rejection policies and fraud patterns change rapidly. Hardcoding them in the DB would force engineering to run migrations every time a new policy is created. The exact list of valid reasons will be maintained in the application codebase instead, preserving operational agility.

### Decision 5.6: Naming `session_extraction_details` vs. `payload_extraction_details`
**Context:** Because this table tracks information extracted from individual message payloads, `payload_extraction_details` was initially considered.
**Decision:** We chose `session_extraction_details` to prioritize domain grouping. In our analytical context, payloads are rarely queried in isolation; they are evaluated as steps within a citizen's overarching session. Prefixing with `session_` groups the primary telemetry and its child extraction table together alphabetically in the data warehouse, making the schema hierarchy immediately obvious to downstream analytics engineers.

### Decision 5.7: Tracking Ledger History via Postgres Triggers vs. Application Layer
**Context:** The governance ledger is highly mutable. We need an immutable audit trail of how claims move through the state machine over time to track SLAs and bottlenecks. We evaluated whether the Python/Node application layer should manually write to a history table, or if the database should handle it natively.
**Decision:** We chose to enforce the `application_governance_ledger_history` via **PostgreSQL Triggers**.
**Rationale:**
*   **Guaranteed Auditability:** If a developer manually updates a claim state via a SQL GUI to fix a bug, or if an API route forgets to call the history insertion function, the audit trail is broken. A database-level `AFTER UPDATE` trigger guarantees 100% compliance; it is physically impossible to change the ledger without generating a history row.
*   **Decoupling:** The application layer only has to care about updating the current state of the claim. The database silently and automatically builds the temporal history in the background, keeping API code clean and reducing transactional overhead.
