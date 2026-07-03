# Hashing Algorithm Evaluation & Selection

**Framework Step:** Phase 0 · Step 0.3: Establish Zero-Trust Purge & Tokenization Protocols  
**Related Documents:** 
- [zero_trust_tokenization.md](./zero_trust_tokenization.md)

---

## 1. Goal

Evaluate and select the cryptographic hashing algorithm used for the in-memory tokenization of highly sensitive citizen Personally Identifiable Information (PII) such as Aadhaar numbers and phone numbers. The chosen algorithm must ensure irreversibility, support deterministic cross-matching, and operate efficiently under high-volume transactional loads.

---

## 2. Constraints & Requirements

1. **Irreversibility (One-Way):** The system must not be able to reconstruct the cleartext PII from the tokenized hash, ensuring compliance with the zero-trust purge mandate.
2. **Deterministic Lookups:** The algorithm must consistently produce the exact same hash for the same citizen ID so that multi-channel interactions (e.g., WhatsApp today, USSD tomorrow) can be correlated to the same `application_governance_ledger` record without storing the cleartext ID.
3. **High Throughput / Low Latency:** As the Orchestrator sits behind real-time telecom gateways (IVR, USSD), the hashing must be extremely fast to prevent timeouts on synchronous carrier connections.
4. **Collision Resistance:** The risk of two different citizens generating the same hash must be cryptographically negligible.
5. **Cost:** The algorithm must be completely free or fit within a permanent free tier if utilizing external APIs, aligning with the project's strict budget constraints.
6. **Availability:** The algorithm should be readily available via standard open-source libraries or native runtime modules to minimize external dependencies.

---

## 3. Evaluated Alternatives

### Option 1: SHA-256 + Secret Pepper (Selected)
A cryptographic hash function belonging to the SHA-2 family.
- **Availability:** Available natively as a built-in library in Node.js (`crypto`).
- **Cost:** 100% Free. Because SHA-256 executes in microseconds, its CPU footprint is virtually zero. It can process thousands of hashes per second on a small, free-tier cloud instance without triggering forced hardware upgrades.
- **Pros:** 
  - **Speed:** Highly optimized and natively supported. Introduces microsecond-level latency.
  - **Deterministic:** When combined with a fixed, highly secure environment `pepper_salt`, it allows for deterministic cross-matching across sessions.
  - **Irreversible:** One-way hash.
- **Cons:** 
  - Fast execution makes it vulnerable to brute-force dictionary attacks *if* an attacker steals both the database hashes and the secret `pepper_salt`. 

### Option 2: bcrypt / Argon2
Adaptive password hashing algorithms deliberately designed to be computationally expensive (key stretching).
- **Availability:** Available as open-source third-party libraries (e.g., npm packages `bcrypt` or `argon2`).
- **Cost:** 100% Free (though compute overhead may increase cloud instance costs at high scale).
- **Pros:** 
  - Industry standard for storing user passwords; highly resistant to brute-force GPU attacks.
- **Cons:** 
  - **Performance Bottleneck:** The deliberate slowness (e.g., ~100ms+ per hash) would cause massive bottlenecks and potential gateway timeouts for high-volume concurrent IVR/USSD traffic.
  - **Non-Deterministic by Default:** Standard implementations generate a unique random salt per hash. To achieve deterministic lookups, the salt would have to be fixed, which undermines the primary design advantage of these algorithms.

### Option 3: AES-256-GCM (Symmetric Encryption)
A widely used symmetric encryption standard.
- **Availability:** Available natively in Node.js (`crypto`).
- **Cost:** 100% Free for compute. However, if using a secure Key Management Service API (like AWS KMS or Google Cloud KMS) to inject the keys, it falls under their **Free Tier / Low Cost Tier** ($0.03 per 10,000 requests).
- **Pros:** 
  - Extremely fast and secure.
- **Cons:** 
  - **Reversible:** This violates the core zero-trust mandate. If an attacker compromises the environment key and the database, all PII can be decrypted back to cleartext. We need a one-way tokenization, not reversible encryption.

### Option 4: SHA-3 / BLAKE3
Newer generation cryptographic hash functions.
- **Availability:** Available as third-party open-source libraries (e.g., npm `blake3`).
- **Cost:** 100% Free.
- **Pros:** 
  - BLAKE3 is significantly faster than SHA-256; SHA-3 is highly secure against theoretical attacks on SHA-2.
- **Cons:** 
  - **Ecosystem Support:** While fast, BLAKE3 often requires external dependencies or native WebAssembly bindings in Node.js. SHA-256 provides the optimal balance of speed, security, and zero-dependency support.

---

## 4. Selection Rationale

We selected **SHA-256 combined with a strict secret pepper** (`SHA-256(raw_id + pepper_salt)`) as the tokenization algorithm. 

**Why it wins:**
1. **Performance:** It handles thousands of concurrent requests per second without impacting the strict latency budgets of telecom USSD/IVR gateways.
2. **Determinism:** It allows the Orchestrator to instantly recognize returning citizens across different channels (by regenerating the same hash in-memory) without ever persisting the cleartext ID.
3. **Zero-Trust Compliance:** It is irreversible (unlike AES-256), completely dropping the cleartext payload from the system while retaining business continuity.

**Security Mitigation:**
Because SHA-256 is fast, the strength of this approach relies entirely on the `pepper_salt`. This pepper must be a high-entropy cryptographically random string (e.g., 64+ characters) injected directly into the application's volatile memory via a secure Secrets Manager (like AWS Secrets Manager or HashiCorp Vault). The pepper must **never** be committed to source code or stored alongside the database.
