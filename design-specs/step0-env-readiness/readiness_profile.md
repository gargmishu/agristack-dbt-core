# Step 0 · AI Readiness & Environment Profile

## 💻 1. Compute & Local Hardware Allocation

### Machine Profile: Apple Silicon development workstation
* **Configuration:** Apple Silicon Architecture (Unified Memory).
* **Rationale:** Leverages the Apple Silicon (M-series) architecture with Unified Memory Architecture (UMA) for efficient local Large Language Model execution, as both CPU and GPU cores access the same memory pool, minimizing data transfer latency.

### Local Intelligence Model Engine: Ollama Local Runtime Instance
* **Configuration:** Lightweight local background service.
* **Rationale:** Ensures total data privacy and compliance with data protection regulations (like India's DPDP Act) by processing data locally on the machine. Ollama acts as a local API server, preventing sensitive information from being transmitted over the public internet to third-party AI services.

### Selected Model Baseline: Local 8B-Class SLM (Quantized to 4-bit)
* **Configuration:** An 8-billion-parameter class model using 4-bit quantization; model weights may occupy roughly 4–5 GB, with additional memory required for runtime state and inference context.
* **Rationale:** Lower-precision quantization reduces memory use compared with 16-bit weights, but may affect output quality. Measure task accuracy, latency, and peak memory on the target workstation before selecting a production model.

### Unified Memory Overhead Buffer: Reserve 3.5 GB for OS Background Processes
* **Configuration:** Memory ceiling protection allocation.
* **Rationale:** Since unified memory is shared with the host OS, failing to protect overhead causes system freezes etc. Restricting the AI runner's footprint ensures macOS, display engines, and local IDEs have enough headroom to operate smoothly without dropping processes.


## 🇮🇳 2. Sovereign India DPI Dependencies

### Language Block: Digital India BHASHINI API Framework (ASR/NMT/TTS)

*   **Configuration:** Suite of government-hosted APIs providing Automatic Speech Recognition (ASR), Neural Machine Translation (NMT), and Text-to-Speech (TTS) capabilities across various Indian languages.
*   **Rationale:** Enables voice-first and multilingual interfaces across India's linguistic landscape. Confirm the selected service endpoint's data-residency, retention, and processing terms before sending citizen content. Recognition quality in dialects and agricultural noise, translation quality, and speech intelligibility must be evaluated for the pilot.

### Core Registry: Federated AgriStack Architecture (FarmerID Verification)

*   **Configuration:** A federated system encompassing multiple registries for verifiable farmer and agricultural data:
    1.  **The Farmer Registry:** Provides a registry identifier and verification status through its authorized interface.
    2.  **The Farmland Plot Registry:** Contains geo-referenced land maps and ownership/cultivation details.
    3.  **The Crop Sown Registry:** A seasonal digital ledger recording crops planted on specific plots.
*   **Rationale:** Establishes a multi-layered foundation of trust and identity for farmers and their activities.
    1.  **Farmer Registry Verification:** The pipeline queries the authorized registry to verify the caller's registered status; a registry match alone must not be treated as proof of legal land ownership.
    2.  **Land Verification:** The Farmland Plot Registry prevents fraud by allowing the pipeline to confirm the caller owns or cultivates the specific land parcels under discussion.
    3.  **Crop Verification:** The Crop Sown Registry enables cross-referencing farmer claims. For example, if a farmer reports a "cotton pest," the pipeline checks this registry to confirm cotton was indeed sown on their registered land for the current season, ensuring relevancy and accuracy.
    The federated nature allows states to manage their data while contributing to a national, verifiable system essential for targeted service delivery.

### Benefit Transfer Rail: Authorized Scheme Payment Interface

*   **Configuration:** An authorized scheme-specific payment interface, selected with the participating department and treasury.
*   **Rationale:** Payment eligibility, authorization, settlement status, and reconciliation must be confirmed through the actual scheme and payment-rail contracts. Do not assume a single central ledger is available or authoritative for every program.


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
