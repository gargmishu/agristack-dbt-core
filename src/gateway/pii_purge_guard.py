"""Layer 2 Zero-Trust PII Purge Guard (In-Memory Privacy Sanitizer & Sentinel).

Combines free-text PII sanitization (redacting cleartext phone numbers and 12-digit Aadhaar
numbers) with downstream compliance assertions (verifying that all citizen identifiers are
strictly SHA-256 HMAC tokens in volatile RAM).

See: decisions/step3.2_security_and_ingestion_firewalls.md
See: decisions/step0.3_zero_trust_tokenization.md
"""

import logging
import re
from typing import Final

from src.data_models.common import PayloadType
from src.data_models.public_agent import PublicAgentStandardizedIntakePayload

logger = logging.getLogger(__name__)

SHA256_HEX_TOKEN_LENGTH: Final[int] = 64
_REDACTION_MARKER: Final[str] = "[REDACTED]"

# E.164 international phone numbers embedded in free text or discrete fields
_E164_PHONE_PATTERN: Final[re.Pattern[str]] = re.compile(r"\+[1-9]\d{1,14}")

# 10-digit Indian mobile numbers with optional +91/91 prefix
_INDIAN_PHONE_PATTERN: Final[re.Pattern[str]] = re.compile(r"(?:\+91|91)?[6-9]\d{9}")

# 12-digit Aadhaar UID with optional spaces (e.g., "1234 5678 9012" or "123456789012")
_AADHAAR_PATTERN: Final[re.Pattern[str]] = re.compile(r"\d{4}\s?\d{4}\s?\d{4}")


class PiiPurgeGuard:
    """Unified in-memory PII redactor and zero-PII contract compliance sentinel."""

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    @classmethod
    def redact_all(cls, text: str, session_id: str | None = None) -> str:
        """Applies all PII redaction rules in sequence and returns sanitized text.

        Args:
            text: Raw free-text input string to sanitize.
            session_id: Optional session identifier for audit logging.

        Returns:
            Sanitized text with all detected PII replaced by [REDACTED].
        """
        if not text or not text.strip():
            return text

        redacted = cls._redact_phone_numbers(text)
        redacted = cls._redact_aadhaar_numbers(redacted)

        if redacted != text:
            logger.warning(
                "PII redacted from free-text input for session=%s",
                session_id or "unknown",
            )

        return redacted

    @classmethod
    def assert_zero_pii(cls, payload: PublicAgentStandardizedIntakePayload) -> None:
        """Asserts that standardized intake payload contains only HMAC tokens and no raw PII.

        Args:
            payload: Validated PublicAgentStandardizedIntakePayload instance.

        Raises:
            ValueError: If cleartext MSISDN or Aadhaar is detected in non-token fields.
        """
        # Token must be strictly a 64-char SHA-256 HMAC hash
        if len(payload.tokenized_citizen_id) != SHA256_HEX_TOKEN_LENGTH:
            raise ValueError(
                f"tokenized_citizen_id must be a {SHA256_HEX_TOKEN_LENGTH}-character "
                f"SHA-256 HMAC token, got length {len(payload.tokenized_citizen_id)}"
            )

        # Ensure citizen token is not a cleartext phone number or Aadhaar UID
        if cls._contains_cleartext_phone(payload.tokenized_citizen_id):
            raise ValueError("Cleartext phone number detected in tokenized_citizen_id field")

        if cls._contains_cleartext_aadhaar(payload.tokenized_citizen_id):
            raise ValueError("Cleartext Aadhaar number detected in tokenized_citizen_id field")

        # Scan unprocessed_input_content for cleartext phone or Aadhaar leak (for text payloads)
        if payload.payload_type == PayloadType.TEXT:
            if cls._contains_cleartext_phone(payload.unprocessed_input_content):
                raise ValueError("Cleartext phone number detected in unprocessed_input_content")
            if cls._contains_cleartext_aadhaar(payload.unprocessed_input_content):
                raise ValueError("Cleartext Aadhaar number detected in unprocessed_input_content")

        logger.debug(
            "Zero-PII compliance verified for session=%s token=%s",
            payload.session_id,
            payload.tokenized_citizen_id[:16],
        )

    # -------------------------------------------------------------------------
    # Private Sanitization & Detection Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def _contains_cleartext_phone(cls, text: str) -> bool:
        """Checks if a string contains raw E.164 or 10-digit Indian phone numbers."""
        if not text or not text.strip():
            return False
        clean = text.strip()
        return bool(_E164_PHONE_PATTERN.search(clean) or _INDIAN_PHONE_PATTERN.search(clean))

    @classmethod
    def _contains_cleartext_aadhaar(cls, text: str) -> bool:
        """Checks if a string contains a 12-digit Aadhaar number pattern."""
        if not text or not text.strip():
            return False
        return bool(_AADHAAR_PATTERN.search(text.strip()))

    @classmethod
    def _redact_phone_numbers(cls, text: str) -> str:
        """Replaces cleartext E.164 and 10-digit Indian phone numbers with [REDACTED]."""
        result = _E164_PHONE_PATTERN.sub(_REDACTION_MARKER, text)
        result = _INDIAN_PHONE_PATTERN.sub(_REDACTION_MARKER, result)
        return result

    @classmethod
    def _redact_aadhaar_numbers(cls, text: str) -> str:
        """Replaces cleartext 12-digit Aadhaar UID patterns with [REDACTED]."""
        return _AADHAAR_PATTERN.sub(_REDACTION_MARKER, text)
