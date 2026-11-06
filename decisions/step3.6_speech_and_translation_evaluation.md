# Step 3.6: Speech Perception & Vernacular Translation Engine Evaluation

> Sequence authority: [roadmap.md](../roadmap.md).

## 1. Context & Architectural Challenge

### 1.1 The Agrarian Intake Landscape
The Citizen Welfare Orchestrator ingests claims and inquiries across diverse communication modalities, including automated voice telephony (Interactive Voice Response - IVR) and messaging platforms (WhatsApp voice notes).

Serving India's agricultural community introduces distinct perception challenges:
- **Linguistic Diversity:** Beneficiaries communicate across 22 Scheduled Indian languages and hundreds of regional dialects (e.g., Bhojpuri, Maithili, Awadhi, Bundeli, Haryanvi, Malwi).
- **Acoustic Degradation:** Rural telephony voice traffic is transmitted over lossy, compressed 8kHz GSM/PSTN cellular networks via basic feature phones, often characterized by background noise (tractors, cattle, outdoor ambient noise).
- **Domain-Specific Vocabulary:** Citizen queries frequently combine vernacular dialects with hyper-localized cadastral and land-tenure terminology (*Khasra, Khatauni, Patta, Bigha, Guntha, Murabba, Kharif, Rabi, Zaid, Kist, Girdawari*).
- **Code-Mixing:** Spoken inputs frequently mix regional languages with Hindi or English (e.g., Hinglish, Tanglish).

### 1.2 The Tri-Modal Perception Requirement
Citizen voice interactions require an end-to-end tri-modal conversational pipeline:
1. **Automated Speech Recognition (ASR):** Transcribe lossy acoustic audio streams into vernacular text.
2. **Neural Machine Translation (NMT):** Translate vernacular dialectal text into standardized administrative language for domain entity extraction.
3. **Text-to-Speech Synthesis (TTS):** Convert adjudicated decisions and clarification prompts back into natural-sounding vernacular speech for citizen playback.

### 1.3 Architectural Separation: Layer 1 Real-Time Telephony Runtime vs. Layer 3 Speech & Translation Model APIs
In national Digital Public Infrastructure (DPI) voice architectures, a frequent design misconception is conflating the **Layer 3 Speech & Translation Model Catalog (`Bhashini`)** with the **Layer 1 Telephony Edge & Real-Time Voice Agent Platform** (such as the open-source **`VoicEra`** Digital Public Good stack incubated by EkStep Foundation and stewarded by the Centre for Open Societal Systems — COSS). They operate at two distinct architectural tiers and are designed to compose together:

| Architectural Dimension | Layer 3 Foundational Speech & Translation Model Catalog (`Bhashini`) | Layer 1 Telephony Edge & Real-Time Voice Agent Platform (Self-Hosted `8kHz` Voice Runtime / `VoicEra`) |
| :--- | :--- | :--- |
| **Architectural Role** | **Stateless AI Speech & Language Model Catalog (`ULCA` / `DIBD`)** | **Full-Stack Telephony Edge, Real-Time Streaming Orchestrator & Session Store** |
| **Primary Responsibilities** | Exposes raw REST/WebSocket inference endpoints for **ASR** (`Audio -> Text`), **NMT** (`Text -> Text`), **TTS** (`Text -> Audio`), and **OCR** across 22 Scheduled Indian languages. | Terminates **SIP / PSTN (`8kHz` GSM)** phone calls and WebSockets, executes real-time bidirectional audio streaming, **Voice Activity Detection (`VAD`)**, turn-taking, and **barge-in** interruption handling, and persists `.wav` recordings and transcripts on sovereign storage at **`<₹1/minute`**. |
| **What It Does *Not* Do Alone** | Does **not** answer phone calls, manage SIP trunks, detect when a farmer pauses or interrupts mid-sentence, or store session recordings. | Does **not** train its own foundational Indic speech/translation models; instead, it invokes **Bhashini** (or pluggable local ASR/TTS models) as its speech perception backend. |
| **Mapping to Zero-Trust 4-Layer Architecture** | **Layer 3 Perception Adapter** (*Speech & Translation Service*). | **Layer 1 Carrier Edge Ingress** (*IVR Telephony Edge Connector* & *IVR Voice Ingress Contract* supporting `8000 Hz` narrowband and `16000 Hz` wideband audio). |

```text
  ┌────────────────────────────────────────────────────────────────────────────┐
  │ 1. LAYER 1: REAL-TIME TELEPHONY EDGE & VOICE RUNTIME (VoicEra / SIP Edge)  │
  │    - Answers 8kHz PSTN / feature-phone call (<₹1/min operating benchmark)  │
  │    - Manages real-time audio frames, VAD, turn-taking & barge-in           │
  │    - Emits validated IVR Voice Ingress Contract (8000 Hz / 16000 Hz PCM)   │
  └─────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
  ┌────────────────────────────────────────────────────────────────────────────┐
  │ 2. LAYER 3: SPEECH & LANGUAGE MODEL APIs (Bhashini ASR / NMT / TTS)        │
  │    - Stateless vernacular speech transcription (ASR)                       │
  │    - Dialect-to-canonical translation (NMT) & regional voice synthesis     │
  └─────────────────────────────────────┬──────────────────────────────────────┘
                                        │
                                        ▼
  ┌────────────────────────────────────────────────────────────────────────────┐
  │ 3. LAYERS 2–4: ZERO-TRUST SECURITY, 3-GATE GOVERNANCE & G2P ENGINE         │
  │    - Layer 2: RAM-only SHA-256 HMAC PII tokenization & prompt firewall     │
  │    - Layer 3 (Gate 1): Constrained SLM agricultural entity extraction      │
  │    - Layer 4 (Gates 2 & 3): Deterministic registry check & G2P payout      │
  └────────────────────────────────────────────────────────────────────────────┘
```

### 1.4 Architectural Decision: Loosely Coupled Webhook Boundary vs. Direct Embedding of `VoicEra`
* **Context:** We evaluated whether the core orchestration repository should directly import or bundle the open-source **`VoicEra`** real-time telephony stack inside its application runtime, or integrate with `VoicEra` across a clean Layer 1 $\rightarrow$ Layer 2 HTTP webhook boundary (`POST /v1/webhooks/ivr`).
* **Decision:** **Maintain a loosely coupled HTTP webhook contract (`POST /v1/webhooks/ivr` accepting `8000 Hz` narrowband and `16000 Hz` wideband audio payloads) rather than embedding `VoicEra` inside the core repository.**
* **Rationale:**
  1. **Separation of Stateful Telecom Infrastructure from Stateless Governance:** `VoicEra` is a multi-container real-time media and telephony runtime (incorporating SIP/PSTN call termination, WebSocket audio frame streaming, Voice Activity Detection, barge-in handling, and object storage for `.wav` recordings). Bundling stateful telecom infrastructure inside the Zero-Trust governance engine would bloat container dependencies and violate the 4-layer separation of concerns.
  2. **Multi-Channel & Multi-Partner Portability:** Keeping the integration boundary at the *IVR Voice Ingress Contract* (`POST /v1/webhooks/ivr`) allows state departments and ecosystem integrators to plug in `VoicEra`, state NIC IVR SIP gateways, or existing field voice stacks without modifying Layers 2–4.
  3. **Independent Scaling & Fault Isolation:** Real-time `8kHz` audio streaming and VAD require persistent long-lived connections, whereas Layer 2–4 claim tokenization and 3-Gate eligibility adjudication are stateless transactional operations. Decoupling them via signed webhooks allows telephony edge nodes and governance workers to scale and recover independently.

---

## 2. Evaluation Criteria

Candidate technologies were evaluated against five core criteria:

| Criterion | Architectural Rationale |
| :--- | :--- |
| **1. Sovereign Data Residency & DPDP Act Compliance** | Acoustic voice recordings contain biometric and personal data. Under India's **Digital Personal Data Protection (DPDP) Act 2023** and National Digital Public Infrastructure (DPI) guidelines, citizen voice telemetry must not traverse foreign cloud infrastructure. |
| **2. Acoustic Telephony Performance (8kHz / Lossy Audio)** | High accuracy on 8kHz narrowband telephony audio captured via low-cost mobile handsets, rather than 16kHz wideband studio recordings. |
| **3. Agrarian & Land Records Lexicon Accuracy** | Reliable transcription and translation of regional cadastral terminology without phonetic hallucination. |
| **4. Tri-Modal Pipeline Integration (ASR + NMT + TTS)** | Standardized, low-latency API coordination across all three perception stages for Indic languages. |
| **5. Scale Economics & DPI Neutrality** | Sustainable operating cost model for national scale (140+ million PM-KISAN beneficiary households) without commercial vendor lock-in. |

---

## 3. Candidate Options Evaluated

The following three mutually exclusive technological approaches were considered:

- **Option 1: Bhashini API (National Language Translation Mission - MeitY)**
  The Government of India's sovereign AI mission platform, developed in partnership with premier academic institutions (IIT Madras, AI4Bharat) and hosted on domestic National Informatics Centre (NIC) and sovereign cloud infrastructure.
- **Option 2: Commercial Cloud & Proprietary AI Speech APIs (Google Cloud Speech / AWS Transcribe / Azure Speech / OpenAI Whisper API / Groq)**
  Managed speech recognition, machine translation, and voice synthesis endpoints offered by commercial cloud hyperscalers and proprietary foundation-model providers.
- **Option 3: Self-Hosted Open-Weights Models on Sovereign GPU Clusters (Whisper Large-v3 / Meta MMS / AI4Bharat IndicConformer)**
  Deploying open-weights foundational speech and translation models on self-managed, domestic GPU infrastructure.

---

## 4. Comparative Evaluation Matrix

| Architectural Dimension | Option 1: Bhashini API (Sovereign DPI) | Option 2: Commercial Cloud & AI APIs (Google / AWS / Azure / OpenAI / Groq) | Option 3: Self-Hosted Open-Weights (Whisper / MMS / IndicConformer) |
| :--- | :--- | :--- | :--- |
| **Data Sovereignty & DPDP Compliance** | **Optimal:** 100% domestic sovereign infrastructure. Fully compliant with public sector data sovereignty mandates. | **High / Critical Risk:** Requires routing citizen audio through commercial third-party cloud regions or cross-border inference clusters; incompatible with strict sovereign DPI data residency. | **Optimal:** Full control over domestic infrastructure and telemetry data retention. |
| **8kHz Telephony Acoustic Robustness** | **Optimal:** Models explicitly fine-tuned on telephony datasets (ULCA project) across rural Indian calling conditions. | **Poor to Moderate:** Hyperscaler suites target urban English/Hindi accents; frontier Whisper endpoints are trained predominantly on 16kHz wideband internet audio and degrade on compressed 8kHz GSM audio. | **Moderate:** Base open-weights models struggle on 8kHz rural telephony without extensive domain fine-tuning. |
| **Agrarian & Land Tenure Lexicon** | **Optimal:** High token recognition for land administration terms (*Khasra, Khatauni, Patta, Bigha, Kist*). | **Poor:** Frequently mistranscribes or hallucinates on localized vernacular revenue and land-tenure terminology. | **Poor (Out-of-the-Box):** Requires custom dataset curation and domain fine-tuning unless paired with specialized Indic checkpoints. |
| **Tri-Modal Completeness (ASR+NMT+TTS)** | **Unified:** Single standardized API suite supporting all 22 Scheduled Indian languages across all three modalities. | **Fragmented / Incomplete:** Hyperscalers split ASR, NMT, and TTS across disparate APIs and pricing tiers; frontier ASR endpoints (Whisper/Groq) lack integrated Indic NMT and regional TTS synthesis altogether. | **Complex:** Requires deploying, orchestrating, and scaling three separate model architectures concurrently. |
| **National Scale Economics** | **Optimal:** Zero per-minute API licensing costs for public digital infrastructure; public good model. | **Prohibitive:** Per-minute or per-token commercial billing (often denominated in foreign currency) scales linearly to millions of dollars annually at national farmer volume. | **High Capex:** Substantial capital expenditure and ongoing operational cost for sovereign GPU cluster management. |
| **Vendor Independence** | **Open DPI Standard:** Aligned with national open digital ecosystem principles. | **Proprietary Lock-In:** High coupling to proprietary commercial cloud SDKs, rate limits, and vendor pricing. | **Self-Managed:** Zero vendor lock-in, but high internal ML engineering burden for model maintenance and operations. |

---

## 5. Detailed Trade-Off Analysis

### 5.1 Option 1: Bhashini API (National Language Translation Mission)
- **Strengths:**
  - **Sovereign Alignment:** Purpose-built for Government of India citizen engagement, eliminating compliance risks under the DPDP Act 2023.
  - **Dialectal Depth:** Direct support for major Indic linguistic families (Indo-Aryan, Dravidian, Austroasiatic, Tibeto-Burman) with rural acoustic grounding.
  - **Domain Familiarity:** Research backing by AI4Bharat ensures continuous training on Indian administrative and agricultural corpora.
  - **Operational Simplicity:** Provides a unified REST/mTLS interface for ASR, NMT, and TTS, minimizing orchestration overhead.
- **Weaknesses:**
  - Dependent on national DPI service availability; requires robust client-side retry policies and fail-closed circuit breaking.

### 5.2 Option 2: Commercial Cloud & Proprietary AI Speech APIs (Hyperscalers & Frontier Endpoints)
- **Strengths:**
  - High global availability SLAs, mature enterprise tooling (hyperscalers), and low-latency hardware acceleration (e.g., LPU inference proxies).
- **Weaknesses:**
  - **Sovereignty & Compliance Risks:** Routing biometric citizen voice streams to foreign-hosted inference endpoints violates national DPI localization mandates, while even domestic hyperscaler regions require complex commercial data processing agreements.
  - **Prohibitive Unit Economics:** Recurring consumption-based per-minute/per-token pricing creates severe financial overhead when serving 140+ million rural beneficiary households.
  - **Acoustic & Lexicon Gaps:** Poor out-of-the-box accuracy on 8kHz rural telephony and localized cadastral vocabulary (*Khasra, Khatauni, Patta*).
  - **Modality Fragmentation:** Frontier ASR endpoints lack integrated Indic NMT and regional voice TTS synthesis, while hyperscaler offerings suffer from inconsistent coverage across all 22 Scheduled Indian languages.

### 5.3 Option 3: Self-Hosted Open-Weights Models on Sovereign GPU Clusters
- **Strengths:**
  - Data remains completely within self-managed sovereign virtual private clouds with full architectural control.
- **Weaknesses:**
  - Massive capital expenditure required for provisioning and maintaining enterprise GPU clusters (NVIDIA A100/H100) capable of handling peak daytime IVR call concurrency.
  - Requires dedicated machine learning engineering staff to maintain acoustic models, fine-tuning pipelines, and multi-lingual voice synthesis engines.

---

## 6. Architectural Verdict & Production Invariants

### 6.1 Final Decision
**Bhashini API is selected as the primary, authoritative speech and vernacular translation engine for production deployments.**

The combination of strict DPDP Act compliance, purpose-trained telephony acoustic models, deep coverage of agrarian vernacular terminology, and unified tri-modal capabilities makes Bhashini uniquely suited for national agricultural welfare delivery.

### 6.2 Architectural Invariants

1. **Production Sovereign Boundary Invariant:**
   In production environments, all live speech transcription, machine translation, and voice synthesis must route exclusively through the sovereign Bhashini gateway. Routing citizen audio streams to commercial foreign cloud providers is strictly prohibited.
2. **Fail-Closed Resiliency Invariant:**
   If the Bhashini service experiences transient network unavailability or cluster outages, the system must fail closed—emitting structured service unavailable errors and routing affected claims to manual caseworker review rather than silently dropping queries or producing corrupted intake contracts.
3. **Offline Mock Simulation Invariant (Development & Automated Testing):**
   To facilitate rapid, zero-dependency local development and automated CI/CD testing without network latency or external service coupling, the perception adapter provides deterministic local mock fixtures that simulate vernacular transcription, translation, and TTS generation.
4. **Composable 8kHz Self-Hosted Telephony Edge & Acoustic Profile Invariant:**
   At the Layer 1 telephony perimeter, the IVR voice ingress contract natively validates both **8kHz narrowband PSTN/GSM telephony (`8000 Hz` default)** and **16kHz wideband PCM (`16000 Hz`)** audio streams. This allows state deployments to pair sovereign Bhashini speech perception at Layer 3 with self-hosted, open-source real-time voice telephony gateways (Apache 2.0 Digital Public Good voice runtimes) at Layer 1, achieving `<₹1/min` full-stack telephony operating economics and sovereign call-media custody without coupling core Layer 4 eligibility governance to any single carrier or media runtime.

