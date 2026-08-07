"""Authoritative DPI Registry: OpenSPP Social Registry Service.

Provides the external Digital Public Infrastructure (DPI) boundary connector for
OpenSPP (Open Social Protection Platform) and sovereign social welfare registries.

This service is dedicated to checking citizen social protection eligibility against
the external registry boundary. It does not own case review lifecycle state.

See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.2)
See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.3)
See: roadmap.md (Phase 3 Step 3.1 Service Abstractions)
"""

import logging

from src.services.dpi.dpi_mock_fixtures import (
    UNVERIFIED_IDENTITY_PREFIX,
    UNVERIFIED_IDENTITY_TOKEN_ZERO,
)

logger = logging.getLogger(__name__)


class SocialRegistryService:
    """External DPI client for citizen social protection eligibility checks.

    Queries the OpenSPP social registry for beneficiary entitlement under a specific
    scheme and exposes compatibility hooks for boundary integrations.

    See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.3)
    """

    async def query_beneficiary_eligibility(
        self, tokenized_citizen_id: str, scheme_id: str
    ) -> bool:
        """Queries external social registry for beneficiary entitlement under a specific scheme.

        Args:
            tokenized_citizen_id: 64-character SHA-256 HMAC citizen token.
            scheme_id: Identifier of the target social protection scheme.

        Returns:
            True if citizen is registered and entitled, False otherwise.
        """
        logger.info(
            "Querying OpenSPP scheme=%s eligibility for token=%s",
            scheme_id,
            tokenized_citizen_id[:16],
        )
        return bool(
            tokenized_citizen_id != UNVERIFIED_IDENTITY_TOKEN_ZERO
            and not tokenized_citizen_id.startswith(UNVERIFIED_IDENTITY_PREFIX)
            and scheme_id.strip()
        )
