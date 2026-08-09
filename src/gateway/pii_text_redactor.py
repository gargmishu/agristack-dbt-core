"""Layer 2 PII Text Redactor (In-Memory Free-Text Sanitizer).

Strips cleartext PII (phone numbers, Aadhaar UIDs) from citizen free-text input content
before downstream processing. Operates exclusively in volatile RAM as a pre-processing
step before PiiPurgeGuard assertion.

Defense-in-depth: PiiPurgeGuard remains as the final sentinel assertion after redaction.
If any PII survives redaction (new patterns, edge cases), the guard will still hard-reject.

See: decisions/step3.2_security_and_ingestion_firewalls.md
"""

import logging
import re
from typing import Final

logger = logging.getLogger(__name__)

_REDACTION_MARKER: Final[str] = "[REDACTED]"

# E.164 international phone numbers embedded in free text (e.g., "+919876543210")
_E164_PHONE_PATTERN: Final[re.Pattern[str]] = re.compile(r"\+[1-9]\d{1,14}")

# 10-digit Indian mobile numbers with optional +91/91 prefix (e.g., "9876543210", "919876543210")
_INDIAN_PHONE_PATTERN: Final[re.Pattern[str]] = re.compile(r"(?:\+91|91)?[6-9]\d{9}")

# 12-digit Aadhaar UID with optional spaces (e.g., "1234 5678 9012" or "123456789012")
_AADHAAR_PATTERN: Final[re.Pattern[str]] = re.compile(r"\d{4}\s?\d{4}\s?\d{4}")


class PiiTextRedactor:
    """In-memory PII redactor stripping cleartext identifiers from free-text content.

    Replaces detected phone numbers and Aadhaar UIDs with '[REDACTED]' marker.
    Stateless utility designed to run before PiiPurgeGuard assertion.

    See: decisions/step3.2_security_and_ingestion_firewalls.md
    """

    @staticmethod
    def redact_phone_numbers(text: str) -> str:
        """Replaces cleartext E.164 and 10-digit Indian phone numbers with [REDACTED].

        Args:
            text: Raw free-text input string.

        Returns:
            Text with phone number patterns replaced by [REDACTED].
        """
        # Apply E.164 first (longer match), then Indian 10-digit pattern
        result = _E164_PHONE_PATTERN.sub(_REDACTION_MARKER, text)
        result = _INDIAN_PHONE_PATTERN.sub(_REDACTION_MARKER, result)
        return result

    @staticmethod
    def redact_aadhaar_numbers(text: str) -> str:
        """Replaces cleartext 12-digit Aadhaar UID patterns with [REDACTED].

        Args:
            text: Raw free-text input string.

        Returns:
            Text with Aadhaar number patterns replaced by [REDACTED].
        """
        return _AADHAAR_PATTERN.sub(_REDACTION_MARKER, text)

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

        redacted = cls.redact_phone_numbers(text)
        redacted = cls.redact_aadhaar_numbers(redacted)

        if redacted != text:
            logger.warning(
                "PII redacted from free-text input for session=%s",
                session_id or "unknown",
            )

        return redacted
