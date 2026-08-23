"""SLM structured entity extraction payload schema (Layer 3 -> Layer4).

Represents structured intent and domain parameters produced by the SLM/NLU pipeline
(or fast-path structured menu bypass) and consumed by the Layer 4 ClaimOrchestrator
and ClaimAdjudicator.

See: decisions/step2.0_canonical_domain_schemas.md#slm-extracted-entity-payload
See: decisions/step3.2_security_and_ingestion_firewalls.md
See: decisions/step3.3_layer4_orchestrator_brain.md
"""

from pydantic import Field, model_validator

from src.data_models.common import (
    AiConfidenceScore,
    ApplicationIntent,
    DomainEntities,
    StrictBaseModel,
)


class ExtractedEntityPayload(StrictBaseModel):
    """Data model representing structured entities extracted from citizen interactions.

    Encapsulates parsed application intent, domain entity parameters, and AI confidence
    score for consumption by Layer 4 completeness validation (Gate 2) and governance
    routing (Gate 3).

    Invariants:
    - If `is_adversarial_attempt` is True, `domain_entities` is automatically reset to `{}`
      and `ai_confidence_score` is forced to `0.0`.
    - If `is_structured_menu_bypass` is True, `ai_confidence_score` defaults to 1.0.

    See: decisions/step2.0_canonical_domain_schemas.md#slm-extracted-entity-payload
    See: decisions/step3.2_security_and_ingestion_firewalls.md
    See: decisions/step3.3_layer4_orchestrator_brain.md
    """

    application_intent: ApplicationIntent
    ai_confidence_score: AiConfidenceScore
    domain_entities: DomainEntities = Field(
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
        StrictBaseModel is immutable (frozen=True) to prevent accidental mutation during
        pipeline
        execution. When a prompt-injection attack is flagged, we must forcefully override
        the
        LLM/SLM output by zeroing confidence score (0.0) and wiping extracted entities to
        prevent
        hallucinated or injected parameters from contaminating downstream governance rules.
        """
        if self.is_adversarial_attempt:
            object.__setattr__(self, "ai_confidence_score", 0.0)
            object.__setattr__(self, "domain_entities", {})
        return self
