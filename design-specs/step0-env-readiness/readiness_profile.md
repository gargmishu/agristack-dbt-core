# Step 0 · AI Readiness & Environment Profile

## 💻 1. Compute & Sovereign Hardware Allocation

### Compute Profile: Sovereign Unified Memory Node / State Cloud Instance
* **Configuration:** Unified Memory Compute Architecture (UMA) or Sovereign On-Premise GPU/NPU Node.
* **Rationale:** Leverages unified or localized memory architectures for low-latency Small Language Model (SLM) execution, minimizing memory-transfer overhead and keeping inference within sovereign compute boundaries.

### Local Intelligence Model Engine: Sovereign On-Premise SLM Inference Runtime
* **Configuration:** Isolated local or state-cloud inference service.
* **Rationale:** Ensures data privacy and compliance with India's DPDP Act 2023 by processing sanitized text within sovereign compute boundaries without transmitting citizen inputs over the public internet to commercial third-party AI APIs.

### Selected Model Baseline: Sovereign 8B-Class SLM (Quantized to 4-bit)
* **Configuration:** An 8-billion-parameter class model using 4-bit quantization; model weights occupy roughly 4–5 GB, with additional memory reserved for runtime state and inference context.
* **Rationale:** Lower-precision quantization reduces memory footprint compared with 16-bit weights while preserving deterministic structured JSON entity extraction. Task accuracy, latency, and peak memory are benchmarked prior to production rollout.

### Memory Overhead Buffer: Reserve 3.5 GB for Host OS & Gateway Processes
* **Configuration:** Memory ceiling protection allocation.
* **Rationale:** Restricting the SLM inference runtime's memory footprint guarantees that the host operating system, ASGI gateway workers, and perimeter security firewalls maintain deterministic headroom under peak concurrency.


## 🇮🇳 2. Sovereign India DPI Dependencies

### Language Block: Digital India BHASHINI API Framework (ASR/NMT/TTS)

*   **Configuration:** Suite of government-hosted APIs providing Automatic Speech Recognition (ASR), Neural Machine Translation (NMT), and Text-to-Speech (TTS) capabilities across 22 Scheduled Indian languages.
*   **Rationale:** Enables voice-first and multilingual interfaces across India's linguistic landscape (`8000 Hz` narrowband PSTN/GSM and `16000 Hz` wideband PCM). Confirm the selected service endpoint's data-residency, retention, and processing terms before sending citizen content.

### Core Land & Crop Registries: Federated AgriStack & Digital Crop Survey (DCS)

*   **Configuration:** A federated system encompassing separated registries for verifiable farmer, cadastral land, and physical crop data:
    1.  **The Farmer & Identity Registry:** Provides a registry identifier and verification status through its authorized interface.
    2.  **The Farmland Plot Registry (Cadastral Land Registry):** Contains geo-referenced cadastral land maps and survey/Khasra ownership details.
    3.  **The Crop Sown & Satellite Verification Registry:** Combines Digital Crop Survey (DCS) seasonal declarations with multi-spectral satellite stress indices (ALU/AMED plot polygons).
*   **Rationale:** Establishes separated, independently auditable verification boundaries for identity, legal land ownership, and physical crop cultivation across state registries.

### Policy Metadata Block: Data DHARA (NMDS 2.0) Model Context Protocol (`/mcp`) Server

*   **Configuration:** National Metadata Dataset Service (Data DHARA) exposing MDDS/LGD-harmonized scheme notifications and calamity tables via JSON-RPC 2.0 Streamable HTTP (`POST /mcp` tools: `search_datasets`, `get_metadata`, `get_table`).
*   **Rationale:** Enables deterministic Gate 3 verification that the claimant's district, crop, and season are covered by an active government calamity notification or subsidy rule without hardcoding scheme tables in application code.

### Beneficiary & Case Management Block: OpenSPP / OpenG2P Social Protection Registry

*   **Configuration:** Digital Public Good (DPG) beneficiary registry and caseworker escalation queue (`/v1/social/eligibility` and `/v1/social/cases`).
*   **Rationale:** Verifies beneficiary enrollment across social protection schemes and stages human-in-the-loop review tickets (`ROUTE_FOR_MANUAL_REVIEW`) when extraction confidence is below `0.85` or registry discrepancies require officer adjudication.

### Benefit Transfer Rail: Authorized Scheme Payment Interface (NPCI APBS / PFMS & G2P Connect v1.0.0)

*   **Configuration:** An authorized scheme-specific payment interface supporting asynchronous treasury clearing and signed G2P Connect v1.0.0 settlement envelopes (`disburse`, `on-disburse`).
*   **Rationale:** Payment eligibility, authorization, settlement status, and reconciliation are confirmed through deterministic state transitions (`PENDING` $\rightarrow$ `INITIATED` $\rightarrow$ `SUCCESS`/`FAILED`) and cryptographic callback verification.


## 🔒 3. Data Compliance Gates

### Data Privacy Standard: Digital Personal Data Protection (DPDP) Act, 2023

*   **Configuration:** Application design and data handling processes must strictly adhere to the principles and obligations outlined in the DPDP Act, 2023.
*   **Rationale:** Ensures legal compliance for processing digital personal data in India. Key principles include purpose limitation (processing data only for consented purposes like subsidy verification), data minimization, and accountability. This protects user privacy and avoids significant legal liabilities for the data fiduciary/processor.

### Logging Profile: Strict Zero-Retention Configuration

*   **Configuration:** Internal logger utilities are modified to filter and strip Personally Identifiable Information (PII) (like names, phone numbers, etc.) and conversational text from logs before they are written to disk. Data is processed in volatile memory (RAM) and cleared immediately after execution.
*   **Rationale:** Prevents accidental leakage of PII through log files. Standard logs often capture raw network request data, posing a breach risk if exposed. Zero-retention ensures sensitive data never persists on disk, mitigating compliance risks with the DPDP Act.

### Tokenization Rule: Approved identity inputs must convert to HMAC-SHA-256 tokens at the Layer 2 perimeter.

*   **Configuration:** The Layer 2 perimeter applies HMAC-SHA-256 using a managed secret pepper and emits a 64-character hexadecimal token. Raw Aadhaar must not be directly HMAC'd; use an authorized UIDAI-issued pseudonymous identifier where required by the verification flow.
*   **Rationale:** Pseudonymization reduces exposure in downstream processing, logs, and storage. HMAC tokens remain sensitive and linkable; key protection, access control, retention limits, and free-text redaction remain mandatory.


```
[Approved Identity Input] ──> (Layer 2: HMAC-SHA-256) ──> [Pseudonymous Token]
 (e.g., phone or authorized UIDAI token)                   (Sensitive; access-controlled)

```
