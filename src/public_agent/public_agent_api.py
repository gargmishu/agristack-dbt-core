"""Layer 3 Public Agent Gateway API (Layer 3 Intake Surface).

Receives canonical, zero-PII PublicAgentStandardizedIntakePayload from Layer 2 Gateway,
evaluates intake structure routing, and prepares structured intake for Layer 4 Orchestrator.

See: decisions/step2.0_canonical_domain_schemas.md (Section 4.2)
"""

import logging

from src.data_models.public_agent import PublicAgentStandardizedIntakePayload
from src.public_agent.intake_payload_evaluator import (
    IntakeEvaluationResult,
    IntakePayloadEvaluator,
)

logger = logging.getLogger(__name__)


class PublicAgentApi:
    """Public Agent Gateway API normalizing events before submitting to Layer 4."""

    def __init__(self, evaluator: IntakePayloadEvaluator | None = None) -> None:
        """Initializes PublicAgentApi with an IntakePayloadEvaluator."""
        self._evaluator = evaluator or IntakePayloadEvaluator()

    async def submit_payload(
        self, payload: PublicAgentStandardizedIntakePayload
    ) -> tuple[PublicAgentStandardizedIntakePayload, IntakeEvaluationResult]:
        """Submits and evaluates standardized intake payload for Layer 4 orchestration.

        Args:
            payload: Validated PublicAgentStandardizedIntakePayload from Layer 2 Gateway.

        Returns:
            Tuple of (PublicAgentStandardizedIntakePayload, IntakeEvaluationResult).
        """
        evaluation_result = self._evaluator.evaluate_payload(payload)
        if not evaluation_result.is_valid:
            logger.error(
                "PublicAgentApi rejected payload for session=%s: %s",
                payload.session_id,
                evaluation_result.evaluation_message,
            )
            raise ValueError(f"Invalid intake payload: {evaluation_result.evaluation_message}")

        logger.info(
            "PublicAgentApi accepted payload for session=%s, channel=%s, nlu_required=%s",
            payload.session_id,
            payload.channel_type,
            evaluation_result.requires_nlu_extraction,
        )
        return payload, evaluation_result
