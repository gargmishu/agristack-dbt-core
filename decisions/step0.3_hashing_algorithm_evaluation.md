# Hashing Algorithm Evaluation & Selection

**Framework Step:** Phase 0 · Step 0.3: Establish Zero-Trust Purge & Tokenization Protocols
**Related Documents:**
- [roadmap.md](../roadmap.md)
- [step0.2_data_model_design.md](./step0.2_data_model_design.md)

---

## 1. Goal

Evaluate and select the cryptographic hashing algorithm used for the in-memory tokenization of highly sensitive citizen Personally Identifiable Information (PII) such as Aadhaar numbers and phone numbers.

---

## 2. Constraints & Requirements

1. **Irreversibility (One-Way):** The system must not be able to reconstruct the cleartext PII from the tokenized hash, ensuring compliance with the zero-trust purge mandate.
2. **Deterministic Lookups:** The algorithm must consistently produce the exact same hash for the same citizen ID so that multi-channel interactions (e.g., WhatsApp today, USSD tomorrow) can be correlated to the same `application_governance_ledger` record without storing the cleartext ID.
3. **High Throughput:** As the Orchestrator sits behind real-time telecom gateways (IVR, USSD), the hashing must be extremely fast to handle large volumes.
4. **Low Latency:** The hashing must have minimal latency to prevent timeouts on synchronous carrier connections.
5. **Collision Resistance:** The risk of two different citizens generating the same hash must be cryptographically negligible.
6. **Cost:** The algorithm must be completely free or fit within a permanent free tier if utilizing external APIs, aligning with the project's strict budget constraints.
7. **Availability:** The algorithm should be readily available via standard open-source libraries or native runtime modules to minimize external dependencies.

---

## 3. Evaluated Options

### Option A – SHA‑256 with a secret prefix (not selected)
- **How it works:** Prefixes the identifier with a secret before hashing. This construction is not a substitute for a keyed message authentication code.
  ```python
  import hashlib

  token = hashlib.sha256((pepper + normalized_id).encode()).hexdigest()
  ```
- **Key Storage:** The secret pepper must be held in an approved secrets manager, not embedded in source or persisted with the identifier.
- **Availability:** Available in Python's standard library.
- **Cost:** No algorithm license fee; runtime and key-management costs depend on deployment.
- **Pros:**
  - Extremely fast and gives the same result every time.
- **Cons:**
  - **Cryptographic Weakness:** Plain concatenation does not provide the security guarantees of a standard keyed message authentication code and is vulnerable to construction errors. In particular, secret-prefix use with Merkle–Damgård hashes such as SHA-256 is susceptible to length-extension attacks. Use HMAC instead.

### Option B – HMAC‑SHA256 (recommended)
- **How it works:** The secret key is mixed inside the hash calculation using the HMAC construction, which is mathematically proven to stop length‑extension attacks. Instead of simple concatenation, HMAC formally nests the hashing mathematically: `Hash(Key XOR opad, Hash(Key XOR ipad, Message))`.
  ```python
  import hashlib
  import hmac

  token = hmac.new(pepper.encode(), normalized_id.encode(), hashlib.sha256).hexdigest()
  ```
- **Key Storage:** The secret pepper is held in an approved secrets manager and supplied to the perimeter service at runtime.
- **Availability:** Available in Python's standard library.
- **Cost:** No algorithm license fee; runtime and key-management costs depend on deployment.
- **Pros:**
  - **Deterministic:** The same identifier always produces the same token, enabling database index lookups.
  - **Immune to Length Extension Attacks:** Formally proven to be secure against length extension attacks, unlike simple concatenation.
  - **High Performance:** Sub-millisecond execution times appropriate for high-throughput ingress webhooks.
- **Cons:**
  - If the secret pepper key stored in your environment is compromised, the entire database can be brute-forced rapidly due to the speed of SHA-256.; protect and rotate the key and restrict token access.

### Option C – HMAC‑SHA3 (newer hash function)
- **How it works:** Same HMAC pattern but uses the newer SHA‑3 algorithm, which has a different internal design. A modern alternative using the same HMAC construction, but swapping the underlying engine from SHA-256 to the newer SHA-3 algorithm.
  ```python
  import hashlib
  import hmac

  token = hmac.new(pepper.encode(), normalized_id.encode(), hashlib.sha3_256).hexdigest()
  ```
- **Key Storage:** The secret pepper is stored in an approved secrets manager and supplied at runtime.
- **Availability:** Available in Python's standard library.
- **Cost:** No algorithm license fee; runtime and key-management costs depend on deployment.
- **Pros:**
  - **Mathematically Stronger:** SHA‑3 uses a "sponge" idea: it soaks up the input data, mixes it thoroughly, and then squeezes out a fixed‑size hash. This design makes SHA‑3 naturally immune to length‑extension attacks and gives it strong security guarantees.
- **Cons:**
  - **Performance**: Slightly slower than SHA‑256
  - **Ecosystem:** May need an extra library in older runtimes.

### Option D: Argon2id (Recommended for Non-Searchable Verification)
If you only need to verify an identifier at point‑of‑intake to see if it matches an exact target, but do not require database‑wide querying or indexing, use a memory‑hard Key Derivation Function (KDF) such as Argon2id (the profile winner of the Password Hashing Competition).
- **How it works:** It forces the CPU to use a configurable amount of memory and processing time, making mass parallelization on GPUs or ASICs economically unfeasible for attackers.
  ```python
  from argon2 import PasswordHasher

  encoded_hash = PasswordHasher().hash(normalized_id)
  ```
- **Availability:** Available through open-source Python libraries.
- **Cost:** The library may be open source, but compute costs depend on the selected memory and time parameters and workload.

- **Key Storage:** No secret key is stored; Argon2id generates a unique random salt for each hash, which is stored as part of the hash output.
- **Pros:**
  - Maximally secure against brute‑force attacks on constrained numeric input spaces. Raises the cost of offline guessing through a tunable memory and compute requirement, though it cannot eliminate guessing against low-entropy identifiers.
- **Cons:**
  - Highly CPU/memory intensive. It cannot be used cleanly for real‑time indexing/database joins across millions of records because it is intentionally slow.

### Option E: bcrypt (Recommended for Non-Searchable Verification)
Bcrypt is another memory‑hard password‑hashing algorithm widely used for secure verification without requiring searchable hashes.
- **How it works:** Bcrypt internally salts the input and applies a configurable cost factor (work factor) to increase computational effort, resisting GPU‑accelerated attacks.
  ```python
  import bcrypt

  encoded_hash = bcrypt.hashpw(normalized_id.encode(), bcrypt.gensalt())
  ```
- **Availability:** Available through open-source Python libraries.
- **Cost:** The library may be open source; compute costs depend on the configured work factor and workload.

- **Key Storage:** The bcrypt algorithm generates its own salt internally; no external secret key is stored.
- **Pros:**
  - Well‑tested, widely supported, and includes built‑in salt generation.
- **Cons:**
  - Still CPU intensive and not suitable for real‑time blind indexing; slower than simple hashing.

### Option F: AES-256-GCM (Symmetric Encryption)
A widely used symmetric encryption standard for securing data at rest or in transit.
- **How it works:** Reversibly encrypts the payload using a symmetric key.
  Standard cryptographic libraries and managed key services provide authenticated encryption.
- **Availability:** Available through standard cryptographic libraries and cloud key-management services.
- **Cost:** 100% Free for compute. However, if using a secure Key Management Service API (like AWS KMS or Google Cloud KMS) to inject the keys, it falls under their **Free Tier / Low Cost Tier** ($0.03 per 10,000 requests).
- **Key Storage:** The encryption key is stored in an approved secrets manager and supplied at runtime.
- **Pros:**
  - Extremely fast and secure.
- **Cons:**
  - **Reversible:** This violates the core zero‑trust mandate. If an attacker compromises the environment key and the database, all PII can be decrypted back to cleartext. We need a one‑way tokenization, not reversible encryption.

### Option G: BLAKE3 (Newer Cryptographic Hash)
A modern, extremely fast cryptographic hash function.
- **How it works:** Uses the BLAKE3 hashing algorithm.
  Use a supported BLAKE3 keyed-hash implementation; do not concatenate a key and identifier and treat an unkeyed hash as a MAC.
- **Availability:** Available through third-party open-source libraries.
- **Cost:** No algorithm license fee; library and runtime costs depend on deployment.
- **Key Storage:** The secret pepper is stored in an approved secrets manager and supplied at runtime.
- **Pros:**
  - BLAKE3 is significantly faster than SHA-256.
- **Cons:**
  - **Ecosystem Support:** It requires an additional library and offers no identified benefit over the standard-library HMAC-SHA-256 choice for this use case.

### Option H: Cloud Key Management Service (AWS KMS / Google Cloud KMS HMAC)
Externalized hashing where the HMAC key never enters the application environment.
- **How it works:** The application calls a Cloud API to generate the hash using a key permanently locked inside a Hardware Security Module (HSM).
  A cloud key-management service can calculate the HMAC while keeping the key in its hardware security module. Exact APIs and pricing depend on the selected provider.
- **Availability:** Provider-specific cloud APIs.
- **Cost:** Provider-specific request costs and quotas must be checked for the selected deployment.
- **Pros:**
  - **Key Isolation:** A correctly configured HSM-backed key-management service prevents direct key extraction from application memory. It does not prevent misuse of an authorized MAC operation or eliminate online guessing risks.
- **Cons:**
  - **Latency:** Adds network round‑trip latency to every single interaction, risking telecom gateway timeouts.
  - **Cost:** Fails the zero‑cost architecture mandate.

---

## 4. Selection Rationale

We selected **Option B: HMAC-SHA-256** using a high-entropy, explicitly configured secret key as the tokenization algorithm. Option A is plain SHA-256 with secret concatenation and is not the selected construction.

**Why it wins:**
1. **Deterministic Lookup:** It allows the Orchestrator to instantly recognize returning citizens across different channels with a direct database query (Blind Indexing), without ever persisting the cleartext ID.
2. **Performance:** It is computationally efficient; throughput and latency must be benchmarked on the selected deployment and carrier path.
3. **Zero-Trust Compliance:** It is fully one-way and irreversible, completely dropping the cleartext payload from the system while retaining business continuity.

**Security Mitigation:**
Because HMAC-SHA-256 executes rapidly, security depends on protecting the high-entropy secret pepper and controlling access to token values. Supply the key at runtime through an approved secrets manager; never commit it to source code or store it alongside the database.
