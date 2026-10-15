"""Layer 4 Governance Engine: Caseworker Case Management Service.

Coordinates incident review ticket lifecycle, district caseworker review queues,
and officer adjudication workflows for escalated claims.

Why locate case management in Layer 4 Orchestrator?
Governs internal domain escalation staging (Flow 2), caseworker review queues, officer
audit logging, and citizen clarification resolution loops within Layer 4 Governance.
It interacts with external social protection registries strictly as an external DPI
boundary client for OpenSPP synchronization.

See: decisions/step2.3_governance_flows_and_state_transitions.md (Section 3.2)
See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.3)
See: roadmap.md (Phase 3 Step 3.3 Layer 4 Brain)
"""

import logging
from datetime import UTC, datetime

from src.data_models.caseworker import (
    CaseworkerCaseReviewPayload,
    CaseworkerReviewOutcomePayload,
    CitizenClarificationPayload,
)
from src.data_models.common import ApplicationStatus, GovernanceAction
from src.services.dpi import SocialRegistryService, create_social_registry_service

logger = logging.getLogger(__name__)

__all__ = ["CaseManagementService"]


class CaseManagementService:
    """Service governing caseworker review ticket queues and manual adjudication workflows.

    Maintains incident review ticket staging, queue queries, and officer adjudication
    determinations.

    Operations:
    - `stage_incident_ticket`: Enqueues an escalated `CaseworkerCaseReviewPayload` into the
      staged cases ledger.
    - `get_staged_case`: Retrieves a staged case review ticket by ticket ID.
    - `process_officer_review`: Evaluates a `CaseworkerReviewOutcomePayload`, transitions
            the case, and records the officer decision in the audit ledger.

        Audit-log storage:
        - Current: keeps an in-memory, append-only history of officer outcomes grouped by
            `escalation_case_id` for lifecycle queries and testable governance behavior.
        - Future: the dictionary boundary can be replaced by a durable append-only audit
            repository without changing the case-management API; each case key is the natural
            partition for retention, retrieval, and compliance export.

    See: decisions/step2.3_governance_flows_and_state_transitions.md (Section 3.2)
    """

    def __init__(self, social_service: SocialRegistryService | None = None) -> None:
        """Initializes case management service with external social registry DPI connector.

        Args:
            social_service: Social protection platform service connector.
        """
        self._social_service = social_service or create_social_registry_service()
        self._staged_cases: dict[str, CaseworkerCaseReviewPayload] = {}
        self._case_records: dict[str, CaseworkerCaseReviewPayload] = {}
        self._case_statuses: dict[str, ApplicationStatus] = {}
        self._review_audit_log: dict[str, list[CaseworkerReviewOutcomePayload]] = {}

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
        self._case_records[case_review.escalation_case_id] = case_review
        self._case_statuses[case_review.escalation_case_id] = ApplicationStatus.UNDER_REVIEW
        return True

    def get_staged_case(self, escalation_case_id: str) -> CaseworkerCaseReviewPayload | None:
        """Retrieves a staged case review payload by escalation incident ticket ID.

        Args:
            escalation_case_id: The unique incident case ticket identifier string.

        Returns:
            CaseworkerCaseReviewPayload if found, None otherwise.
        """
        return self._staged_cases.get(escalation_case_id)

    def list_staged_cases(self) -> list[CaseworkerCaseReviewPayload]:
        """Returns all currently staged caseworker incident review tickets.

        Returns:
            List of all staged CaseworkerCaseReviewPayload instances.
        """
        return list(self._staged_cases.values())

    def get_case_status(self, escalation_case_id: str) -> ApplicationStatus | None:
        """Returns the current lifecycle status for a staged or reviewed case.

        Args:
            escalation_case_id: The unique incident case ticket identifier string.

        Returns:
            Current ApplicationStatus enum value if case exists, None otherwise.
        """
        return self._case_statuses.get(escalation_case_id)

    def list_review_audit_entries(
        self, escalation_case_id: str
    ) -> list[CaseworkerReviewOutcomePayload]:
        """Returns a chronological copy of the audit history for one escalation case.

        Args:
            escalation_case_id: The unique incident case ticket identifier string.

        Returns:
            List of CaseworkerReviewOutcomePayload entries in chronological order.
        """
        return list(self._review_audit_log.get(escalation_case_id, []))

    def get_citizen_clarification(self, escalation_case_id: str) -> str | None:
        """Returns the latest citizen clarification recorded for an escalation case.

        Args:
            escalation_case_id: The unique incident case ticket identifier string.

        Returns:
            Latest clarification text string if available, None otherwise.
        """
        clarifications = self.get_citizen_clarifications(escalation_case_id)
        return clarifications[-1].text if clarifications else None

    def get_citizen_clarifications(
        self, escalation_case_id: str
    ) -> list[CitizenClarificationPayload]:
        """Returns a copy of all citizen clarifications recorded for an escalation case.

        Args:
            escalation_case_id: The unique incident case ticket identifier string.

        Returns:
            List of CitizenClarificationPayload objects in historical order.
        """
        case_record = self._case_records.get(escalation_case_id)
        return list(case_record.clarification_history) if case_record else []

    async def process_officer_review(self, review_outcome: CaseworkerReviewOutcomePayload) -> bool:
        """Processes officer review outcome submitted from the caseworker dashboard.

        Validates review action constraints, updates case lifecycle state, and records
        officer justification notes into the audit trail.

        Args:
            review_outcome: Validated CaseworkerReviewOutcomePayload instance.

        Returns:
            True if the review decision was processed successfully, False if the case was
            not staged or the action is unsupported.
        """
        case_id = review_outcome.escalation_case_id
        if case_id not in self._staged_cases:
            logger.warning("Cannot process review for unstaged ticket=%s", case_id)
            return False

        next_status_by_action = {
            GovernanceAction.MANUAL_APPROVE: ApplicationStatus.APPROVED,
            GovernanceAction.MANUAL_REJECT: ApplicationStatus.REJECTED,
            GovernanceAction.REQUEST_MORE_INFO: ApplicationStatus.INFO_REQUESTED,
        }
        next_status = next_status_by_action.get(review_outcome.governance_action)
        if next_status is None:
            return False

        logger.info(
            "Processing officer review ticket=%s action=%s by reviewer=%s",
            case_id,
            review_outcome.governance_action,
            review_outcome.reviewer_id,
        )
        self._case_statuses[case_id] = next_status
        self._review_audit_log.setdefault(case_id, []).append(review_outcome)
        self._staged_cases.pop(case_id)
        return True

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
            logger.warning(
                "Cannot resolve clarification: empty case_id='%s' or empty text",
                escalation_case_id,
            )
            return False
        if self._case_statuses.get(escalation_case_id) != ApplicationStatus.INFO_REQUESTED:
            logger.warning(
                "Cannot resolve clarification for ticket=%s: ticket not in INFO_REQUESTED status",
                escalation_case_id,
            )
            return False

        logger.info(
            "Citizen clarification received for ticket=%s; transitioning to UNDER_REVIEW",
            escalation_case_id,
        )
        clarification = citizen_clarification_text.strip()
        clarification_received_at = datetime.now(UTC)
        case_record = self._case_records[escalation_case_id]
        updated_case = case_record.model_copy(
            update={
                "clarification_history": [
                    *case_record.clarification_history,
                    CitizenClarificationPayload(
                        text=clarification,
                        received_at=clarification_received_at,
                    ),
                ]
            }
        )
        self._case_records[escalation_case_id] = updated_case
        self._staged_cases[escalation_case_id] = updated_case
        self._case_statuses[escalation_case_id] = ApplicationStatus.UNDER_REVIEW
        return True
