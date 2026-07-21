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

11. **Practical Integration Fit:** The database should be easy to connect to from common ingestion (such as webhook-driven gateways) and analytics tools (ex: ETL/ELT pipelines,  dbt-based transformation jobs). This is a preference rather than a disqualifier: a candidate that is slightly less convenient is still acceptable if it clearly satisfies the core data, security, and analytical requirements. For example, whether the system uses a direct SQL interface, a simple HTTP API, or a thinner application-layer service can be decided separately in the API/access-layer decision.

---

## 3. Evaluation Method

The selection was judged from first principles against the requirements above rather than by vendor marketing. The most important factors are:

1. **Fit to the data model:** relational integrity, UUIDs, SQL window functions, and tokenization-friendly storage.
2. **Security posture:** RLS, encryption, and server-side validation controls.
3. **Operational simplicity:** Free-tier viability, predictable availability, and low operational overhead.
4. **Integration ergonomics:** How easily connectors, gateways, and analytics jobs can talk to the database.

Integration style matters, but it is a separate architectural concern from the database choice itself. A database that is easy to connect to is useful, especially for webhook-driven ingestion and analytics tooling, but the specific interface pattern should be decided in the companion access-layer decision rather than embedded as a primary reason for selecting the database.

---

## 4. Executive Summary

 **Supabase (Managed Cloud PostgreSQL)** is selected as the primary authoritative database. **Neon (Serverless PostgreSQL)** is recommended as a secondary serverless alternative.

---

## 5. Evaluated Database Options

The evaluation considered the main database families relevant to this project:

- PostgreSQL-based managed databases (Supabase, Neon)
- Self-hosted PostgreSQL deployments
- Managed PostgreSQL providers with a different operational model from Supabase/Neon
- Distributed SQL databases (CockroachDB)
- Document-oriented databases (MongoDB Atlas)

This covers the most plausible options for a free-tier, relational-first architecture with webhook-style ingestion and analytics needs.

### Option 1: Supabase (Managed Cloud PostgreSQL) — 🏆 Selected Primary

#### How it works
Supabase provides an open-source cloud suite backed by a managed PostgreSQL instance.

#### Why it fits
- **PostgreSQL-native relational model:** Matches the hard requirements for UUIDs, foreign keys, SQL window functions, and SQL-based analytical workloads.
- **Good ecosystem fit:** A mature PostgreSQL ecosystem makes it easier to connect gateways, automation tools, and analytics pipelines (for example, webhook-based ingestion, n8n automation, and dbt analytics jobs).
- **Security controls:** RLS, auth, and server-side extensions are available out of the box (for example, row-level policies for token_hash access, JWT-based auth, and pgcrypto checks).

#### Free Tier Limits
- 500 MB DB storage
- 1 GB file storage
- 2 shared vCPUs

#### Pros
- **Best overall balance:** It is the closest match to the project’s hard requirements while keeping the operational model simple.
- **Easier integration path:** The platform is friendlier for webhook-style ingestion, automation tools, and dbt-based analytics than many alternatives.
- **Strong built-in security features:** RLS, auth hooks, and extension support reduce the amount of custom plumbing needed.

#### Cons
- **Inactivity Pausing:** Pauses after 7 idle days; development work may need a keep-alive ping or scheduled heartbeat to avoid timeouts on strict carrier gateways like USSD `*147#` or IVR.
- **Storage Ceiling:** 500 MB is enough for Phase 0–4 prototyping and E2E verification, but production growth will require pruning, partitioning, or an upgrade path.

---

### Option 2: Neon (Serverless Cloud PostgreSQL) — ⭐ Recommended Alternative

#### How it works
Neon separates compute and storage, offering dynamically scaling serverless PostgreSQL.

#### Why it fits
- **Strong PostgreSQL compatibility:** It satisfies the relational and SQL requirements almost as well as Supabase.
- **Low-friction developer workflow:** Branching and serverless compute are convenient for experimentation and schema iteration.

#### Free Tier Limits
- 500 MB storage
- 0.25 vCPU

#### Pros
- **Modern developer workflow:** Branching and ephemeral environments make schema iteration and experimentation easier.
- **Low operational overhead:** It avoids self-hosting complexity while still staying close to standard PostgreSQL behavior.
- **Good fit for iterative prototyping:** Useful when the team needs to try multiple data-model revisions quickly.

#### Cons
- The team would need to add its own access layer for gateway-style ingestion, because Neon does not provide the same built-in convenience layer as Supabase; in practice, some form of application-layer API or webhook bridge would still be needed to receive WhatsApp or USSD events and write them into Neon safely, whereas Supabase offers more of that integration convenience out of the box.
- Cold starts and compute usage caps can be awkward for always-on public ingress or sustained traffic.

---

### Option 3: Self-Hosted PostgreSQL

#### How it works
A self-managed PostgreSQL deployment, such as a VM-based or containerized PostgreSQL service, is a valid alternative when full control over the database runtime is important.

#### Why it fits
- **Maximum control:** Full authority over versions, extensions, networking, backups, and operational policies.
- **Strong PostgreSQL compatibility:** It preserves the relational and SQL requirements exactly.

#### Free Tier Limits
- Depends on the hosting environment
- Often effectively free only when self-hosted on donated or low-cost infrastructure

#### Pros
- **Maximum control:** The team can choose the runtime, networking model, backup strategy, and extension policy directly.
- **No vendor-specific constraints:** It avoids platform-specific pauses, cold starts, or free-tier policy changes.
- **Flexible deployment model:** A self-hosted instance can be placed in a trusted environment if compliance needs demand it.

#### Cons
- The team must manage updates, backups, security, and uptime.
- It adds infrastructure overhead that is not ideal for the current rapid-prototyping goal.

---

### Option 4: CockroachDB Cloud (Serverless Basic)

#### How it works
CockroachDB is a cloud-native distributed SQL database using the PostgreSQL wire protocol.

#### Why it fits
- **Large free storage:** Useful for heavy logging or analytics retention.
- **Distributed resilience:** Attractive for multi-region or high-availability scenarios.

#### Free Tier Limits
- 10 GB storage
- 50M Request Units (RUs)/month forever

#### Pros
- **More generous free storage:** The free tier is materially larger for retaining logs or analytics history.
- **Distributed resilience:** The architecture is designed for multi-region and high-availability scenarios.
- **Useful for heavier operational workloads:** It could be attractive later if ingestion volume or retention grows beyond the initial scope.

#### Cons
- It is more complex than needed for the initial Phase 0–4 scope. Its distributed design introduces extra operational concerns that are unnecessary for a first implementation focused on reliable ingestion and simple analytics.
- It may require extra adapter work for `dbt-core` and SQL portability, because some PostgreSQL-compatible patterns do not translate perfectly to CockroachDB without tuning or rewrites.
- Added latency and operational overhead make it less ideal as the first choice when the project’s immediate need is correctness and simplicity rather than large-scale distributed resilience.

---

### Option 6: MongoDB Atlas (M0 Shared Cloud Cluster)

#### How it works
MongoDB Atlas is the industry-standard managed NoSQL document database service.

#### Why it fits
- **Flexible JSON storage:** It can ingest varied payloads quickly.

#### Free Tier Limits
- 512 MB storage
- Shared RAM/CPU across multi-cloud regions

#### Pros
- **Flexible payload handling:** It can absorb varied JSON-like event structures without forcing a rigid schema upfront.
- **Fast iteration for ingest-heavy use cases:** Useful when the payload shape is still evolving.
- **Broad ecosystem support:** Many application stacks already include MongoDB drivers and tooling.

#### Cons
- It does not satisfy the relational integrity and SQL-window requirements as cleanly as PostgreSQL-based options.
- The analytical workflow is less suitable for document-style joins and aggregations than for relational SQL.

---

## 6. Summary Comparison Matrix

| Evaluation Criteria            | Supabase (PostgreSQL)   | Neon (Serverless PG)    | Self-Hosted PostgreSQL | Managed PG Alternative | CockroachDB Cloud          | MongoDB Atlas (NoSQL)  |
| :----------------------------- | :---------------------- | :---------------------- | :--------------------- | :---------------------- | :------------------------- | :--------------------- |
| **Free Tier Storage**          | 500 MB                  | 500 MB                  | Varies                 | Varies                 | **10 GB**                  | 512 MB                 |
| **`dbt-core` Compatibility**   | ⭐⭐⭐⭐⭐ (Native)        | ⭐⭐⭐⭐⭐ (Native)        | ⭐⭐⭐⭐⭐ (Native)       | ⭐⭐⭐⭐⭐ (Native)       | ⭐⭐⭐⭐ (Compatible)         | ⭐ (Poor / Non-SQL)     |
| **Window Functions & CTEs**    | Full Support            | Full Support            | Full Support           | Full Support           | Full Support               | Limited (Aggregations) |
| **Relational Integrity (FKs)** | Declarative Enforcement | Declarative Enforcement | Declarative Enforcement | Declarative Enforcement | Declarative Enforcement    | Application-Level Only |
| **Integration Flexibility**   | Strong                  | Strong                  | Strong                  | Strong                  | Strong                      | Moderate               |
| **Idle Behavior**              | Pauses after 7 days     | Scales compute to 0     | Depends on hosting     | Depends on provider     | Always Active              | Always Active          |
| **Final Verdict**              | 🏆 **Selected Primary**  | ⭐ **Strong Alternative** | ⚖️ **Operationally Heavy** | ⚖️ **Needs Validation** | 💡 **Best for Large Storage** | ❌ **Rejected**         |

---

## 7. Supabase vs Neon

Although Supabase and Neon are both managed PostgreSQL options and satisfy the core relational and SQL requirements, they are not equivalent for this project.

- **Supabase** is preferred because it offers a more complete managed experience for a system that must support ingestion, access control, and analytics without adding substantial custom infrastructure. It is a stronger fit when the team wants a practical, turnkey platform for early implementation.
- **Neon** is a strong alternative when the priority is serverless Postgres, fast schema iteration, and a developer-centric workflow. Its branching and scaling model are attractive for experimentation, but it is less convenient as a full platform for gateway-style ingestion and operational simplicity.
- In short, the difference is not that Neon is technically inferior; it is that Supabase is a better overall fit for the project’s immediate need for a managed, reliable, and easier-to-operate data layer.

## 8. Selection Rationale

The database decision is about storage, integrity, and analytics fit. For this project, the database should also minimize operational overhead and support a practical path for ingestion, security, and dbt-based analytics.

We selected **Supabase** as our authoritative cloud database provider because it best satisfies the project’s hard requirements with the least complexity:

1. **Best fit to the data model:** It aligns directly with PostgreSQL features required for UUIDs, foreign keys, JSONB, and SQL window functions.
2. **Straightforward integration story:** The platform is easy to connect to while still remaining a managed, reliable data layer.
3. **Seamless `dbt-core` Integration:** PostgreSQL connectivity and SQL compatibility make the analytics pipeline straightforward.
4. **Appropriate free-tier scope:** The 500 MB ceiling is sufficient for the initial prototyping and simulation phases, with a clear upgrade path if the project scales.

In short, the reason to prefer Supabase is that it satisfies the storage, integrity, security, and analytics requirements better than the other options for this stage of the project.
