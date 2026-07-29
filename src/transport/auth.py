"""Layer 2 Carrier Auth Validator (Layer 1 -> Layer 2 Security Gateway).

Validates webhook signatures (e.g. Meta X-Hub-Signature-256 for WhatsApp)
and carrier gateway bearer tokens (SIP / USSD SS7 gateways).
"""

import hmac
import secrets
from hashlib import sha256


class CarrierAuthValidator:
    """Security validator enforcing cryptographic signature & token verification for ingress webhooks."""

    @staticmethod
    def validate_whatsapp_signature(
        payload_bytes: bytes,
        signature_header: str | None,
        app_secret: str,
    ) -> bool:
        """Validates Meta WhatsApp Business API X-Hub-Signature-256 header.

        Args:
            payload_bytes: Raw HTTP request body bytes.
            signature_header: Raw 'X-Hub-Signature-256' header string (e.g., 'sha256=abcdef...').
            app_secret: Meta Application Secret key.

        Returns:
            True if signature matches, False otherwise.
        """
        if not signature_header or not signature_header.startswith("sha256="):
            return False

        expected_signature = signature_header[7:].strip()
        computed_signature = hmac.new(
            app_secret.encode("utf-8"),
            payload_bytes,
            sha256,
        ).hexdigest()

        return secrets.compare_digest(computed_signature, expected_signature)

    @staticmethod
    def validate_bearer_token(
        auth_header: str | None,
        expected_token: str,
    ) -> bool:
        """Validates Bearer token header for SIP/USSD carrier gateway requests.

        Args:
            auth_header: Raw 'Authorization' header string (e.g., 'Bearer secret_token').
            expected_token: Expected secret token string.

        Returns:
            True if token matches using constant-time comparison, False otherwise.
        """
        if not auth_header or not auth_header.startswith("Bearer "):
            return False

        provided_token = auth_header[7:].strip()
        return secrets.compare_digest(provided_token, expected_token)
