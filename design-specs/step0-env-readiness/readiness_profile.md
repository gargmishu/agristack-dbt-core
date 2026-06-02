# Step 0 · AI Readiness & Environment Profile

## 💻 1. Compute & Local Hardware Allocation

### Machine Profile: MacBook Pro (mishugarg-macbookpro4)
* **Configuration:** Apple Silicon Architecture (Unified Memory).
* **Rationale:** Leverages the Apple Silicon (M-series) architecture with Unified Memory Architecture (UMA) for efficient local Large Language Model execution, as both CPU and GPU cores access the same memory pool, minimizing data transfer latency.

### Local Intelligence Model Engine: Ollama Local Runtime Instance
* **Configuration:** Lightweight local background service.
* **Rationale:** Ensures total data privacy and compliance with data protection regulations (like India's DPDP Act) by processing data locally on the machine. Ollama acts as a local API server, preventing sensitive information from being transmitted over the public internet to third-party AI services.

### Selected Model Baseline: LLaMA-3-8B / DeepSeek-R1-8B (Quantized to 4-bit)
* **Configuration:** 8-Billion parameter models, compressed using 4-bit integer quantization (~4.7 GB active memory footprint).
* **Rationale:** Unquantized 16-bit models require roughly 16 GB of VRAM, which would overwhelm consumer hardware. 4-bit quantization compresses weights to simple integers, drastically reducing memory footprint from **~16 GB to ~4.7 GB**, with negligible loss in semantic comprehension, allowing it to easily fit on local hardware.

### VRAM Overhead Buffer: 3.5 GB Isolated for OS Background Processes
* **Configuration:** Memory ceiling protection allocation.
* **Rationale:** Since unified memory is shared with the host OS, failing to protect overhead causes system freezes etc. Restricting the AI runner's footprint ensures macOS, display engines, and local IDEs have enough headroom to operate smoothly without dropping processes.


## 🇮🇳 2. Sovereign India DPI Dependencies

### Language Block: Digital India BHASHINI API Framework (ASR/NMT/TTS)

*   **Configuration:** Suite of government-hosted APIs providing Automatic Speech Recognition (ASR), Neural Machine Translation (NMT), and Text-to-Speech (TTS) capabilities across various Indian languages.
*   **Rationale:** Enables building voice-first and multi-lingual interfaces, ensuring inclusivity and accessibility for users across India's diverse linguistic landscape. Using the BHASHINI framework ensures data remains within Indian sovereign boundaries, critical for DPI. The ASR handles raw dialect variations and filters out heavy agricultural background noise, the NMT standardizes the text, and the TTS returns a natural, spoken response to guarantee accessibility for non-literate operators.

### Core Registry: Federated AgriStack Architecture (FarmerID Verification)

*   **Configuration:** A federated system encompassing multiple registries for verifiable farmer and agricultural data:
    1.  **The Farmer Registry (FarmerID):** Assigns a unique, Aadhaar-verified electronic ID to each farmer.
    2.  **The Farmland Plot Registry:** Contains geo-referenced land maps and ownership/cultivation details.
    3.  **The Crop Sown Registry:** A seasonal digital ledger recording crops planted on specific plots.
*   **Rationale:** Establishes a multi-layered foundation of trust and identity for farmers and their activities.
    1.  **FarmerID Verification:** The pipeline queries the Farmer Registry to verify the caller is a legally recognized landholder.
    2.  **Land Verification:** The Farmland Plot Registry prevents fraud by allowing the pipeline to confirm the caller owns or cultivates the specific land parcels under discussion.
    3.  **Crop Verification:** The Crop Sown Registry enables cross-referencing farmer claims. For example, if a farmer reports a "cotton pest," the pipeline checks this registry to confirm cotton was indeed sown on their registered land for the current season, ensuring relevancy and accuracy.
    The federated nature allows states to manage their data while contributing to a national, verifiable system essential for targeted service delivery.

### Benefit Transfer Rail: Central PM-KISAN Ledger Core

*   **Configuration:** Centralized, immutable ledger system tracking Direct Benefit Transfers (DBT) under the PM-KISAN scheme.
*   **Rationale:** Ensures transparency, accountability, and efficient delivery of financial benefits directly to verified farmers' accounts. Acts as the single source of truth for all PM-KISAN transactions, minimizing leakages and delays.


## 🔒 3. Data Compliance Gates

### Data Privacy Standard: Digital Personal Data Protection (DPDP) Act, 2023

*   **Configuration:** Application design and data handling processes must strictly adhere to the principles and obligations outlined in the DPDP Act, 2023.
*   **Rationale:** Ensures legal compliance for processing digital personal data in India. Key principles include purpose limitation (processing data only for consented purposes like subsidy verification), data minimization, and accountability. This protects user privacy and avoids significant legal liabilities for the data fiduciary/processor.

### Logging Profile: Strict Zero-Retention Configuration

*   **Configuration:** Internal logger utilities are modified to filter and strip Personally Identifiable Information (PII) (like names, phone numbers, etc.) and conversational text from logs before they are written to disk. Data is processed in volatile memory (RAM) and cleared immediately after execution.
*   **Rationale:** Prevents accidental leakage of PII through log files. Standard logs often capture raw network request data, posing a breach risk if exposed. Zero-retention ensures sensitive data never persists on disk, mitigating compliance risks with the DPDP Act.

### Tokenization Rule: Identity inputs must convert to SHA-256 tokens at the ingestion boundary.

*   **Configuration:** All raw identity inputs (e.g., Aadhaar numbers, Phone numbers) are immediately hashed using the SHA-256 algorithm upon entering the application gateway. Only the resulting 64-character hexadecimal token is used for internal processing, API calls, and logging.
*   **Rationale:** Enforces "Privacy by Design" by replacing sensitive identifiers with irreversible 64-character hexadecimal tokens right at the gateway and throughout the application lifecycle. SHA-256 is a one-way cryptographic function, making it computationally infeasible to reverse the hash back to the original identifier. This ensures that even if internal data or logs are compromised, the actual PII remains secure, as only non-linkable tokens are exposed, maintaining DPDP Act compliance.


```
[Raw Identity Input] ──> ( Ingestion Boundary: SHA-256 Hash ) ──> [Deterministic Token]
 (e.g., Aadhaar String)                                           (Safe for App Processing & Logs)

```
