"""Authoritative DPI Registry: Identity Verification Service.

Provides Zero-PII identity token verification against authoritative MOSIP/Aadhaar
registries.

Why operate exclusively on Zero-PII HMAC tokens?
Cleartext PII (phone numbers, Aadhaar numbers, cleartext names) is strictly forbidden from
touching persistent database ledgers or disk storage under Aadhaar Act §29 and national
privacy
mandates. While active tokenization occurs at the Layer 2 perimeter via
ZeroTrustIdentityTokenizer,
all downstream registry verification operates exclusively on pre-computed 64-character hex
tokens
(`HmacCitizenToken`).

See: decisions/step0.3_zero_trust_tokenization.md
See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.1)
See: roadmap.md (Phase 3 Step 3.1 Service Abstractions)
"""

import logging

from src.services.dpi.dpi_mock_fixtures import (
    UNVERIFIED_IDENTITY_PREFIX,
    UNVERIFIED_IDENTITY_TOKEN_ZERO,
)

logger = logging.getLogger(__name__)


class IdentityVerificationService:
    """Service client for sovereign identity registry verification.

    Verifies active citizen registration using pseudonymous 64-character SHA-256 HMAC
    tokens.

    Operations:
    - `verify_identity_token`: Queries identity registry to confirm token validity.

    See: decisions/step0.3_zero_trust_tokenization.md
    See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.1)
    """

    async def verify_identity_token(self, tokenized_citizen_id: str) -> bool:
        """Verifies if tokenized citizen identity token exists in authoritative registry.

        Args:
            tokenized_citizen_id: 64-character SHA-256 HMAC citizen identity token.

        Returns:
            True if identity token is verified and active in registry, False otherwise.
        """
        logger.info("Verifying identity token=%s...", tokenized_citizen_id[:16])
        return (
            tokenized_citizen_id != UNVERIFIED_IDENTITY_TOKEN_ZERO
            and not tokenized_citizen_id.startswith(UNVERIFIED_IDENTITY_PREFIX)
        )
