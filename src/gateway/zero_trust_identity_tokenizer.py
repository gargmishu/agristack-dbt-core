"""Layer 2 Zero-Trust Identity Tokenizer (Layer 2 Privacy Boundary).

Performs one-way SHA-256 HMAC tokenization of citizen identifiers (MSISDN, Aadhaar UID)
in volatile RAM, guaranteeing that cleartext PII never touches disk storage or database ledgers.

See: decisions/step0.3_zero_trust_tokenization.md
"""

import hmac
import os
from hashlib import sha256


class ZeroTrustIdentityTokenizer:
    """In-memory SHA-256 HMAC identity tokenizer enforcing Zero-PII compliance."""

    DEFAULT_PEPPER_ENV_VAR = "AGRISTACK_PEPPER_SECRET"

    def __init__(self, pepper_key: str) -> None:
        """Initializes tokenizer with an explicit cryptographic pepper key."""
        if not pepper_key or not pepper_key.strip():
            raise ValueError("pepper_key cannot be empty or whitespace-only.")
        self._pepper_key = pepper_key.encode("utf-8")

    @classmethod
    def from_env(cls) -> "ZeroTrustIdentityTokenizer":
        """Factory method to instantiate tokenizer using environment variable configuration."""
        pepper_key = os.getenv(cls.DEFAULT_PEPPER_ENV_VAR)
        if not pepper_key or not pepper_key.strip():
            raise ValueError(
                f"Required env var '{cls.DEFAULT_PEPPER_ENV_VAR}' is missing or empty."
            )
        return cls(pepper_key=pepper_key)

    def tokenize_citizen_id(self, raw_identifier: str) -> str:
        """Tokenizes raw citizen ID (Aadhaar / MSISDN / Farmer ID) into 64-char SHA-256 HMAC token.

        Args:
            raw_identifier: Cleartext identity string (e.g. "+919876543210" or Aadhaar number).

        Returns:
            64-character lowercase hex HMAC-SHA256 digest string.
        """
        clean_id = raw_identifier.strip()
        if not clean_id:
            raise ValueError("raw_identifier cannot be empty or whitespace-only")

        token = hmac.new(
            self._pepper_key,
            clean_id.encode("utf-8"),
            sha256,
        ).hexdigest()
        return token

    def tokenize_phone_number(self, phone_number: str) -> str:
        """Tokenizes E.164 phone number into 64-character SHA-256 HMAC token."""
        return self.tokenize_citizen_id(phone_number)
