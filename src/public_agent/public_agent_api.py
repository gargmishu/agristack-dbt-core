"""Layer 3 Public Agent Gateway API (Layer 3 Intake Surface).

Receives canonical, zero-PII PublicAgentStandardizedIntakePayload from Layer 2 Gateway,
runs IntakeValidator structure routing, and prepares structured intake for Layer 4 Orchestrator.

See: decisions/step2.0_canonical_domain_schemas.md (Section 4.2)
"""

import logging

from src.data_models.public_agent import PublicAgentStandardizedIntakePayload
from src.public_agent.intake_validator import IntakeValidator, ValidationResult

logger = logging.getLogger(__name__)


class PublicAgentApi:
    """Public Agent Gateway API normalizing events before submitting to Layer 4."""

    def __init__(self, validator: IntakeValidator | None = None) -> None:
        """Initializes PublicAgentApi with an IntakeValidator."""
        self._validator = validator or IntakeValidator()

    async def submit_payload(
        self, payload: PublicAgentStandardizedIntakePayload
    ) -> tuple[PublicAgentStandardizedIntakePayload, ValidationResult]:
        """Submits and validates standardized intake payload for Layer 4 orchestration.

        Args:
            payload: Validated PublicAgentStandardizedIntakePayload from Layer 2 Gateway.

        Returns:
            Tuple of (PublicAgentStandardizedIntakePayload, ValidationResult).
        """
        validation_result = self._validator.validate_intake(payload)
        if not validation_result.is_valid:
            logger.error(
                "PublicAgentApi rejected payload for session=%s: %s",
                payload.session_id,
                validation_result.validation_message,
            )
            raise ValueError(f"Invalid intake payload: {validation_result.validation_message}")

        logger.info(
            "PublicAgentApi accepted payload for session=%s, channel=%s, nlu_required=%s",
            payload.session_id,
            payload.channel_type,
            validation_result.requires_nlu_extraction,
        )
        return payload, validation_result
