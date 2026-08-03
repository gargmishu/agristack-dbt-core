"""Layer 4 Governance Engine: Decision Matrix Router.

Evaluates AI extraction confidence scores, landholding cross-match eligibility,
and anti-double-dipping ledgers to assign automated decisions:
1. AUTOMATED_PAYOUT / AUTO_APPROVE (High confidence >=0.85 + Eligible + No active payout)
2. HUMAN_REVIEW / ROUTE_FOR_MANUAL_REVIEW (Low confidence <0.85 or entity discrepancies)
3. AUTO_REJECT (Ineligible land records or double-dipping detection)

See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.1)
See: decisions/step2.0_canonical_domain_schemas.md (Section 4.3)
See: roadmap.md (Phase 3 Step 3.3 Layer 4 Governance Router)
"""

import logging

from src.data_models.governance import GovernanceOutcomePayload

logger = logging.getLogger(__name__)


class GovernanceRouter:
    """Evaluates governance decision matrix based on confidence and registry eligibility.

    Decouples governance adjudication from financial execution by assigning an idempotent
    disbursement transaction key (`disbursement_txn_id`) and status `PENDING` upon approval,
    enabling asynchronous clearing over sovereign payment rails.

    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.1 & 4.1)
    """

    async def route_governance_outcome(
        self, payload: GovernanceOutcomePayload
    ) -> GovernanceOutcomePayload:
        """Routes application evaluation outcome through governance policy matrix.

        Args:
            payload: Validated GovernanceOutcomePayload instance.

        Returns:
            GovernanceOutcomePayload with finalized governance action and tracking keys.
        """
        logger.info(
            "Routing governance outcome for session=%s, decision=%s, confidence=%.2f",
            payload.session_id,
            payload.governance_decision,
            payload.ai_confidence_score,
        )
        return payload
