# Cloud Database Evaluation & Selection Rationale

**Framework Step:** Phase 0 · Step 0.1: Choose the Database Infrastructure  
**Target Environment:** Managed Cloud Database (100% Free Tier)  
**Related Documents:** 
- [roadmap.md](../roadmap.md)
- [flowchart.md](../design-specs/step3-guardrails/flowchart.md)

---

## 1. Goal

Identify, evaluate, and select a production-grade, authoritative cloud database provider to

a. Support citizen data ingestion (ex: whatsapp texts, voice transcriptions, etc.)
b. Persist system actions (ex: language translations, speech to text conversion etc.) and decisions (ex: claim denied, etc.)
c. Tokenized identity hashes via in-memory hashing protocols ([roadmap.md:L11](../roadmap.md#L11))
d. Structured agricultural claims
e. Support data ingestion from multi-channel entry points (WhatsApp, IVR Voice, USSD).
f. Scale to support millions of users in production (while operating within a 100% free tier during Phase 0–4 prototyping and verification).

---

## 2. Constraints

> [!WARNING]
> **Strict Operational & Architectural Boundaries**
> The selected database infrastructure must adhere strictly to four non-negotiable operational boundaries established in our design specifications:

1. **Strict Cost Constraint (100% Permanent Free Tier):**
   - Zero financial overhead permitted for development & intital testing.
2. **Zero-Trust Security & Tokenization Ingress:**
   - [roadmap.md:L11](../roadmap.md#L11) (Step 0.3) mandates in-memory PII tokenization (`SHA-256(raw_id + pepper_salt)` in volatile RAM).
   - Must handle rapid transactional write bursts to persist irreversible identity hashes generated in RAM without cleartext PII ever touching disk storage.
3. **Relational Integrity & Schema Enforcement:**
   - While detailed DDL schemas are not yet defined at this initial stage (Step 0.1), [roadmap.md:L10](../roadmap.md#L10) (Step 0.2) requires the database platform to natively support relational modeling with declarative foreign keys to enforce 1-to-Many cardinality between parent session lifecycle tracking and child transactional extraction logs as schemas are designed in Step 0.4.
4. **Analytical Data Transformation (`dbt-core` Compatibility):**
   - Must natively support standard SQL windowing functions (e.g., `ROW_NUMBER() OVER`) and CTEs to execute analytical deduplication of multi-attempt conversational loops required by [roadmap.md:L12](../roadmap.md#L12) (Step 0.4).

---

## 3. Executive Summary

To support the multi-channel citizen intake pipeline (WhatsApp, IVR Voice, USSD) defined in the AgriStack DPI architecture, we evaluated cloud database providers offering a **permanent free tier**.

> [!IMPORTANT]
> **Selection Verdict:** **Supabase (Managed Cloud PostgreSQL)** is selected as the primary authoritative database. **Neon (Serverless PostgreSQL)** is recommended as a secondary serverless alternative.

Selection criteria were derived directly from [roadmap.md](../roadmap.md) (Step 0.1–0.4) and [flowchart.md](../design-specs/step3-guardrails/flowchart.md), requiring ACID relational integrity, UUID primary keys, rapid transactional write bursts, and full compatibility with `dbt-core` SQL window functions.

---

## 4. Evaluated Database Options

### Option 1: Supabase (Managed Cloud PostgreSQL) — 🏆 Selected Primary

Supabase provides an open-source cloud suite backed by a managed PostgreSQL instance.

- **Free Tier Limits:** 500 MB DB storage, 1 GB file storage, 2 shared CPU cores.
- **Pros:**
  - **Automated PostgREST APIs:** Instant REST endpoints for n8n workflows and gateways.
  - **100% `dbt-core` Compatibility:** Standard `dbt-postgres` driver for window queries.
  - **Row Level Security (RLS):** Fine-grained access control for caseworkers vs. APIs.
- **Cons:**
  - **Inactivity Pausing:** Pauses after 7 idle days (auto-wakes in ~2s on webhook, which requires a keep-alive ping or scheduled heartbeat during development to prevent timeout drops on strict carrier gateways like USSD `*147#` or IVR).
  - **Storage Ceiling:** 500 MB cap is sufficient for Phase 0–4 prototyping and E2E verification, but production scaling to millions of users will require automated data pruning/TTL routines or upgrading to a paid/self-hosted PostgreSQL cluster.

---

### Option 2: Neon (Serverless Cloud PostgreSQL) — ⭐ Recommended Alternative

Neon separates compute and storage, offering dynamically scaling serverless PostgreSQL.

- **Free Tier Limits:** 500 MB storage, 0.25 vCPU, 100 compute hours/month.
- **Pros:**
  - **Auto-Scaling Compute:** Absorbs traffic spikes, scaling to zero when idle.
  - **Database Branching:** Instant copy-on-write branching for schema testing.
- **Cons:**
  - **Cold Starts:** ~100–300ms wake-up latency when resuming from zero compute.
  - **Compute Hour Caps:** Requires monitoring if background polling workers run 24/7.

---

### Option 3: CockroachDB Cloud (Serverless Basic)

CockroachDB is a cloud-native distributed SQL database using the PostgreSQL wire protocol.

- **Free Tier Limits:** 10 GB storage, 50M Request Units (RUs)/month forever.
- **Pros:**
  - **Massive Free Storage:** 10 GB capacity (20x higher) for extensive text logging.
  - **Multi-Region Resiliency:** Distributed consensus matches national DPI goals.
- **Cons:**
  - **Macro Compatibility:** Minor DDL nuances require custom adapters for `dbt-core`.
  - **Latency Overhead:** Consensus protocol adds ~10–20ms latency on single writes.

---

### Option 4: MongoDB Atlas (M0 Shared Cloud Cluster)

MongoDB Atlas is the industry-standard managed NoSQL document database service.

- **Free Tier Limits:** 512 MB storage, shared RAM/CPU across multi-cloud regions.
- **Pros:**
  - **Native Document Schema:** Ingests JSON payloads (`{type: "audio"}`) seamlessly.
- **Cons:**
  - **Architectural Mismatch:** Cannot cleanly execute SQL window deduplication.
  - **No Declarative Foreign Keys:** Relational integrity relies on application code.

---

## 5. Summary Comparison Matrix

| Evaluation Criteria            | Supabase (PostgreSQL)   | Neon (Serverless PG)    | CockroachDB Cloud          | MongoDB Atlas (NoSQL)  |
| :----------------------------- | :---------------------- | :---------------------- | :------------------------- | :--------------------- |
| **Free Tier Storage**          | 500 MB                  | 500 MB                  | **10 GB**                  | 512 MB                 |
| **`dbt-core` Compatibility**   | ⭐⭐⭐⭐⭐ (Native)        | ⭐⭐⭐⭐⭐ (Native)        | ⭐⭐⭐⭐ (Compatible)         | ⭐ (Poor / Non-SQL)     |
| **Window Functions & CTEs**    | Full Support            | Full Support            | Full Support               | Limited (Aggregations) |
| **Relational Integrity (FKs)** | Declarative Enforcement | Declarative Enforcement | Declarative Enforcement    | Application-Level Only |
| **API Auto-Generation**        | Built-in (PostgREST)    | None (Requires App)     | None (Requires App)        | Data API Available     |
| **Idle Behavior**              | Pauses after 7 days     | Scales compute to 0     | Always Active              | Always Active          |
| **Final Verdict**              | 🏆 **Selected Primary**  | ⭐ **Strong Alternative** | 💡 **Best for Large Storage** | ❌ **Rejected**         |

---

## 6. Selection Rationale

We selected **Supabase** as our authoritative cloud database provider based on four key differentiators:

1. **Flawless Schema Alignment:** Direct support for PG 15+, JSONB storage, UUIDs, and declarative foreign keys required by [roadmap.md:L9-L12](../roadmap.md#L9-L12) (Step 0.1–0.4) and the master flowchart.
2. **Elimination of Boilerplate:** PostgREST APIs let ingestion connectors in [flowchart.md:L24-L28](../design-specs/step3-guardrails/flowchart.md#L24-L28) post JSON directly.
3. **Seamless `dbt-core` Integration:** PG connection strings run deduplication window models without changes.
4. **Zero Financial Cost for Prototyping:** Ample 500 MB free capacity to process thousands of test citizen sessions during Phase 0–4 scaffolding and E2E simulation verification (with clear upgrade/pruning paths for production scaling).
