"""Layer 2 Carrier Auth Validator (Layer 1 -> Layer 2 Security Gateway).

Validates webhook signatures (e.g. Meta X-Hub-Signature-256 for WhatsApp)
and carrier gateway bearer tokens for both IVR (SIP) and USSD (SS7) edge integrations.

See: decisions/step3.2_security_and_ingestion_firewalls.md (Section 2)
See: decisions/step2.0_canonical_domain_schemas.md
"""

import hmac
import secrets
from hashlib import sha256
from typing import Final


class CarrierAuthValidator:
    """Security validator enforcing cryptographic signature & token verification for webhooks.

    Validates transport authenticity across incoming carrier webhooks using timing-safe
    comparisons:
    1. Meta WhatsApp Webhooks: Verifies `X-Hub-Signature-256` SHA-256 HMAC digest against
       app secret.
    2. Bearer Tokens: Verifies Bearer tokens presented in the `Authorization` header.

    Security Guarantees:
    - Constant-Time Comparison: Employs `secrets.compare_digest` across all signature and
      token checks
      to prevent timing side-channel attack vectors.
    - Fail-Closed: Missing headers, invalid formatting, or mismatched digests fail closed.

    See: decisions/step3.2_security_and_ingestion_firewalls.md (Section 2)
    """

    _SIGNATURE_PREFIX: Final[str] = "sha256="
    _BEARER_PREFIX: Final[str] = "Bearer "

    @classmethod
    def validate_hmac_signature(
        cls,
        payload_bytes: bytes,
        signature_header: str | None,
        app_secret: str,
    ) -> bool:
        """Validates SHA-256 HMAC payload signature headers (e.g. Meta WhatsApp, BSPs).

        Args:
            payload_bytes: Raw HTTP request body bytes.
            signature_header: Raw 'X-Hub-Signature-256' or equivalent HMAC header string
                (e.g., 'sha256=abcdef...').
            app_secret: Shared HMAC webhook signing key / application secret.

        Returns:
            True if signature matches using constant-time comparison, False otherwise.
        """
        if not signature_header or not signature_header.startswith(cls._SIGNATURE_PREFIX):
            return False

        expected_signature = signature_header.removeprefix(cls._SIGNATURE_PREFIX).strip()
        computed_signature = hmac.new(
            app_secret.encode("utf-8"),
            payload_bytes,
            sha256,
        ).hexdigest()

        return secrets.compare_digest(computed_signature, expected_signature)

    @classmethod
    def validate_carrier_bearer_token(
        cls,
        auth_header: str | None,
        expected_token: str,
    ) -> bool:
        """Validates Bearer token headers for IVR (SIP), USSD (SS7), and SMS requests.

        Args:
            auth_header: Raw 'Authorization' header string (e.g., 'Bearer secret_token').
            expected_token: Expected secret token string configured for the carrier gateway.

        Returns:
            True if token matches using constant-time comparison, False otherwise.
        """
        if not auth_header or not auth_header.startswith(cls._BEARER_PREFIX):
            return False

        provided_token = auth_header.removeprefix(cls._BEARER_PREFIX).strip()
        return secrets.compare_digest(provided_token, expected_token)
