"""Caseworker incident review staging payload schema."""

from pydantic import Field

from src.data_models.common import (
    ApplicationIntent,
    DomainEntities,
    EscalationCaseId,
    EscalationReasonCode,
    ExtractionPayloadId,
    HmacCitizenToken,
    SessionId,
    StrictBaseModel,
    UnprocessedInputContent,
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
    extracted_entities: DomainEntities = Field(
        default_factory=dict,
        description=(
            "Extracted domain parameters. May be empty ({}) if escalation was "
            "triggered by AI entity extraction failure or unparseable input."
        ),
    )
    unprocessed_input_content: UnprocessedInputContent
    escalation_reason: EscalationReasonCode = Field(
        ...,
        description="Canonical escalation classification code",
    )
    staged_at: UtcTimestamp = Field(
        ..., description="UTC timestamp when incident ticket was staged into review dashboard"
    )
