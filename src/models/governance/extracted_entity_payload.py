from pydantic import Field, model_validator

from src.models.base import StrictBaseModel
from src.models.enums import ApplicationIntent, DomainEntityKey
from src.models.validators import AiConfidenceScore


class ExtractedEntityPayload(StrictBaseModel):
    """SLM structured entity extraction payload (Layer 3 -> Layer 4)."""

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
        """Enforces confidence zeroing and entity wipe when adversarial attempt is flagged."""
        if self.is_adversarial_attempt:
            object.__setattr__(self, "ai_confidence_score", 0.0)
            object.__setattr__(self, "domain_entities", {})
        return self
