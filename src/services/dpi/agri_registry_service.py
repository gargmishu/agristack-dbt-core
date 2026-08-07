"""Authoritative DPI Registry: AgriStack Cadastral & Land Registry Service.

Performs cadastral plot verification, landholding ownership cross-matching, and crop validation.

Why cross-match against AgriStack cadastral registries?
Benefit eligibility requires verifying landholding entitlement, survey/khata numbers, and seasonal
crop records before executing automated payouts or staging caseworker reviews.

See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.2)
See: decisions/step2.0_canonical_domain_schemas.md (Section 4.3)
See: decisions/step2.2_governance_flows_and_state_transitions.md
See: roadmap.md (Phase 3 Step 3.1 Service Abstractions)
"""

import logging

from src.services.dpi.dpi_mock_fixtures import (
    INVALID_LAND_RECORD_PREFIX,
    INVALID_SURVEY_NUMBER,
    MOCK_CADASTRAL_REGISTRY,
    UNVERIFIED_IDENTITY_PREFIX,
    UNVERIFIED_IDENTITY_TOKEN_ZERO,
)

logger = logging.getLogger(__name__)


class AgriRegistryService:
    """Service abstraction for AgriStack cadastral and crop land registry cross-matching.

    Validates land ownership parameters and seasonal crop entitlement without exposing PII.

    See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.2)
    """

    async def verify_land_record(self, tokenized_citizen_id: str, land_record_id: str) -> bool:
        """Cross-matches citizen identity token against cadastral land record ID.

        Args:
            tokenized_citizen_id: 64-character SHA-256 HMAC citizen identity token.
            land_record_id: Land record survey/plot identifier.

        Returns:
            True if land ownership and crop entitlement match, False otherwise.
        """
        logger.info(
            "Verifying land record=%s for token=%s...",
            land_record_id,
            tokenized_citizen_id[:16],
        )
        if (
            not land_record_id.strip()
            or land_record_id.startswith(INVALID_LAND_RECORD_PREFIX)
            or INVALID_SURVEY_NUMBER in land_record_id
        ):
            return False
        if (
            tokenized_citizen_id == UNVERIFIED_IDENTITY_TOKEN_ZERO
            or tokenized_citizen_id.startswith(UNVERIFIED_IDENTITY_PREFIX)
        ):
            return False
        if land_record_id in MOCK_CADASTRAL_REGISTRY:
            return MOCK_CADASTRAL_REGISTRY[land_record_id].is_entitled
        return True
