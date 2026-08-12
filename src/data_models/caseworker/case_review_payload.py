"""Caseworker incident review staging payload schema."""

from pydantic import Field

from src.data_models.common import (
    ApplicationIntent,
    DomainEntityKey,
    EscalationCaseId,
    EscalationReasonCode,
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

    escalation_case_id: EscalationCaseId = Field(
        ..., description="Unique escalation incident ticket identifier"
    )
    session_id: SessionId = Field(
        ..., description="Primary session key tracking citizen interaction context"
    )
    payload_id: ExtractionPayloadId = Field(
        ..., description="Foreign key referencing upstream NLU extraction payload"
    )
    tokenized_citizen_id: HmacCitizenToken = Field(
        ..., description="Zero-PII SHA-256 HMAC citizen identity token"
    )
    application_intent: ApplicationIntent = Field(..., description="Target scheme intent")
    extracted_entities: dict[DomainEntityKey, str | float | int] = Field(
        default_factory=dict,
        description=(
            "Extracted domain parameters. May be empty ({}) if escalation was "
            "triggered by AI entity extraction failure or unparseable input."
        ),
    )
    # min_length=1 allows single-digit USSD DTMF selections or single-character menu inputs
    # (e.g., "1", "2", "Y") that failed downstream processing to be staged for caseworker review.
    unprocessed_input_content: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Raw citizen text, single-digit menu selection, or signed audio URL",
    )
    escalation_reason: EscalationReasonCode = Field(
        ...,
        description="Canonical escalation classification code",
    )
    staged_at: UtcTimestamp = Field(
        ..., description="UTC timestamp when incident ticket was staged into review dashboard"
    )
