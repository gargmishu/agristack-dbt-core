"""Authoritative DPI Registry: OpenSPP Social Registry Service.

Provides the external Digital Public Infrastructure (DPI) boundary connector for
OpenSPP (Open Social Protection Platform) and Sovereign Social Welfare registries.

Why separate SocialRegistryService from CaseManagementService?
SocialRegistryService acts strictly as the external network boundary client interfacing
with sovereign OpenSPP registries to register incident tickets (`SPP-CASE-...`) and verify
social protection program entitlement. CaseManagementService handles internal domain
caseworker queues and review lifecycles within AgriStack.

See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.2)
See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.3)
See: roadmap.md (Phase 3 Step 3.1 Service Abstractions)
"""

import logging

from src.data_models.caseworker import CaseworkerCaseReviewPayload
from src.services.dpi.dpi_mock_fixtures import (
    MOCK_CASE_REJECT_PREFIX,
    MOCK_FAIL_STAGE_NOTE,
    UNVERIFIED_IDENTITY_PREFIX,
    UNVERIFIED_IDENTITY_TOKEN_ZERO,
)

logger = logging.getLogger(__name__)


class SocialRegistryService:
    """External DPI client for OpenSPP social protection and beneficiary registry integration.

    Manages remote synchronization of incident review cases (`SPP-CASE-YYYY-XXXXXX`)
    and citizen social protection eligibility queries.

    See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.3)
    """

    async def sync_incident_ticket(self, case_review: CaseworkerCaseReviewPayload) -> bool:
        """Synchronizes an escalated case review ticket into external OpenSPP registry.

        Args:
            case_review: Validated CaseworkerCaseReviewPayload instance.

        Returns:
            True if OpenSPP accepted the ticket, False if rejected or malformed.
        """
        logger.info(
            "Syncing incident ticket=%s to OpenSPP registry for session=%s",
            case_review.escalation_case_id,
            case_review.session_id,
        )
        return not (
            case_review.escalation_case_id.startswith(MOCK_CASE_REJECT_PREFIX)
            or MOCK_FAIL_STAGE_NOTE in (case_review.escalation_reason or "").lower()
        )

    async def stage_case_review(self, case_review: CaseworkerCaseReviewPayload) -> bool:
        """Alias for sync_incident_ticket to maintain interface compatibility.

        Args:
            case_review: Validated CaseworkerCaseReviewPayload instance.

        Returns:
            True if case sync succeeded, False otherwise.
        """
        return await self.sync_incident_ticket(case_review)

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
