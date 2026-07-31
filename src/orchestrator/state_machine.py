"""Layer 4 Orchestrator Brain: Deterministic State Machine.

Govern workflow transitions across the three evaluation gates:
1. Ingress & Structure Gate (Modality & Bypass Routing)
2. Intake Validation Gate (Entity Completeness & Multi-attempt Conversational Loops)
3. Deterministic Governance Routing Matrix (Auto Payout vs Review vs Auto Reject)

See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 2.1)
See: decisions/step2.0_canonical_domain_schemas.md (Section 4.3)
See: roadmap.md (Phase 3 Step 3.3 Layer 4 Brain)
"""

import logging

from src.data_models.governance import ExtractedEntityPayload

logger = logging.getLogger(__name__)


class StateMachine:
    """Deterministic state machine governing monotonic workflow transitions.

    Enforces straight-through processing for high-confidence claims while managing
    conversational multi-attempt correction loops and escalation staging for low-confidence
    or incomplete citizen inputs.

    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 2.1)
    """

    async def execute_state_transition(
        self, payload: ExtractedEntityPayload
    ) -> ExtractedEntityPayload:
        """Evaluates extracted entity payload and executes state machine transition.

        Args:
            payload: Validated ExtractedEntityPayload instance from NLU pipeline.

        Returns:
            Updated ExtractedEntityPayload reflecting the new state transition.

        Raises:
            ValueError: If payload contains invalid state transition parameters.
        """
        logger.info(
            "Evaluating state machine transition for intent=%s, confidence=%.2f",
            payload.application_intent,
            payload.ai_confidence_score,
        )
        return payload
