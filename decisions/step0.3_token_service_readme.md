# Token Service Reference

> Sequence authority: [roadmap.md](../roadmap.md).

## Purpose

Describe the identity-tokenization capability inside the Layer 2 perimeter. Raw identity values are accepted only at that boundary and are removed before the standardized intake contract is passed downstream.

## API Overview

### POST /v1/tokenize

- **Description:** Generate a deterministic token for a supplied identity value.
- **Authentication:** Service-to-service authorization or mutual TLS.
- **Headers:** `Content-Type: application/json`, `Authorization`, and optional `X-Request-ID`.
- **Body (JSON):**

```json
{
  "type": "phone|uidai_token|bank_account|custom",
  "value": "<raw-value>",
  "meta": { "tenant_id": "<tenant>" }
}
```

- **Response (200):**

```json
{
  "token": "<64-character-lowercase-hex>",
  "type": "phone",
  "algorithm": "HMAC-SHA256",
  "token_version": "v1"
}
```

- **Notes:** The token field contains exactly 64 lowercase hexadecimal characters. The algorithm and token version are separate fields and must be persisted with the token. Never submit raw Aadhaar for direct tokenization; use an authorized UIDAI-issued pseudonymous identifier where a verification flow requires one.

### POST /v1/tokenize/batch

- **Description:** Batch tokenization for multiple values.
- **Body schema:** `values: [{ type, value, meta }, ...]`

There is no reverse-token operation. HMAC tokens are not decryptable. If a regulated workflow requires retrieval of a raw identity value, a separately governed vault must own that value and mediate access with explicit authorization and audit.

## Example

```bash
curl -X POST https://token.example.svc/v1/tokenize \
  -H "Authorization: <service-credential>" \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: <request-id>" \
  -d '{"type":"phone","value":"<phone-number>"}'
```

## Token Format & Determinism

- Primary implementation: deterministic HMAC-SHA-256 using a managed secret pepper. Determinism allows consistent lookup across requests without storing cleartext.
- Format convention: 64 lowercase hexadecimal characters in the token field. Persist the identity type, algorithm, and token version alongside it to support future algorithm or key changes.
- Rotation: rotating the pepper changes outputs. Preserve lookups through a versioned secret store and controlled migration or by checking records against approved prior key versions.

## Security & Key Management

- Store the pepper in an approved secrets manager. The tokenization capability should fetch keys via short-lived credentials and avoid writing secrets to disk.
- Authenticate and authorize all callers. Log only token identifiers, never raw values.
- Audit calls with request ID, caller identity, and outcome; redact request bodies from long-term logs.

## Operational Notes

- **Idempotency:** Deterministic tokenization is idempotent per secret version. One-time dispatch tokens require a separate, governed registry.
- **Error handling:** Return `4xx` for malformed requests, `401/403` for authorization failures, and `5xx` for key-management outages. Provide clear retry guidance to callers.
- **Performance:** Tokenization is CPU-light; the service can remain stateless and horizontally scalable.

## Invariants

- Perform tokenization within the Layer 2 perimeter before data is passed to Layer 3 or Layer 4.
- Never persist raw PII; persist tokens and approved metadata only.
- Prefer a separately governed vault for any permitted raw-PII retention or retrieval.
