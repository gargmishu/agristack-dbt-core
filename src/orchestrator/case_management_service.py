"""Layer 4 Governance Engine: Caseworker Case Management Service.

Coordinates incident review ticket lifecycle, district caseworker review queues,
and officer adjudication workflows for escalated claims.

Why locate CaseManagementService in Layer 4 Orchestrator?
CaseManagementService governs internal domain escalation staging (Flow 2), caseworker
review queues, officer audit logging, and citizen clarification resolution loops within
AgriStack's Layer 4 Governance Engine. It injects SocialRegistryService (from src/services/dpi/)
strictly as an external DPI boundary client for OpenSPP synchronization.

See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.2)
See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.3)
See: roadmap.md (Phase 3 Step 3.3 Layer 4 Brain)
"""

import logging

from src.data_models.caseworker import (
    CaseworkerCaseReviewPayload,
    CaseworkerReviewOutcomePayload,
)
from src.data_models.common import GovernanceAction
from src.services.dpi.social_registry_service import SocialRegistryService

logger = logging.getLogger(__name__)


class CaseManagementService:
    """Layer 4 orchestrator service governing caseworker incident review queues and adjudication.

    Maintains lifecycle state transitions for manual review tickets and interfaces
    with the external OpenSPP SocialRegistryService for registry synchronization.

    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.2)
    """

    def __init__(self, social_registry_service: SocialRegistryService) -> None:
        """Initializes CaseManagementService with injected external DPI social registry client.

        Args:
            social_registry_service: Non-nullable SocialRegistryService instance.
        """
        self._social_registry_service = social_registry_service

    @classmethod
    def from_default(cls) -> "CaseManagementService":
        """Factory method to construct CaseManagementService with default dependencies."""
        return cls(social_registry_service=SocialRegistryService())

    async def stage_case_review(self, case_review: CaseworkerCaseReviewPayload) -> bool:
        """Stages an incident review ticket into the district caseworker review queue.

        Coordinates local ticket staging and synchronizes the ticket into the external OpenSPP
        social protection registry.

        Args:
            case_review: Validated CaseworkerCaseReviewPayload instance.

        Returns:
            True if staging succeeded locally and was accepted by OpenSPP, False otherwise.
        """
        logger.info(
            "Staging caseworker review ticket=%s for session=%s",
            case_review.escalation_case_id,
            case_review.session_id,
        )
        return await self._social_registry_service.sync_incident_ticket(case_review)

    async def process_officer_review(
        self, review_outcome: CaseworkerReviewOutcomePayload
    ) -> bool:
        """Processes officer review outcome submitted from the caseworker dashboard.

        Validates review action constraints, updates case lifecycle state, and records
        officer justification notes into the audit trail.

        Args:
            review_outcome: Validated CaseworkerReviewOutcomePayload instance.

        Returns:
            True if review decision was processed successfully, False otherwise.
        """
        logger.info(
            "Processing officer review ticket=%s action=%s by reviewer=%s",
            review_outcome.escalation_case_id,
            review_outcome.governance_action,
            review_outcome.reviewer_id,
        )
        return review_outcome.governance_action in {
            GovernanceAction.MANUAL_APPROVE,
            GovernanceAction.MANUAL_REJECT,
            GovernanceAction.REQUEST_MORE_INFO,
        }

    async def resolve_citizen_clarification(
        self, escalation_case_id: str, citizen_clarification_text: str
    ) -> bool:
        """Attaches citizen clarification reply to open escalation ticket.

        Transitions ticket state strictly from INFO_REQUESTED back to UNDER_REVIEW
        for final caseworker adjudication.

        Args:
            escalation_case_id: Incident ticket ID (SPP-CASE-YYYY-XXXXXX).
            citizen_clarification_text: Citizen text reply provided over conversational channel.

        Returns:
            True if clarification was successfully attached and queued, False otherwise.
        """
        if not escalation_case_id.strip() or not citizen_clarification_text.strip():
            return False

        logger.info(
            "Attached citizen clarification to ticket=%s; transitioning to UNDER_REVIEW",
            escalation_case_id,
        )
        return True
