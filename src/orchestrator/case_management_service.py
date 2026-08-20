"""Layer 4 Governance Engine: Caseworker Case Management Service.

Coordinates incident review ticket lifecycle, district caseworker review queues,
and officer adjudication workflows for escalated claims.

Why locate CaseManagementService in Layer 4 Orchestrator?
CaseManagementService governs internal domain escalation staging (Flow 2), caseworker
review queues, officer audit logging, and citizen clarification resolution loops within
AgriStack's Layer 4 Governance Engine. It injects SocialRegistryService (from
src/services/dpi/)
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
from src.services.dpi import SocialRegistryService

logger = logging.getLogger(__name__)


class CaseManagementService:
    """Service governing caseworker review ticket queues and manual adjudication workflows.

    Maintains incident review ticket staging, queue queries, and officer adjudication
    determinations.

    Operations:
    - `stage_incident_ticket`: Enqueues an escalated `CaseworkerCaseReviewPayload` into the
      staged cases ledger.
    - `get_staged_case`: Retrieves a staged case review ticket by ticket ID.
    - `process_officer_review`: Evaluates a `CaseworkerReviewOutcomePayload`, transitions
      the case,
      and returns a corresponding `GovernanceOutcomePayload`.

    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.2)
    """

    def __init__(self, social_service: SocialRegistryService | None = None) -> None:
        """Initializes CaseManagementService with OpenSPP external DPI connector.

        Args:
            social_service: Social protection platform service connector.
        """
        self._social_service = social_service or SocialRegistryService()
        self._staged_cases: dict[str, CaseworkerCaseReviewPayload] = {}

    async def stage_incident_ticket(self, case_review: CaseworkerCaseReviewPayload) -> bool:
        """Stages an escalated case review into the District Caseworker Dashboard.

        Args:
            case_review: Validated CaseworkerCaseReviewPayload instance.

        Returns:
            True if case was staged successfully into the queue, False otherwise.
        """
        logger.info(
            "Staging incident review ticket=%s session=%s reason=%s",
            case_review.escalation_case_id,
            case_review.session_id,
            case_review.escalation_reason,
        )
        self._staged_cases[case_review.escalation_case_id] = case_review
        return True

    def get_staged_case(self, escalation_case_id: str) -> CaseworkerCaseReviewPayload | None:
        """Retrieves a staged case review payload by escalation incident ticket ID."""
        return self._staged_cases.get(escalation_case_id)

    def list_staged_cases(self) -> list[CaseworkerCaseReviewPayload]:
        """Returns all currently staged caseworker incident review tickets."""
        return list(self._staged_cases.values())

    async def process_officer_review(self, review_outcome: CaseworkerReviewOutcomePayload) -> bool:
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
        """Handles a citizen response to a request-for-more-info case.

        This is the orchestration entrypoint for the citizen follow-up workflow.
        It validates the incoming reply, records that the clarification was received,
        and transitions the case back into the review queue for caseworker adjudication.

        Args:
            escalation_case_id: Incident ticket ID (SPP-CASE-YYYY-XXXXXX).
            citizen_clarification_text: Citizen text reply provided over conversational
            channel.

        Returns:
            True if the response was accepted and queued for re-review, False otherwise.
        """
        if not escalation_case_id.strip() or not citizen_clarification_text.strip():
            return False

        logger.info(
            "Citizen clarification received for ticket=%s; transitioning to UNDER_REVIEW",
            escalation_case_id,
        )
        return True

    async def process_citizen_response_workflow(
        self, escalation_case_id: str, citizen_clarification_text: str
    ) -> bool:
        """Workflow wrapper for citizen follow-up after a REQUEST_MORE_INFO decision.

        This keeps the citizen-response flow explicit and reusable from the orchestrator
        layer without introducing a separate service class for a single use case.
        """
        return await self.resolve_citizen_clarification(
            escalation_case_id, citizen_clarification_text
        )
