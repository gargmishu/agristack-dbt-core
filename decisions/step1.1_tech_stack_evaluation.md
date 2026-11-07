# Stack Selection: Language, Runtime & AI Frameworks

**Framework Step:** Phase 1 · Step 1.1: Choose Language, Runtime & AI Frameworks
**Related Documents:**
- [roadmap.md](../roadmap.md)
- The Phase 0 data and security requirements.

---

## 1. Goal

Select the core application runtime, orchestration engine, and AI framework stack for the Zero-Trust DPI Orchestrator. Choices must satisfy 3 non-negotiable constraints:
1. **Sovereign compliance** — Sensitive data must not leave Indian DPI boundaries during processing.
2. **Real-time I/O** — WhatsApp webhooks, IVR SIP streams, and USSD sessions require low-latency, concurrent I/O handling.
3. **AI integration** — Structured entity extraction via local/sovereign SLM and ASR/NMT/TTS via Bhashini must integrate cleanly without leaking citizen data to commercial cloud proxies.

---

## 2. Decision 1: Core Application Runtime

The orchestrator must handle high-concurrency webhook ingestion while simultaneously coordinating downstream AI models and database transactions.

### Options Evaluated

| Option | Pros | Cons |
| :--- | :--- | :--- |
| **Python (FastAPI)** | Undisputed leader for AI/ML integration. Native support for Pydantic v2, SQLAlchemy 2.0, and async HTTP orchestration (`httpx`). FastAPI provides excellent async I/O. | GIL (Global Interpreter Lock) can bottleneck CPU-bound concurrent tasks, though less relevant for I/O bound webhooks. |
| **Node.js (TypeScript)** | Best-in-class event loop for handling thousands of concurrent I/O requests (webhooks, DB calls). Strong ecosystem for state machines (XState). | AI/ML ecosystem is secondary to Python. Often requires bridging to Python for complex AI pipelines. |
| **Go (Golang)** | Phenomenal concurrency (goroutines) and extremely low resource footprint. Great for strict API gateways. | Minimal native AI ecosystem. Writing complex state machines and handling unstructured JSON can be verbose. |

**Decision: Python (FastAPI + Pydantic v2)**

While Node.js excels at raw I/O, this project is primarily an **AI orchestration and policy-governance pipeline**. Python offers the most mature ecosystem for interacting with local SLMs (Ollama / vLLM) and building robust data pipelines. FastAPI's async capabilities are more than sufficient for the expected webhook load, and Pydantic v2 provides the strict runtime validation required for DPI payloads.

---

## 3. Decision 2: Orchestration Engine for State Transitions

### The Problem
The governance routing engine requires a strict, testable, deterministic state machine across 3 evaluation gates (Gate 1: Security & Anti-Double-Dipping → Gate 2: Confidence & Completeness Loop → Gate 3: Sovereign Registry & Policy Matrix). Ad-hoc untyped `if/else` chains are fragile and untestable.

### Options Evaluated

| Option | Description | Pros | Cons |
| :--- | :--- | :--- | :--- |
| **Temporal / Cadence** | A polyglot, standalone infrastructure platform for microservice orchestration and durable execution. | Enterprise-grade orchestration with guaranteed execution, built-in retries, and seamless handling of long-running processes. | High infrastructure overhead requiring a separate managed cluster. |
| **External FSM Library (`transitions`)** | Third-party dynamic Finite State Machine library using runtime string callbacks and monkey-patched model methods. | Concise declarative table definition for simple state graphs. | Dynamic attribute injection breaks strict `mypy --strict` static typing and mutates models in-place, violating our immutable `frozen=True` Pydantic v2 contract invariants. |
| **Deterministic Native Python + Pydantic v2 State-Matrix Engine + SQLAlchemy Core** | Pure, type-safe async state evaluators enforcing immutable Pydantic v2 contract truth tables with synchronous SQLAlchemy 2.0 Core ledger persistence. | 100% compatible with `mypy --strict` and `frozen=True` domain models, zero third-party FSM dependency bloat, and exhaustive unit testability across every state transition. | State transition invariants must be explicitly codified in Pydantic `@model_validator(mode="after")` truth tables and orchestrator gate methods. |

**Decision: Deterministic Native Python + Pydantic v2 State-Matrix Engine + SQLAlchemy 2.0 Core Persistence**

We implement the 3-Gate Governance routing engine as a deterministic, strictly typed native Python orchestrator backed by immutable Pydantic v2 contract truth tables (`StrictBaseModel`). To handle persistence, auditability, and multi-turn compaction without the heavy operational overhead of Temporal, state transitions are persisted to our PostgreSQL database (or SQLite in local/CI environments) via **SQLAlchemy 2.0 Core** (`psycopg[binary]`) across the `session_telemetry_log`, `session_extraction_details`, `consent_registry`, and `governance_decisions` tables defined in Phase 0.

---

## 4. Decision 3: AI & ML Framework Stack

The AI stack is split into two concerns: **Speech processing** (ASR + NMT + TTS) and **Structured Entity Extraction** (SLM).

### 4.1 Speech Processing: Digital India Bhashini + Offline Deterministic Mock

| Service | Role | Decision |
| :--- | :--- | :--- |
| **Bhashini ULCA API** | Production ASR, NMT (Hindi→English, regional languages→English), TTS | **Primary for production.** Sovereign India DPI boundary compliance. Data does not leave Indian infrastructure. |
| **Deterministic Offline Mock (`ENVIRONMENT=development\|testing`)** | Hermetic local development and CI testing | **Development/testing default.** Eliminates external commercial cloud proxies (such as Groq Whisper) so zero citizen or test audio is ever transmitted outside sovereign/local boundaries, while guaranteeing sub-millisecond hermetic CI runs (see [step3.6_speech_and_translation_evaluation.md](step3.6_speech_and_translation_evaluation.md)). |

> [!WARNING]
> **Production Rule:** Commercial third-party cloud speech proxies are strictly prohibited. Production deployments (`ENVIRONMENT=production`) must route exclusively through the sovereign Bhashini ULCA pipeline (`BHASHINI_API_URL`, `BHASHINI_API_KEY`, `BHASHINI_USER_ID`), and the service factory fails fast at startup if credentials are omitted.

### 4.2 Structured Entity Extraction Framework

To perform structured entity extraction (e.g., parsing `district`, `crop_name`, and `survey_number` from text), we need an inference framework.

| Option | Description | Pros | Cons |
| :--- | :--- | :--- | :--- |
| **Cloud APIs (Groq / OpenAI / Gemini)** | Off-device, managed LLM inference endpoints. | Fast inference and zero local hardware requirements. | Routes sensitive user queries to external cloud providers, directly violating DPDP Act sovereign data requirements for public infrastructure. |
| **Hugging Face `transformers`** | Native Python library for loading and running models locally via PyTorch. | Deeply integrated with Python; maximal control over the generation loop and tokenization. | Extremely inefficient for concurrent inference. No built-in batching or REST API. High VRAM overhead. |
| **vLLM / Ollama over Pooled `httpx.AsyncClient`** | Local/sovereign inference engine (Ollama GGUF on local/edge nodes or vLLM on sovereign GPU nodes) accessed via an asynchronous connection-pooled HTTP client. | Zero heavy ML framework bloat inside the FastAPI gateway container; supports strict JSON schema enforcement (`temperature=0.0`) and seamless switching between local Ollama and sovereign vLLM endpoints. | Requires a running local/sovereign inference server in `ENVIRONMENT=production`. |

**Decision: Sovereign Local SLM (Ollama / vLLM) via Pooled `httpx.AsyncClient` (Prod), Deterministic Heuristic Extractor (Dev/Test)**

To guarantee that citizen data never leaves the sovereign boundary, we reject external commercial Cloud APIs. In production, the orchestrator communicates with a sovereign 8B-parameter quantized SLM endpoint (such as **Ollama** or **vLLM** running `LLaMA-3-8B-Instruct` at `temperature=0.0`) over a shared, connection-pooled `httpx.AsyncClient` without coupling the gateway to vendor-specific SDKs. In development and automated test suites (`ENVIRONMENT=development|testing`), a deterministic offline entity extractor provides reproducible, zero-latency extraction.

---

## 5. Summary: Confirmed Stack

| Concern | Technology | Environment |
| :--- | :--- | :--- |
| Core Application Framework | **Python 3.11+ (FastAPI + Uvicorn)** | Dev + Test + Prod |
| Data Validation & Contracts | **Pydantic v2 (`StrictBaseModel`)** | Dev + Test + Prod |
| State Machine & Governance | **Deterministic Native Python + Pydantic v2 Truth Tables** | Dev + Test + Prod |
| ASR / NMT / TTS (Prod) | **Digital India Bhashini ULCA API (`httpx.AsyncClient`)** | Prod (`ENVIRONMENT=production`) |
| ASR / NMT / TTS (Dev/Test) | **Deterministic Offline Speech Mock** | Dev + Test |
| Entity Extraction (Prod) | **Sovereign Local SLM (Ollama / vLLM, 8B 4-bit via `httpx.AsyncClient`)** | Prod (`ENVIRONMENT=production`) |
| Entity Extraction (Dev/Test) | **Deterministic Offline Heuristic Extractor** | Dev + Test |
| Database Persistence | **SQLAlchemy 2.0 Core + PostgreSQL (`psycopg[binary]`) / SQLite** | Dev + Test + Prod |

