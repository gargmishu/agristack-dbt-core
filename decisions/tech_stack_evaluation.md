# Stack Selection: Language, Runtime & AI Frameworks

**Framework Step:** Phase 1 · Step 1.1: Choose Language, Runtime & AI Frameworks  
**Related Documents:**
- [roadmap.md](../roadmap.md)
- [readiness_profile.md](../design-specs/step0-env-readiness/readiness_profile.md)
- [flowchart.md](../design-specs/step3-guardrails/flowchart.md)

---

## 1. Goal

Select the core application runtime, orchestration engine, and AI framework stack for the Zero-Trust DPI Orchestrator. Choices must satisfy four non-negotiable constraints:
1. **Sovereign compliance** — sensitive data must not leave Indian DPI boundaries during processing.
2. **Real-time I/O** — WhatsApp webhooks, IVR SIP streams, and USSD sessions require low-latency, concurrent I/O handling.
3. **AI integration** — structured entity extraction via local SLM and ASR via Bhashini/Groq proxy must integrate cleanly.
4. **Consistency with existing code** — the `src/` directory already contains JavaScript files targeting an n8n workflow runtime.

---

## 2. Decision 1: Core Application Runtime

### Constraint
The existing codebase (`src/parse_groq_response.js`, `src/speech_to_text_transcription.js`, `n8n-config/`) already uses **JavaScript inside n8n function nodes** as the primary execution environment. The runtime is therefore partially committed.

### Architecture: n8n (Workflow Orchestration) + Node.js (Custom Logic)

| Layer | Technology | Rationale |
| :--- | :--- | :--- |
| **Workflow Orchestration** | **n8n (self-hosted)** | Existing workflows are already built in n8n. It provides a visual state machine for wiring connectors (WhatsApp webhooks, Twilio IVR, HTTP nodes) to custom JavaScript function nodes without reimplementing HTTP boilerplate. |
| **Custom Business Logic** | **Node.js (JavaScript ES2022+)** | Already in use. Node's event loop handles high-concurrency I/O (simultaneous webhook callbacks) efficiently. Well-supported SDKs exist for Supabase, Twilio, Meta APIs, and Ollama. |
| **Language** | **JavaScript (CommonJS / ES Modules)** | Consistent with all existing `src/` files. TypeScript is recommended as a future upgrade (Step 1.2) for strict runtime safety, but not mandated in Phase 1 to avoid blocking scaffold work. |

> [!IMPORTANT]
> **Why not Python (FastAPI)?**  
> Python would be the natural choice for an AI-heavy pipeline in isolation. However, the existing codebase, n8n workflow exports, and all `src/` logic are already JavaScript. Switching to Python mid-project would require maintaining two separate runtimes with a bridge layer, increasing operational complexity without sufficient benefit at this stage.

---

## 3. Decision 2: Orchestration Engine for State Transitions

### The Problem
The governance routing engine requires a strict, testable, deterministic state machine across 3 evaluation gates (Ingress Gate → Validation Gate → Governance Matrix). Ad-hoc `if/else` chains in JavaScript are fragile and untestable.

### Options Evaluated

| Option | Pros | Cons |
| :--- | :--- | :--- |
| **XState v5** (JavaScript state machine library) | Fully deterministic, visualizable, testable in isolation, maps directly to the flowchart state diagram. First-class TypeScript support. | Requires explicit state/event/transition definitions (more upfront work). |
| **n8n IF/Switch nodes** | No extra dependency, visual wiring. | Non-deterministic at scale; routing logic lives in the UI, not version-controlled code. Cannot be unit tested. |
| **Custom if/else in Node.js** | Simplest. | Impossible to verify all state transitions are exhaustive. High risk of silent bugs in edge cases. |

**Decision: XState v5**

XState's state machine model maps exactly to the flowchart's three evaluation gates. Each gate becomes an XState state, each routing outcome becomes a transition guarded by a condition function. This guarantees:
- Every valid state transition is explicitly declared.
- The machine rejects invalid state transitions (e.g., a `COMMITTED` payload cannot go back to `STAGED`).
- Unit tests can assert the machine's behavior without hitting any network or database.

---

## 4. Decision 3: AI & ML Framework Stack

The AI stack is split into two concerns: **Speech processing** (ASR + NMT + TTS) and **Structured Entity Extraction** (SLM).

### 4.1 Speech Processing: Bhashini + Groq Whisper Proxy

| Service | Role | Decision |
| :--- | :--- | :--- |
| **Bhashini API** | Production ASR, NMT (Hindi→English, regional languages→English), TTS | **Primary for production.** Sovereign India DPI boundary compliance. Data does not leave Indian infrastructure. |
| **Groq Whisper v3 (proxy)** | Fast ASR for development and local testing | **Development/fallback only.** Already integrated in `src/speech_to_text_transcription.js`. Groq's inference is faster and requires no local VRAM during dev, but routes data outside India — not acceptable for production deployments. |

> [!WARNING]
> **Production Rule:** The Groq Whisper proxy must be gated behind an environment flag (`NODE_ENV !== 'production'` or `BHASHINI_OVERRIDE=true`). Any production deployment must route exclusively through the Bhashini API to satisfy DPDP Act sovereign data requirements.

### 4.2 Structured Entity Extraction: Ollama (Local SLM)

| Option | Pros | Cons |
| :--- | :--- | :--- |
| **Ollama (LLaMA-3-8B / DeepSeek-R1-8B, 4-bit quantized)** | Fully local, sovereign, zero network latency after model load, already documented in `readiness_profile.md`. | Requires local GPU/CPU resources (~4.7 GB VRAM). |
| **Groq API (cloud inference)** | Fastest inference, no local resources needed. | Routes data off-device to US infrastructure — violates DPDP Act for production. |
| **OpenAI / Gemini API** | Best quality models. | Same sovereign data violation concern as Groq. |

**Decision: Ollama (primary), Groq (dev/test only)**

Ollama runs the quantized SLM locally on the Apple Silicon MacBook (as documented in `readiness_profile.md`) and in production on a sovereign India-hosted VM. The `ollama` Node.js SDK provides a simple REST interface to call structured JSON extraction prompts.

---

## 5. Summary: Confirmed Stack

| Concern | Technology | Environment |
| :--- | :--- | :--- |
| Workflow Orchestration | **n8n (self-hosted)** | Dev + Prod |
| Custom Logic Runtime | **Node.js (JavaScript ES2022+)** | Dev + Prod |
| State Machine Engine | **XState v5** | Dev + Prod |
| ASR / NMT / TTS | **Bhashini API** | Prod only |
| ASR Proxy (dev) | **Groq Whisper v3** | Dev / local testing only |
| Structured Entity Extraction | **Ollama (LLaMA-3-8B, 4-bit)** | Prod (sovereign) |
| SLM Proxy (dev) | **Groq (cloud inference)** | Dev / local testing only |
| Database Client | **Supabase JS SDK (`@supabase/supabase-js`)** | Dev + Prod |

---

## 6. Next Step

**Step 1.2: Enforce Runtime Strictness & Linting** — Configure ESLint with strict rules, enable JSON Schema validation via `ajv` for all inter-layer payloads, and define the canonical `StandardizedIntakePayload` schema that every connector must emit.
