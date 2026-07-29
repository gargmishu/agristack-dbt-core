from pydantic import Field, model_validator

from src.models.common import (
    ApplicationIntent,
    DomainEntityKey,
    EscalationCaseId,
    ExtractionPayloadId,
    HmacCitizenToken,
    SessionId,
    StrictBaseModel,
    UtcTimestamp,
)


class CaseworkerCaseReviewPayload(StrictBaseModel):
    """Payload emitted by Step 11 to stage case review in Caseworker Review Dashboard.

    See: decisions/step2.0_canonical_domain_schemas.md#441-case-review-payload
    """

    escalation_case_id: EscalationCaseId
    session_id: SessionId
    payload_id: ExtractionPayloadId
    tokenized_citizen_id: HmacCitizenToken
    application_intent: ApplicationIntent = Field(..., description="Target scheme intent")
    extracted_entities: dict[DomainEntityKey, str | float | int] = Field(
        default_factory=dict, description="Extracted domain parameters"
    )
    unprocessed_input_content: str = Field(
        ..., max_length=5000, description="Raw citizen text or signed audio URL"
    )
    escalation_reason: str = Field(..., max_length=512, description="Reason for escalation")
    staged_at: UtcTimestamp

    @model_validator(mode="after")
    def validate_non_empty_fields(self) -> "CaseworkerCaseReviewPayload":
        """Ensforces non-empty, non-whitespace text fields."""
        if not self.unprocessed_input_content or not self.unprocessed_input_content.strip():
            raise ValueError("unprocessed_input_content cannot be empty or whitespace")
        if not self.escalation_reason or not self.escalation_reason.strip():
            raise ValueError("escalation_reason cannot be empty or whitespace")
        return self
