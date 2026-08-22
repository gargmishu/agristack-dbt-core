"""Layer 3 Public Agent Gateway API (Layer 3 Intake Surface).

Receives canonical, zero-PII PublicAgentStandardizedIntakePayload from Layer 2 Gateway,
evaluates intake structure routing via IntakePayloadEvaluator, and prepares structured
intake payloads for Layer 4 Orchestrator Brain execution.

Why decouple Layer 3 Public Agent API from Layer 2 Access Proxy?
Layer 2 canonicalizes raw channel webhooks (WhatsApp, IVR, USSD) into zero-PII payloads.
Layer 3 provides the public API surface for event intake, Intent Gate routing, and payload
preparation before submitting to Layer 4 state machines.

See: decisions/step2.0_canonical_domain_schemas.md (Section 4.2)
See: roadmap.md (Phase 2 Step 2.2 Layer 3)
"""

import logging

from src.data_models.public_agent import PublicAgentStandardizedIntakePayload
from src.public_agent.intake_payload_evaluator import (
    IntakeEvaluationResult,
    IntakePayloadEvaluator,
)

logger = logging.getLogger(__name__)


class PublicAgentApi:
    """Public Agent Gateway API providing intake submission and structure evaluation.

    Submits standardized intake payloads for evaluation and prepares accepted payloads for
    processing.

    Operations:
    - `submit_payload`: Evaluates a `PublicAgentStandardizedIntakePayload` via the injected
      evaluator,
      raising `ValueError` if invalid, or returning the verified payload and evaluation
      result.

    See: decisions/step2.0_canonical_domain_schemas.md (Section 4.2)
    """

    def __init__(self, evaluator: IntakePayloadEvaluator) -> None:
        """Initializes PublicAgentApi with an explicit IntakePayloadEvaluator instance.

        Args:
            evaluator: IntakePayloadEvaluator instance.
        """
        self._evaluator = evaluator

    @classmethod
    def from_default(cls) -> "PublicAgentApi":
        """Factory method to instantiate PublicAgentApi with default evaluator."""
        return cls(evaluator=IntakePayloadEvaluator())

    async def submit_payload(
        self, payload: PublicAgentStandardizedIntakePayload
    ) -> tuple[PublicAgentStandardizedIntakePayload, IntakeEvaluationResult]:
        """Submits and evaluates standardized intake payload for Layer 4 orchestration.

        Args:
            payload: Validated PublicAgentStandardizedIntakePayload from Layer 2 Gateway.

        Returns:
            Tuple of (PublicAgentStandardizedIntakePayload, IntakeEvaluationResult).

        Raises:
            ValueError: If payload fails intake evaluation sanity checks.
        """
        evaluation_result = self._evaluator.evaluate_payload(payload)
        if not evaluation_result.is_valid:
            logger.warning(
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
