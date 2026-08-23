"""Layer 3 Public Agent Gateway API (Layer 3 Intake Surface).

Receives canonical, zero-PII PublicAgentStandardizedIntakePayload instances from the
Layer 2 Security Gateway, evaluates intake structure routing via IntakePayloadEvaluator,
and prepares standardized payloads for Layer 4 ClaimOrchestrator execution.

Why decouple Layer 3 Public Agent Gateway from Layer 2 Security Gateway?
1. Separation of Concerns: Layer 2 handles transport-level security (HMAC webhook signatures,
   Bearer tokens, token-bucket rate limiting, and in-memory PII tokenization into RAM).
2. Domain Intake Routing: Layer 3 provides the public API surface for event intake, structural
   intent evaluation (fast-path DTMF/menu bypass vs. SLM/NLU entity extraction), and session
   correlation before submitting to Layer 4 governance orchestration.
3. Multi-Channel Normalization: Decouples channel-specific edge nuances (WhatsApp, IVR Voice,
   USSD Menu, SMS) from the core claim evaluation pipeline.

See: decisions/step3.4_layer3_intake_gateway_and_connectors.md
See: decisions/step2.0_canonical_domain_schemas.md (Section 4.2)
See: decisions/step3.3_layer4_orchestrator_brain.md
"""

import logging

from src.data_models.public_agent import PublicAgentStandardizedIntakePayload
from src.public_agent.intake_payload_evaluator import (
    IntakeEvaluationResult,
    IntakePayloadEvaluator,
)

logger = logging.getLogger(__name__)


class PublicAgentApi:
    """Public Agent Gateway API providing standardized intake submission and routing evaluation.

    Serves as the primary Layer 3 entrypoint that bridges Layer 2 perimeter security and
    Layer 4 claim orchestration. Inspects normalized, zero-PII intake payloads to classify
    downstream extraction requirements before execution by `ClaimOrchestrator`.

    Routing Classification:
    - Structured Inputs (DTMF / USSD menu choices): Evaluates fast-path bypass
      (`requires_nlu_extraction=False`) to avoid GPU NLU latency and eliminate AI hallucinations.
    - Unstructured Inputs (Free text / Voice audio): Routes to NLU extraction
      (`requires_nlu_extraction=True`) for ASR speech transcription and SLM entity parsing.
    """

    def __init__(self, evaluator: IntakePayloadEvaluator | None = None) -> None:
        """Initializes PublicAgentApi with an optional IntakePayloadEvaluator instance.

        Args:
            evaluator: Optional IntakePayloadEvaluator instance (defaults to standard evaluator).
        """
        self._evaluator = evaluator or IntakePayloadEvaluator()

    async def submit_payload(
        self, payload: PublicAgentStandardizedIntakePayload
    ) -> tuple[PublicAgentStandardizedIntakePayload, IntakeEvaluationResult]:
        """Evaluates intake payload structure and returns verified payload with routing flags.

        Performs content sanity checks and determines whether the incoming interaction requires
        natural language processing (SLM extraction) or can follow a deterministic structured path.

        Args:
            payload: Validated PublicAgentStandardizedIntakePayload from Layer 2 Gateway.

        Returns:
            Tuple of:
            - PublicAgentStandardizedIntakePayload: The validated intake payload ready for
              Layer 4 claim orchestration.
            - IntakeEvaluationResult: Structural evaluation outcome containing `is_valid`,
              `requires_nlu_extraction`, and descriptive status notes.

        Raises:
            ValueError: If payload fails structural validation, contains empty or whitespace-only
                content, or violates channel-structure compatibility constraints.
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
