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
from src.data_models.caseworker.citizen_clarification_payload import CitizenClarificationPayload


class CaseworkerCaseReviewPayload(StrictBaseModel):
    """Data model representing a staged case review ticket for caseworker review.

    Carries full incident context to the District Agricultural Officer Review Ledger
    when automated processing triggers a human-in-the-loop escalation gate (e.g. low AI
    confidence [60%-94%], cadastral record mismatches, or extraction failure).

    Key Invariants:
    - `tokenized_citizen_id` must be a valid 64-character hexadecimal SHA-256 HMAC token to
      guarantee cleartext PII (MSISDN/Aadhaar) never enters caseworker queues.
    - Fallback Context: `extracted_entities` defaults to `{}` so unparseable or failed AI
      extractions can still be staged and reviewed via `unprocessed_input_content`.
    - `escalation_case_id` must match the format `SPP-CASE-YYYY-XXXXXX`.

    See: decisions/step2.0_canonical_domain_schemas.md#441-case-review-payload
    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 4.4)
    See: decisions/step0.3_zero_trust_tokenization.md
    """

    escalation_case_id: EscalationCaseId
    session_id: SessionId
    payload_id: ExtractionPayloadId
    tokenized_citizen_id: HmacCitizenToken
    application_intent: ApplicationIntent
    extracted_entities: DomainEntities = Field(
        default_factory=dict,
        description=(
            "Extracted domain parameters. May be empty ({}) if escalation was "
            "triggered by AI entity extraction failure or unparseable input."
        ),
    )
    unprocessed_input_content: UnprocessedInputContent
    clarification_history: list[CitizenClarificationPayload] = Field(default_factory=list)
    escalation_reason: EscalationReasonCode
    staged_at: UtcTimestamp = Field(
        ..., description="UTC timestamp when incident ticket was staged into review dashboard"
    )
