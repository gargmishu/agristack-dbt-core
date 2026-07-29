from pydantic import Field, model_validator

from src.data_models.common import (
    AiConfidenceScore,
    ApplicationIntent,
    DomainEntityKey,
    StrictBaseModel,
)


class ExtractedEntityPayload(StrictBaseModel):
    """SLM structured entity extraction payload (Layer 3 -> Layer 4).

    See: decisions/step2.0_canonical_domain_schemas.md#slm-extracted-entity-payload
    """

    application_intent: ApplicationIntent = Field(
        ..., description="Classified citizen intent (e.g. apply_subsidy, check_status)"
    )
    ai_confidence_score: AiConfidenceScore
    domain_entities: dict[DomainEntityKey, str | float | int] = Field(
        default_factory=dict,
        description="Parsed domain fields keyed by canonical DomainEntityKey",
    )
    is_adversarial_attempt: bool = Field(False, description="Flagged by prompt injection firewall")
    is_structured_menu_bypass: bool = Field(
        False, description="True for USSD/DTMF structured menu selections"
    )

    @model_validator(mode="after")
    def validate_adversarial_zeroing(self) -> "ExtractedEntityPayload":
        """Enforces confidence zeroing and entity wipe when adversarial attempt is flagged.

        Why object.__setattr__?
        StrictBaseModel is immutable (frozen=True) to prevent accidental mutation during pipeline
        execution. When a prompt-injection attack is flagged, we must forcefully override the
        LLM/SLM output by zeroing confidence score (0.0) and wiping extracted entities to prevent
        hallucinated or injected parameters from contaminating downstream governance rules.
        """
        if self.is_adversarial_attempt:
            object.__setattr__(self, "ai_confidence_score", 0.0)
            object.__setattr__(self, "domain_entities", {})
        return self
