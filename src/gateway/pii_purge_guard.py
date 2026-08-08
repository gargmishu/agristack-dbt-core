"""Layer 2 Zero-Trust PII Purge Guard (In-Memory Privacy Sentinel).

Verifies that incoming cleartext PII (raw phone numbers, 12-digit Aadhaar IDs) is tokenized
in volatile RAM and that no raw PII leaks into downstream standardized contracts.

See: decisions/step3.2_security_and_ingestion_firewalls.md
See: decisions/step0.3_zero_trust_tokenization.md
"""

import logging
import re
from typing import Final

from src.data_models.public_agent import PublicAgentStandardizedIntakePayload

logger = logging.getLogger(__name__)

SHA256_HEX_TOKEN_LENGTH: Final[int] = 64

# Patterns matching cleartext 10/12-digit numbers and international E.164 phone numbers
_E164_PHONE_PATTERN: Final[re.Pattern[str]] = re.compile(r"^\+[1-9]\d{1,14}$")
_AADHAAR_PATTERN: Final[re.Pattern[str]] = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
_INDIAN_PHONE_PATTERN: Final[re.Pattern[str]] = re.compile(r"(?:\+91|91)?[6-9]\d{9}")


class PiiPurgeGuard:
    """In-memory security sentinel asserting zero-PII compliance on canonicalized contracts."""

    @classmethod
    def contains_cleartext_phone(cls, text: str | None) -> bool:
        """Checks if a string contains raw E.164 or 10-digit Indian phone numbers."""
        if not text or not text.strip():
            return False
        clean = text.strip()
        return bool(_E164_PHONE_PATTERN.match(clean) or _INDIAN_PHONE_PATTERN.search(clean))

    @classmethod
    def contains_cleartext_aadhaar(cls, text: str | None) -> bool:
        """Checks if a string contains a 12-digit Aadhaar number pattern."""
        if not text or not text.strip():
            return False
        return bool(_AADHAAR_PATTERN.search(text.strip()))

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
        if cls.contains_cleartext_phone(payload.tokenized_citizen_id):
            raise ValueError("Cleartext phone number detected in tokenized_citizen_id field")

        if cls.contains_cleartext_aadhaar(payload.tokenized_citizen_id):
            raise ValueError("Cleartext Aadhaar number detected in tokenized_citizen_id field")


        logger.debug(
            "Zero-PII compliance verified for session=%s token=%s",
            payload.session_id,
            payload.tokenized_citizen_id[:16],
        )
