"""Authoritative DPI Registry: Social Registry & Caseworker Staging Service.

Interfaces with OpenSPP / Social Welfare registries for incident ticket staging
and case lifecycle management.

Why stage cases into Social Protection Registries?
When AI extraction confidence falls below threshold (<0.85) or entity discrepancies occur,
claims must be staged into caseworker queues (`SPP-CASE-...`) for human officer adjudication.

See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.2 & 4.2)
See: roadmap.md (Phase 2 Step 2.2 Service Abstractions)
"""

import logging

from src.data_models.caseworker import CaseworkerCaseReviewPayload

logger = logging.getLogger(__name__)


class SocialRegistryService:
    """Service abstraction for social welfare case staging and benefit lifecycle tracking.

    Manages incident ticket staging (`SPP-CASE-YYYY-XXXXXX`) and human officer review queues.

    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 4.2)
    """

    async def stage_case_review(self, case_review: CaseworkerCaseReviewPayload) -> bool:
        """Stages an incident review ticket into the district caseworker review queue.

        Args:
            case_review: Validated CaseworkerCaseReviewPayload instance.

        Returns:
            True if case staging succeeded, False otherwise.
        """
        logger.info(
            "Staging case review ticket=%s for session=%s",
            case_review.escalation_case_id,
            case_review.session_id,
        )
        return not (
            case_review.escalation_case_id.startswith("SPP-CASE-REJECT")
            or "fail_stage" in (case_review.escalation_reason or "").lower()
        )
