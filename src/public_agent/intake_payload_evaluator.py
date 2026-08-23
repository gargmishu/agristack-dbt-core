"""Layer 3 Intake Payload Evaluator (Layer 3 Intent & Structure Gate).

Performs structural routing evaluation on PublicAgentStandardizedIntakePayload:
1. Fast-path routing for DTMF_SELECTION and MENU_SELECTION (bypassing NLU extraction).
2. NLU path routing for FREE_TEXT.
3. Content sanity & non-empty validation.

Why structured bypass for DTMF and Menu Selections?
Structured inputs (e.g. keypresses on USSD or IVR phone menus) have deterministic intent
and parameter values. Bypassing AI/SLM entity extraction saves ~800ms GPU NLU latency and
completely eliminates AI hallucinations for structured selections.

See: decisions/step2.0_canonical_domain_schemas.md (Section 4.2)
See: roadmap.md (Phase 2 Step 2.2 Layer 3)
"""

import logging
from typing import NamedTuple

from src.data_models.public_agent import PublicAgentStandardizedIntakePayload

logger = logging.getLogger(__name__)


class IntakeEvaluationResult(NamedTuple):
    """Result of intake payload structure evaluation.

    Encapsulates structural validity and NLU extraction requirement flags.

    Attributes:
        is_valid: True if the payload satisfies non-empty content and structure guards.
        requires_nlu_extraction: True if payload requires natural language extraction; False
        if structured bypass applies.
        evaluation_message: Descriptive message explaining the evaluation outcome.

    See: decisions/step2.0_canonical_domain_schemas.md (Section 4.2)
    """

    is_valid: bool
    requires_nlu_extraction: bool
    evaluation_message: str


class IntakePayloadEvaluator:
    """Evaluator classifying intake payload structure and extraction requirements.

    Inspects `PublicAgentStandardizedIntakePayload` instances to determine whether natural
    language extraction is required or if structured bypass applies.

    Evaluation Rules:
    - Structured Inputs (`MENU_SELECTION`, `DTMF_SELECTION`): Bypasses NLU extraction
      (`requires_nlu_extraction=False`).
    - Unstructured Inputs (`FREE_TEXT`): Routes to NLU extraction
      (`requires_nlu_extraction=True`).
    - Content Validation: Rejects empty or whitespace-only inputs (`is_valid=False`).

    See: decisions/step2.0_canonical_domain_schemas.md (Section 4.2)
    """

    def evaluate_payload(
        self, payload: PublicAgentStandardizedIntakePayload
    ) -> IntakeEvaluationResult:
        """Evaluates payload structure level and determines downstream routing path.

        Args:
            payload: Validated PublicAgentStandardizedIntakePayload instance.

        Returns:
            IntakeEvaluationResult indicating validity and whether NLU extraction is
            required.
        """
        if not payload.unprocessed_input_content or not payload.unprocessed_input_content.strip():
            logger.warning(
                "Intake evaluation failed: empty unprocessed_input_content for session=%s",
                payload.session_id,
            )
            return IntakeEvaluationResult(
                is_valid=False,
                requires_nlu_extraction=False,
                evaluation_message="unprocessed_input_content cannot be empty or whitespace-only",
            )

        if payload.structure_level.is_structured:
            # Fast-path structured bypass: Saves ~800ms GPU NLU latency and avoids hallucinations.
            logger.info(
                "Structured bypass evaluated for session=%s, channel=%s, level=%s",
                payload.session_id,
                payload.channel_type,
                payload.structure_level,
            )
            return IntakeEvaluationResult(
                is_valid=True,
                requires_nlu_extraction=False,
                evaluation_message="Structured input cleared for direct deterministic processing",
            )
        else:
            # Free-text NLU path: Requires ASR/NMT translation and SLM entity extraction.
            logger.info(
                "NLU extraction path evaluated for session=%s, channel=%s, modality=%s",
                payload.session_id,
                payload.channel_type,
                payload.payload_type,
            )
            return IntakeEvaluationResult(
                is_valid=True,
                requires_nlu_extraction=True,
                evaluation_message="Free-text input cleared for SLM entity extraction pipeline",
            )
