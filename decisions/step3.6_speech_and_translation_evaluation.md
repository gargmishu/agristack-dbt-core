# Architectural Decision Record: Speech Perception & Vernacular Translation Engine Evaluation

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

The following technological approaches were considered:

- **Option 1: Bhashini API (National Language Translation Mission - MeitY)**  
  The Government of India's sovereign AI mission platform, developed in partnership with premier academic institutions (IIT Madras, AI4Bharat) and hosted on domestic National Informatics Centre (NIC) and sovereign cloud infrastructure.
- **Option 2: Commercial Multi-Cloud Speech APIs (Google Cloud Speech / AWS Transcribe / Azure Speech)**  
  Managed hyperscaler voice and translation services with global multi-language catalogs.
- **Option 3: Proprietary Frontier AI Endpoints (OpenAI Whisper API / Groq Proxy)**  
  Hosted transformer-based speech recognition endpoints offered by commercial AI providers.
- **Option 4: Self-Hosted Open-Source Models (Whisper Large-v3 / Meta MMS on Sovereign GPU Clusters)**  
  Deploying open-weights foundational speech models on self-managed, domestic GPU infrastructure.

---

## 4. Comparative Evaluation Matrix

| Architectural Dimension | Option 1: Bhashini API (Sovereign DPI) | Option 2: Commercial Hyperscalers (Google / AWS / Azure) | Option 3: Frontier Endpoints (OpenAI Whisper / Groq) | Option 4: Self-Hosted Open-Source (Whisper / MMS) |
| :--- | :--- | :--- | :--- | :--- |
| **Data Sovereignty & DPDP Compliance** | **Optimal:** 100% domestic sovereign infrastructure. Fully compliant with public sector data sovereignty mandates. | **High Risk:** Data routing through multinational commercial cloud regions; enterprise data processing agreements required. | **Critical Risk:** Violates data localization; voice streams traverse overseas inference clusters. | **Optimal:** Full control over infrastructure and telemetry data retention. |
| **8kHz Telephony Acoustic Robustness** | **Optimal:** Models explicitly fine-tuned on telephony datasets (ULCA project) across rural Indian calling conditions. | **Moderate:** Strong noise suppression, but optimized primarily for urban English/Hindi accents. | **Poor:** Trained predominantly on 16kHz internet audio; degrades significantly on compressed 8kHz GSM audio. | **Moderate:** Base models struggle on 8kHz without extensive domain fine-tuning. |
| **Agrarian & Land Tenure Lexicon** | **Optimal:** High token recognition for land administration terms (*Khasra, Khatauni, Patta, Bigha, Kist*). | **Poor:** Frequently mistranscribes localized revenue and land-tenure terminology. | **Poor:** Severe hallucination on vernacular administrative terms. | **Poor:** Requires custom dataset collection and fine-tuning. |
| **Tri-Modal Completeness (ASR+NMT+TTS)** | **Unified:** Single standardized API suite supporting all 22 Scheduled Indian languages across all three modalities. | **Fragmented:** Disjointed APIs with disparate pricing, language coverage gaps, and mismatched locale codes. | **Incomplete:** ASR available; separate models required for translation and speech synthesis. | **Complex:** Requires running and scaling three separate model architectures concurrently. |
| **National Scale Economics** | **Optimal:** Zero per-minute API licensing costs for public digital infrastructure; public good model. | **Prohibitive:** Per-minute pricing scales linearly to millions of dollars annually at national farmer volume. | **Prohibitive:** Per-minute or per-token usage fees in foreign currency. | **High Capex:** Substantial capital expenditure and ongoing operational cost for GPU cluster management. |
| **Vendor Independence** | **Open DPI Standard:** Aligned with national open digital ecosystem principles. | **Proprietary:** High vendor lock-in to proprietary cloud APIs. | **Proprietary:** Complete dependency on single commercial provider. | **Self-Managed:** High internal engineering burden for model updates and operations. |

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

### 5.2 Option 2: Commercial Multi-Cloud Speech APIs
- **Strengths:**
  - High global availability SLAs and mature operational tooling.
- **Weaknesses:**
  - Recurring consumption-based pricing creates severe financial overhead when serving 140+ million rural citizens.
  - Telephony performance outside standard urban Hindi and English drops substantially.
  - Inconsistent support across all 22 official languages, especially for regional TTS synthesis.

### 5.3 Option 3: Frontier Endpoints (OpenAI Whisper / Groq)
- **Strengths:**
  - Ultra-low latency inference via specialized hardware accelerators (e.g., Groq LPU).
- **Weaknesses:**
  - Incompatible with sovereign DPI security invariants; citizen voice streams cannot leave national borders.
  - Lack of integrated Indic NMT and regional voice TTS synthesis.

### 5.4 Option 4: Self-Hosted Open-Source Models
- **Strengths:**
  - Data remains completely within self-managed sovereign virtual private clouds.
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
