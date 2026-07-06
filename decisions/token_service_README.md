# Token Service — README

## Purpose

Provide a compact reference for the tokenization service used by the intake/orchestrator (Layer 3/4). This document describes API endpoints, expected inputs, example requests/responses, security notes, and operational guidance.

## API Overview

### POST /v1/tokenize

- **Description:** Generate a deterministic token for a supplied PII value.
- **Auth:** Bearer token (service-to-service) or mTLS.
- **Headers:** `Content-Type: application/json`, `Authorization: Bearer <svc-token>`, `X-Request-ID` (recommended)
- **Body (JSON):**

```json
{
  "type": "phone|aadhaar|bank_account|custom",
  "value": "<raw-value>",
  "meta": { "tenant_id": "<tenant>" }
}
```

- **Response (200):**

```json
{
  "token": "hmac-sha256:<hex>",
  "type": "aadhaar",
  "algorithm": "HMAC-SHA256",
  "token_version": "v1"
}
```

- **Notes:** Service returns a one-way token (HMAC-SHA256 hex) prefixed with algorithm and version. Use `type` to disambiguate hashing/normalization rules.

### POST /v1/tokenize/batch

- **Description:** Batch tokenization for multiple values.
- **Body schema:** `values: [{ type, value, meta }, ...]`

### POST /v1/reverse (OPTIONAL, restricted)

- **Description:** Resolve token -> raw value.
- **Notes:** Disabled by default. If required for regulated vault access, restrict to operator vaults with strict audit and short TTL credentials.
- **Recommendation:** Prefer downstream vaults to own raw PII and return short-lived dispatch tokens rather than reversing tokens in service.

## Examples

### Example curl (single)

```bash
curl -X POST https://token.example.svc/v1/tokenize \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type":"phone","value":"+919876543210"}'
```

### Example Response

```json
{
  "token": "hmac-sha256:3f7a8b...",
  "type": "phone",
  "algorithm": "HMAC-SHA256",
  "token_version": "v1"
}
```

## Token Format & Determinism

- Primary implementation: deterministic HMAC-SHA256 using a service-managed secret (`pepper_salt`). Determinism allows consistent lookup across requests without storing cleartext.
- Format convention: `<algorithm>:<hex>` (e.g., `hmac-sha256:...`). Include `type` and `token_version` in persisted records to support future algorithm/version changes.
- Rotation: rotating the `pepper_salt` changes outputs; to preserve existing token lookups across rotations, maintain a versioned secret store and support lookup using previous secret versions, or store mapping records in a secure token registry.

## Security & KMS

- Store `pepper_salt` in a secrets manager (KMS/Vault). The token service should fetch keys via short-lived credentials and avoid writing secrets to disk.
- Access to the token service must be authenticated and authorized (service-to-service credentials). Log only token identifiers (never raw values).
- Audit all calls with `X-Request-ID`, caller identity, and outcome (success/failure); redact request bodies in long-term logs.

## Operational Notes

- **Idempotency:** Deterministic tokenization is idempotent per secret version. For non-deterministic needs (one-time tokens), implement a separate endpoint that stores mapping in a secure registry.
- **Error handling:** return `4xx` for malformed requests, `401/403` for auth failures, `5xx` for KMS outages. Provide clear retry guidance to callers.
- **Performance:** Tokenization is CPU-light; keep service stateless and horizontally scalable.

## Best Practices

- Perform tokenization at Layer 3 (Public Agent Intake Gateway) or immediately after entity extraction in Layer 4 (Orchestrator Brain).
- Never persist raw PII; persist tokens + metadata only.
- Prefer vault ownership of raw PII for long-term retention and retrieval; use tokens for correlation and lookups.

---

For link-back: reference this file from `decisions/zero_trust_tokenization.md` if desired.
