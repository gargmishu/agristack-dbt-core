"""Layer 3 Intake Payload Evaluator (Layer 3 Intent & Structure Gate).

Performs structural routing evaluation on PublicAgentStandardizedIntakePayload:
1. Fast-path routing for DTMF_SELECTION and MENU_SELECTION (bypassing NLU extraction).
2. NLU path routing for FREE_TEXT.
3. Content sanity & non-empty validation.

Why structured bypass for DTMF and Menu Selections?
Structured inputs (e.g. keypresses on USSD or IVR phone menus) have deterministic intent
and parameter values. Bypassing AI/SLM entity extraction saves ~800ms GPU NLU latency and
completely eliminates AI hallucinations for structured selections.

See: decisions/step3.4_layer3_intake_gateway_and_connectors.md
See: decisions/step2.0_canonical_domain_schemas.md (Section 4.2)
See: decisions/step3.3_layer4_orchestrator_brain.md
See: roadmap.md (Phase 2 Step 2.2 Layer 3)
"""

import logging

from src.data_models.public_agent import PublicAgentStandardizedIntakePayload

logger = logging.getLogger(__name__)


class IntakePayloadEvaluator:
    """Evaluator classifying intake payload structure and NLU extraction requirements.

    Inspects `PublicAgentStandardizedIntakePayload` instances to determine whether natural
    language extraction is required or if structured bypass applies.

    Evaluation Rules:
    - Structured Inputs (`MENU_SELECTION`, `DTMF_SELECTION`): Bypasses NLU extraction
      and enables direct deterministic entity mapping.
    - Unstructured Inputs (`FREE_TEXT`): Routes to NLU extraction for ASR transcription
      and SLM domain entity parsing.
    - Content Validation: Rejects empty or whitespace-only inputs by raising `ValueError`.

    See: decisions/step3.4_layer3_intake_gateway_and_connectors.md
    See: decisions/step2.0_canonical_domain_schemas.md (Section 4.2)
    """

    def evaluate_payload(self, payload: PublicAgentStandardizedIntakePayload) -> None:
        """Evaluates payload structure level and validates routing prerequisites.

        Args:
            payload: Validated PublicAgentStandardizedIntakePayload instance.

        Raises:
            ValueError: If unprocessed_input_content is empty or whitespace-only.
        """
        if not payload.unprocessed_input_content or not payload.unprocessed_input_content.strip():
            logger.warning(
                "Intake evaluation failed: empty unprocessed_input_content for session=%s",
                payload.session_id,
            )
            raise ValueError("unprocessed_input_content cannot be empty or whitespace-only")

        if payload.structure_level.is_structured:
            # Fast-path structured bypass: Saves ~800ms GPU NLU latency and avoids hallucinations.
            logger.info(
                "Structured bypass evaluated for session=%s, channel=%s, level=%s",
                payload.session_id,
                payload.channel_type,
                payload.structure_level,
            )
        else:
            # Free-text NLU path: Requires ASR/NMT translation and SLM entity extraction.
            logger.info(
                "NLU extraction path evaluated for session=%s, channel=%s, modality=%s",
                payload.session_id,
                payload.channel_type,
                payload.payload_type,
            )
