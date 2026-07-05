# Cloud Database Evaluation & Selection Rationale

**Framework Step:** Phase 0 · Step 0.1: Choose the Database Infrastructure  
**Target Environment:** Managed Cloud Database (100% Free Tier)  
**Related Documents:** 
- [roadmap.md](../roadmap.md)
- [flowchart.md](../design-specs/step3-guardrails/flowchart.md)

---

## 1. Goal

Identify, evaluate, and select a production‑grade, authoritative cloud database that can securely store tokenized citizen data, support multi‑channel ingestion, and scale to millions of users while remaining within a permanent free tier.

---

## 2. Requirements

> [!WARNING]
> **Non‑Negotiable Operational Boundaries**
> The selected database must satisfy all of the following requirements. Any candidate that violates one is disqualified.

1. **Free Tier (Zero Cost):** All storage, compute, and ancillary services must remain within a 100 % permanent free tier throughout Phase 0‑4.

2. **No Clear‑Text PII on Disk:** The database must accept and durably persist only pre‑tokenized data. Cleartext personally‑identifiable information must never reach persistent storage (see [roadmap.md](../roadmap.md) Step 0.3).

3. **ACID Transactions:** Every write must be atomic, consistent, isolated, and durable. Partial or uncommitted writes are not acceptable for identity‑hash ingestion.

4. **UUID Primary Keys:** All tables must use UUID‑based primary keys to prevent sequence enumeration and support distributed ingestion from multiple entry channels.

5. **Relational Integrity:** The database must natively enforce declarative foreign keys to maintain 1‑to‑Many cardinality between session records and their child event logs (see [roadmap.md](../roadmap.md) Step 0.2).

6. **SQL Analytical Compatibility:** Must support standard SQL window functions (e.g., `ROW_NUMBER() OVER`) and CTEs (Common Table Expressions — named temporary result sets defined with a `WITH` clause that let you chain multi‑step queries in a single readable SQL statement) required by analytical deduplication models (see [roadmap.md](../roadmap.md) Step 0.4). This capability is exercised by `dbt-core` transformation models.

7. **Horizontal Scale:** Must handle concurrent multi‑channel ingestion (WhatsApp, IVR, USSD) and scale toward millions of users without architectural changes.

8. **Row‑Level Security (RLS):** Must support fine‑grained access control at the row or column level so that only the tokenization service can read or write identity‑hash columns. For example: an analytics role querying `citizen_sessions` automatically receives `NULL` for the `token_hash` column — the DB enforces this via policy, so a misconfigured query or rogue service cannot accidentally expose tokens even if it has SELECT access to the table.

9. **Encryption‑at‑Rest:** All data stored on disk (token hashes, session metadata, WAL logs, backups) must be encrypted at the storage layer. This is distinct from PII tokenization — tokenization prevents cleartext PII from entering the DB, while encryption‑at‑rest protects whatever *is* stored (including tokens and metadata) from physical disk access or stolen backups. Even opaque tokens are sensitive: they can be cross‑referenced with external datasets for re‑identification, and unencrypted metadata (timestamps, channel, session duration) can reveal behaviour patterns. A clear key‑management model must be documented — the DB choice directly determines who holds the at‑rest encryption key (provider‑managed KMS vs. customer‑controlled KMS), which affects data‑sovereignty compliance.

10. **Extension / Stored‑Procedure Support:** Must allow server‑side extensions or functions (e.g., `pgcrypto`) to validate token format at write time. This provides defense‑in‑depth: even if an application‑layer bug sends cleartext PII instead of a token, the DB rejects the write before it ever touches disk — the application layer alone cannot guarantee this because bugs, misconfigured middleware, or a compromised service could bypass it.

---

## 3. Executive Summary

 **Supabase (Managed Cloud PostgreSQL)** is selected as the primary authoritative database. **Neon (Serverless PostgreSQL)** is recommended as a secondary serverless alternative.

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
