"""Layer 3 Intake Validator (Layer 3 Intent & Structure Gate).

Performs structural routing validation on PublicAgentStandardizedIntakePayload:
1. Fast-path routing for DTMF_SELECTION and MENU_SELECTION (bypassing SLM NLU).
2. NLU path routing for FREE_TEXT.
3. Content sanity & non-empty validation.

See: decisions/step2.0_canonical_domain_schemas.md (Section 4.2)
See: roadmap.md (Phase 2 Step 2.2 Layer 3)
"""

import logging
from typing import NamedTuple

from src.data_models.common import StructureLevel
from src.data_models.public_agent import PublicAgentStandardizedIntakePayload

logger = logging.getLogger(__name__)


class ValidationResult(NamedTuple):
    """Result of Layer 3 intake validation."""

    is_valid: bool
    requires_nlu_extraction: bool
    validation_message: str


class IntakeValidator:
    """Validates and determines pipeline routing for Layer 3 intake payloads."""

    def validate_intake(
        self, payload: PublicAgentStandardizedIntakePayload
    ) -> ValidationResult:
        """Evaluates payload structure level and determines downstream Layer 3 -> Layer 4 routing path.

        Args:
            payload: Validated PublicAgentStandardizedIntakePayload instance.

        Returns:
            ValidationResult indicating validity and whether NLU extraction is required.
        """
        if not payload.unprocessed_input_content or not payload.unprocessed_input_content.strip():
            logger.warning("Intake validation failed: empty unprocessed_input_content for session=%s", payload.session_id)
            return ValidationResult(
                is_valid=False,
                requires_nlu_extraction=False,
                validation_message="unprocessed_input_content cannot be empty or whitespace-only",
            )

        if payload.structure_level in (StructureLevel.DTMF_SELECTION, StructureLevel.MENU_SELECTION):
            # Fast-path structured bypass: Saves ~800ms GPU NLU latency and eliminates AI hallucinations.
            logger.info(
                "Structured bypass validated for session=%s, channel=%s, level=%s",
                payload.session_id,
                payload.channel_type,
                payload.structure_level,
            )
            return ValidationResult(
                is_valid=True,
                requires_nlu_extraction=False,
                validation_message="Structured input cleared for direct deterministic processing",
            )
        else:
            # Free-text NLU path: Requires Bhashini ASR/NMT translation and SLM entity extraction.
            logger.info(
                "NLU extraction path validated for session=%s, channel=%s, modality=%s",
                payload.session_id,
                payload.channel_type,
                payload.payload_type,
            )
            return ValidationResult(
                is_valid=True,
                requires_nlu_extraction=True,
                validation_message="Free-text input cleared for SLM entity extraction pipeline",
            )
