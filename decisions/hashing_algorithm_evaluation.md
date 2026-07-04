# Hashing Algorithm Evaluation & Selection

**Framework Step:** Phase 0 · Step 0.3: Establish Zero-Trust Purge & Tokenization Protocols  
**Related Documents:** 
- [roadmap.md](../roadmap.md)
- [flowchart.md](../design-specs/step3-guardrails/flowchart.md)
- [data_model_design.md](./data_model_design.md)

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

### Option A – SHA‑256 + Secret Pepper (simple concatenation)
- **How it works:** Appends or prepends a secret “pepper” string to the ID and run the SHA‑256 hash.
  ```javascript
  const crypto = require('crypto');
  const token = crypto.createHash('sha256')
                      .update('+919876543210' + process.env.PEPPER_KEY)
                      .digest('hex');
  ```
- **Key Storage:** The secret pepper lives in an environment variable (`process.env.PEPPER_KEY`).
- **Availability:** Available natively as a built-in library in Node.js (`crypto`).
- **Cost:** 100% Free. Because it executes in microseconds, its CPU footprint is virtually zero.
- **Pros:** 
  - Extremely fast and gives the same result every time.
- **Cons:** 
  - **Cryptographic Weakness:** A length‑extension attack lets an attacker take a known hash of `message + secret` and append extra data to produce a valid hash for `message + secret + extra` without knowing the secret. For example, if the hash was computed over `+919876543210` with a secret pepper, an attacker could add `+1234` and generate a new hash that still verifies, breaking security. HMAC (Option B) prevents this.

### Option B – HMAC‑SHA256 (recommended)
- **How it works:** The secret key is mixed inside the hash calculation using the HMAC construction, which is mathematically proven to stop length‑extension attacks. Instead of simple concatenation, HMAC formally nests the hashing mathematically: `Hash(Key XOR opad, Hash(Key XOR ipad, Message))`.
  ```javascript
  const crypto = require('crypto');
  const token = crypto.createHmac('sha256', process.env.PEPPER_KEY)
                      .update('+919876543210')
                      .digest('hex');
  ```
- **Key Storage:** The secret pepper is stored in an environment variable (`process.env.PEPPER_KEY`).
- **Availability:** Available natively as a built-in library in Node.js (`crypto`).
- **Cost:** 100% Free. Because it executes in microseconds, its CPU footprint is virtually zero.
- **Pros:** 
  - **Deterministic:** The same identifier always produces the same token, enabling database index lookups.
  - **Immune to Length Extension Attacks:** Formally proven to be secure against length extension attacks, unlike simple concatenation.
  - **High Performance:** Sub-millisecond execution times appropriate for high-throughput ingress webhooks.
- **Cons:** 
  - If the secret pepper key stored in your environment is compromised, the entire database can be brute-forced rapidly due to the speed of SHA-256.

### Option C – HMAC‑SHA3 (newer hash function)
- **How it works:** Same HMAC pattern but uses the newer SHA‑3 algorithm, which has a different internal design. A modern alternative using the same HMAC construction, but swapping the underlying engine from SHA-256 to the newer SHA-3 algorithm.
  ```javascript
  const crypto = require('crypto');
  const token = crypto.createHmac('sha3-256', process.env.PEPPER_KEY)
                      .update('+919876543210')
                      .digest('hex');
  ```
- **Key Storage:** The secret pepper is stored in an environment variable (`process.env.PEPPER_KEY`).
- **Availability:** Often requires third-party libraries depending on the exact runtime, though some modern environments support it natively.
- **Cost:** 100% Free.
- **Pros:** 
  - **Mathematically Stronger:** SHA‑3 uses a "sponge" idea: it soaks up the input data, mixes it thoroughly, and then squeezes out a fixed‑size hash. This design makes SHA‑3 naturally immune to length‑extension attacks and gives it strong security guarantees.
- **Cons:** 
  - **Performance**: Slightly slower than SHA‑256
  - **Ecosystem:** May need an extra library in older runtimes.

### Option D: Argon2id (Recommended for Non-Searchable Verification)
If you only need to verify an identifier at point‑of‑intake to see if it matches an exact target, but do not require database‑wide querying or indexing, use a memory‑hard Key Derivation Function (KDF) such as Argon2id (the profile winner of the Password Hashing Competition).
- **How it works:** It forces the CPU to use a configurable amount of memory and processing time, making mass parallelization on GPUs or ASICs economically unfeasible for attackers.
  ```javascript
  const argon2 = require('argon2');
  // Generates a unique salt automatically, preventing DB searches
  const hash = await argon2.hash('+919876543210'); 
  ```
- **Availability:** Available as open‑source third‑party libraries (e.g., npm package `argon2`).
- **Cost:** 100% Free for the software, but the heavy compute overhead will mandate upgrading cloud hardware under load.

- **Key Storage:** No secret key is stored; Argon2id generates a unique random salt for each hash, which is stored as part of the hash output.
- **Pros:**
  - Maximally secure against brute‑force attacks on constrained numeric input spaces.
- **Cons:**
  - Highly CPU/memory intensive. It cannot be used cleanly for real‑time indexing/database joins across millions of records because it is intentionally slow.

### Option E: bcrypt (Recommended for Non-Searchable Verification)
Bcrypt is another memory‑hard password‑hashing algorithm widely used for secure verification without requiring searchable hashes.
- **How it works:** Bcrypt internally salts the input and applies a configurable cost factor (work factor) to increase computational effort, resisting GPU‑accelerated attacks.
  ```javascript
  const bcrypt = require('bcrypt');
  const saltRounds = 12; // work factor
  const hash = await bcrypt.hash('+919876543210', saltRounds);
  ```
- **Availability:** Available via npm package `bcrypt` (or `bcryptjs` for pure JavaScript).
- **Cost:** 100% Free for the software.

- **Key Storage:** The bcrypt algorithm generates its own salt internally; no external secret key is stored.
- **Pros:**
  - Well‑tested, widely supported, and includes built‑in salt generation.
- **Cons:**
  - Still CPU intensive and not suitable for real‑time blind indexing; slower than simple hashing.

### Option F: AES-256-GCM (Symmetric Encryption)
A widely used symmetric encryption standard for securing data at rest or in transit.
- **How it works:** Reversibly encrypts the payload using a symmetric key.
  ```javascript
  const crypto = require('crypto');
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', process.env.ENCRYPTION_KEY, iv);
  const token = cipher.update('+919876543210', 'utf8', 'hex') + cipher.final('hex');
  ```
- **Availability:** Available natively in Node.js (`crypto`).
- **Cost:** 100% Free for compute. However, if using a secure Key Management Service API (like AWS KMS or Google Cloud KMS) to inject the keys, it falls under their **Free Tier / Low Cost Tier** ($0.03 per 10,000 requests). 
- **Key Storage:** The encryption key is stored in an environment variable (`process.env.ENCRYPTION_KEY`).
- **Pros:** 
  - Extremely fast and secure.
- **Cons:** 
  - **Reversible:** This violates the core zero‑trust mandate. If an attacker compromises the environment key and the database, all PII can be decrypted back to cleartext. We need a one‑way tokenization, not reversible encryption.

### Option G: BLAKE3 (Newer Cryptographic Hash)
A modern, extremely fast cryptographic hash function.
- **How it works:** Uses the BLAKE3 hashing algorithm.
  ```javascript
  const { hash } = require('blake3');
  // Example using concatenation, though BLAKE3 also supports keyed modes
  const token = hash(process.env.PEPPER_KEY + '+919876543210').toString('hex');
  ```
- **Availability:** Available as third‑party open‑source libraries (e.g., npm `blake3`).
- **Cost:** 100% Free.
- **Key Storage:** The secret pepper is stored in an environment variable (`process.env.PEPPER_KEY`).
- **Pros:**
  - BLAKE3 is significantly faster than SHA-256.
- **Cons:**
  - **Ecosystem Support:** While fast, BLAKE3 often requires external dependencies or native WebAssembly bindings in Node.js. 

### Option H: Cloud Key Management Service (AWS KMS / Google Cloud KMS HMAC)
Externalized hashing where the HMAC key never enters the application environment.
- **How it works:** The application calls a Cloud API to generate the hash using a key permanently locked inside a Hardware Security Module (HSM).
  ```javascript
  const { KMSClient, GenerateMacCommand } = require("@aws-sdk/client-kms");
  const client = new KMSClient();
  const response = await client.send(new GenerateMacCommand({
    KeyId: "arn:aws:kms:region:account:key/uuid",
    Message: Buffer.from('+919876543210'),
    MacAlgorithm: "HMAC_SHA_256"
  }));
  ```
- **Availability:** Proprietary Cloud APIs.
- **Cost:** Violates the 100% Free Tier constraint. Generates API costs (e.g., ~$0.03 per 10,000 requests) that scale linearly with traffic.
- **Pros:** 
  - **Ultimate Security:** Perfectly overcomes the cons of Option A. Even if the application memory is dumped, the key cannot be stolen, making an offline dictionary attack impossible.
- **Cons:** 
  - **Latency:** Adds network round‑trip latency to every single interaction, risking telecom gateway timeouts.
  - **Cost:** Fails the zero‑cost architecture mandate.

---

## 4. Selection Rationale

We selected **Option A: HMAC-SHA256** using a strict cryptographic environment key as the tokenization algorithm. 

**Why it wins:**
1. **Deterministic Lookup:** It allows the Orchestrator to instantly recognize returning citizens across different channels with a direct database query (Blind Indexing), without ever persisting the cleartext ID.
2. **Performance:** It handles thousands of concurrent requests per second on a 100% free-tier CPU without impacting the strict latency budgets of telecom USSD/IVR gateways.
3. **Zero-Trust Compliance:** It is fully one-way and irreversible, completely dropping the cleartext payload from the system while retaining business continuity.

**Security Mitigation:**
Because HMAC-SHA256 executes rapidly, the strength of this approach relies entirely on the `pepper_salt` key. This key must be a high-entropy cryptographically random string (e.g., 64+ characters) injected directly into the application's volatile memory via a secure Secrets Manager. The key must **never** be committed to source code or stored alongside the database.
