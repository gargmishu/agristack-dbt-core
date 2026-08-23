"""Layer 3 Public Agent Gateway API (Layer 3 Intake Surface).

Receives canonical, zero-PII PublicAgentStandardizedIntakePayload instances from the
Layer 2 Security Gateway (IngestionFirewall / PayloadCanonicalizer), evaluates intake
structure and routing requirements via IntakePayloadEvaluator, and prepares standardized
payloads for Layer 4 ClaimOrchestrator execution.

Why decouple Layer 3 Public Agent Gateway from Layer 2 Security Gateway?
1. Separation of Concerns: Layer 2 handles transport-level security (HMAC webhook signatures,
   Bearer tokens, token-bucket rate limiting, and in-memory PII tokenization into RAM).
2. Domain Intake Routing: Layer 3 provides the public API surface for event intake, structural
   intent evaluation (fast-path DTMF/menu bypass vs. SLM/NLU entity extraction), and session
   correlation before submitting to Layer 4 governance orchestration.
3. Multi-Channel Normalization: Decouples channel-specific edge nuances (WhatsApp, IVR Voice,
   USSD Menu, SMS) from the core claim evaluation state machine.

See: decisions/step3.4_layer3_intake_gateway_and_connectors.md
See: decisions/step2.0_canonical_domain_schemas.md (Section 4.2)
See: decisions/step3.3_layer4_orchestrator_brain.md
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

    Acts as the primary Layer 3 entrypoint that mediates between Layer 2 perimeter security
    and Layer 4 claim orchestration. Submits standardized intake payloads for structural
    evaluation and prepares verified payloads for downstream processing.

    Core Responsibilities:
    - Intake Validation (`submit_payload`): Validates incoming normalized payloads against
      non-empty content guards and structural compatibility rules via `IntakePayloadEvaluator`.
    - Routing Classification: Determines whether a payload is a structured fast-path input
      (DTMF/USSD keypress bypassing GPU NLU extraction) or an unstructured input requiring
      speech-to-text (ASR) and Small Language Model (SLM) domain entity extraction.
    - Zero-PII Invariant: Operates strictly on pre-tokenized 64-character SHA-256 HMAC citizen
      identity tokens (`HmacCitizenToken`), guaranteeing that cleartext identifiers never enter
      the Layer 3 intake boundary.

    See: decisions/step3.4_layer3_intake_gateway_and_connectors.md
    See: decisions/step2.0_canonical_domain_schemas.md (Section 4.2)
    See: decisions/step3.3_layer4_orchestrator_brain.md
    """

    def __init__(self, evaluator: IntakePayloadEvaluator) -> None:
        """Initializes PublicAgentApi with an explicit IntakePayloadEvaluator instance.

        Follows strict dependency injection to allow custom or mock structural evaluators
        during unit and integration testing.

        Args:
            evaluator: Non-nullable IntakePayloadEvaluator instance.
        """
        self._evaluator = evaluator

    @classmethod
    def from_default(cls) -> "PublicAgentApi":
        """Factory constructor instantiating PublicAgentApi with standard evaluator.

        Returns:
            PublicAgentApi configured with the default IntakePayloadEvaluator.
        """
        return cls(evaluator=IntakePayloadEvaluator())

    async def submit_payload(
        self, payload: PublicAgentStandardizedIntakePayload
    ) -> tuple[PublicAgentStandardizedIntakePayload, IntakeEvaluationResult]:
        """Submits and evaluates a standardized intake payload for Layer 4 orchestration.

        Validates that the incoming payload meets structural and content sanity requirements,
        and determines the downstream processing path (structured menu bypass vs. NLU/SLM
        entity extraction pipeline).

        Args:
            payload: Validated, zero-PII PublicAgentStandardizedIntakePayload from Layer 2.

        Returns:
            Tuple of:
            - PublicAgentStandardizedIntakePayload: The validated intake payload ready for
              Layer 4 ClaimOrchestrator.execute_orchestration_cycle().
            - IntakeEvaluationResult: Structural evaluation outcome detailing whether NLU
              extraction is required (`requires_nlu_extraction`) and descriptive status messages.

        Raises:
            ValueError: If the payload fails structural validation, contains empty/whitespace-only
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
