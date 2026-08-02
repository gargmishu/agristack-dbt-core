"""Layer 2 Carrier Auth Validator (Layer 1 -> Layer 2 Security Gateway).

Validates webhook signatures (e.g. Meta X-Hub-Signature-256 for WhatsApp)
and carrier gateway bearer tokens for both IVR (SIP) and USSD (SS7) edge integrations.
"""

import hmac
import secrets
from hashlib import sha256


class CarrierAuthValidator:
    """Security validator enforcing cryptographic signature & token verification for webhooks."""

    SIGNATURE_PREFIX = "sha256="
    BEARER_PREFIX = "Bearer "

    @classmethod
    def validate_whatsapp_signature(
        cls,
        payload_bytes: bytes,
        signature_header: str | None,
        app_secret: str,
    ) -> bool:
        """Validates Meta WhatsApp Business API X-Hub-Signature-256 header.

        Args:
            payload_bytes: Raw HTTP request body bytes.
            signature_header: Raw 'X-Hub-Signature-256' header string (e.g., 'sha256=abcdef...').
            app_secret: Meta Application Secret key (provided via the Meta Developers Dashboard).

        Returns:
            True if signature matches, False otherwise.
        """
        if not signature_header or not signature_header.startswith(cls.SIGNATURE_PREFIX):
            return False

        expected_signature = signature_header.removeprefix(cls.SIGNATURE_PREFIX).strip()
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
        """Validates Bearer token header for both IVR (SIP) and USSD (SS7) carrier gateway requests.

        Args:
            auth_header: Raw 'Authorization' header string (e.g., 'Bearer secret_token').
            expected_token: Expected secret token string configured for the carrier gateway.

        Returns:
            True if token matches using constant-time comparison, False otherwise.
        """
        if not auth_header or not auth_header.startswith(cls.BEARER_PREFIX):
            return False

        provided_token = auth_header.removeprefix(cls.BEARER_PREFIX).strip()
        return secrets.compare_digest(provided_token, expected_token)
