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
3. **AI integration** — Structured entity extraction via local SLM and ASR via Bhashini/Groq proxy must integrate cleanly.

---

## 2. Decision 1: Core Application Runtime

The orchestrator must handle high-concurrency webhook ingestion while simultaneously coordinating downstream AI models and database transactions.

### Options Evaluated

| Option | Pros | Cons |
| :--- | :--- | :--- |
| **Python (FastAPI)** | Undisputed leader for AI/ML integration. Native support for LangChain, LlamaIndex, and Ollama. FastAPI provides excellent async I/O. | GIL (Global Interpreter Lock) can bottleneck CPU-bound concurrent tasks, though less relevant for I/O bound webhooks. |
| **Node.js (TypeScript)** | Best-in-class event loop for handling thousands of concurrent I/O requests (webhooks, DB calls). Strong ecosystem for state machines (XState). | AI/ML ecosystem is secondary to Python. Often requires bridging to Python for complex AI pipelines. |
| **Go (Golang)** | Phenomenal concurrency (goroutines) and extremely low resource footprint. Great for strict API gateways. | Minimal native AI ecosystem. Writing complex state machines and handling unstructured JSON can be verbose. |

**Decision: Python (FastAPI + Pydantic)**

While Node.js excels at raw I/O, this project is primarily an **AI orchestration pipeline**. Python offers the most mature ecosystem for interacting with local SLMs (Ollama) and building robust data pipelines. FastAPI's async capabilities are more than sufficient for the expected webhook load, and Pydantic provides the strict runtime validation required for DPI payloads.

---

## 3. Decision 2: Orchestration Engine for State Transitions

### The Problem
The governance routing engine requires a strict, testable, deterministic state machine across 3 evaluation gates (Ingress Gate → Validation Gate → Governance Matrix). Ad-hoc `if/else` chains are fragile and untestable.

### Options Evaluated

| Option | Description | Pros | Cons |
| :--- | :--- | :--- | :--- |
| **Temporal / Cadence** | A polyglot, standalone infrastructure platform for microservice orchestration and durable execution. | Enterprise-grade orchestration with guaranteed execution, built-in retries, and seamless handling of long-running processes. | High infrastructure overhead requiring a separate managed cluster. |
| **Python `transitions` + Supabase** | Combining a native Python Finite State Machine (FSM) library with synchronous writes to our PostgreSQL database. | Explicit state definitions in code, easily testable, and leverages our existing database without adding new infrastructure. | Requires manual wiring to synchronize the in-memory FSM state with the database records. |
| **Custom if/else logic** | Native control flow using standard Python conditional statements. | Simplest to implement initially for basic branching. | Impossible to verify all state transitions are exhaustive. High risk of silent bugs in edge cases. |

**Decision: Python `transitions` library + Supabase State Tracking**

We will use the Python `transitions` library to strictly define the valid routing gates in code. To handle persistence and retries (without the heavy overhead of Temporal), we will persist the state synchronously to our Supabase PostgreSQL database at each transition using the `session_telemetry_log`, `session_extraction_details`, and the newly added `consent_registry` tables defined in Phase 0.

---

## 4. Decision 3: AI & ML Framework Stack

The AI stack is split into two concerns: **Speech processing** (ASR + NMT + TTS) and **Structured Entity Extraction** (SLM).

### 4.1 Speech Processing: Bhashini + Groq Whisper Proxy

| Service | Role | Decision |
| :--- | :--- | :--- |
| **Bhashini API** | Production ASR, NMT (Hindi→English, regional languages→English), TTS | **Primary for production.** Sovereign India DPI boundary compliance. Data does not leave Indian infrastructure. |
| **Groq Whisper v3 (proxy)** | Fast ASR for development and local testing | **Development/fallback only.** Groq's inference is extremely fast for rapid prototyping, but routes data outside India — strictly prohibited for production deployments. |

> [!WARNING]
> **Production Rule:** The Groq Whisper proxy must be gated behind an environment flag (`ENVIRONMENT != 'production'`). Any production deployment must route exclusively through the Bhashini API to satisfy DPDP Act sovereign data requirements.

### 4.2 Structured Entity Extraction Framework

To perform structured entity extraction (e.g., parsing `district` and `crop_type` from text), we need an inference framework.

| Option | Description | Pros | Cons |
| :--- | :--- | :--- | :--- |
| **Cloud APIs (Groq / OpenAI / Gemini)** | Off-device, managed LLM inference endpoints. | Fastest inference, highest quality models, and zero local hardware requirements. | Routes sensitive user queries to external cloud providers, directly violating DPDP Act sovereign data requirements for public infrastructure. |
| **Hugging Face `transformers`** | Native Python library for loading and running models locally via PyTorch. | Deeply integrated with Python; maximal control over the generation loop and tokenization. | Extremely inefficient for concurrent inference. No built-in batching or REST API. High VRAM overhead. |
| **vLLM** | High-throughput and memory-efficient local inference engine with PagedAttention. | Industry-leading performance for high-concurrency production deployments. | Massive dependency footprint (requires PyTorch, specific CUDA kernels, Ray). Hard to run on non-NVIDIA hardware. Overkill for local development on consumer hardware (e.g., Apple Silicon). |
| **Ollama** | Lightweight, container-like local inference engine for quantized models (GGUF). | Effortless to run locally as a single, pre-compiled binary with zero Python dependencies. Built-in REST API and excellent Python SDK. | Lower throughput than vLLM at massive scale, but sufficient for our anticipated concurrency. |

**Decision: Ollama (primary), Groq (dev/test only)**

To guarantee that citizen data never leaves the sovereign boundary, we must use a local Small Language Model (SLM). We reject Cloud APIs for production due to data privacy constraints. Between the local options, **Ollama** running a quantized 8B parameter model (e.g., LLaMA-3-8B-Instruct-GGUF) strikes the ideal balance. It is lightweight enough to run economically on private infrastructure (or a developer's laptop) while providing a robust REST API out-of-the-box. We will use the official `ollama-python` library to integrate it into the FastAPI application.

---

## 5. Summary: Confirmed Stack

| Concern | Technology | Environment |
| :--- | :--- | :--- |
| Core Application Framework | **Python (FastAPI)** | Dev + Prod |
| Data Validation | **Pydantic** | Dev + Prod |
| State Machine Engine | **Python `transitions` library** | Dev + Prod |
| ASR / NMT / TTS | **Bhashini API** | Prod only |
| ASR Proxy (dev) | **Groq Whisper v3** | Dev / local testing only |
| Structured Entity Extraction | **Ollama (LLaMA-3-8B, 4-bit)** | Prod (sovereign) |
| SLM Proxy (dev) | **Groq (cloud inference)** | Dev / local testing only |
| Database Client | **Supabase Python SDK** | Dev + Prod |
