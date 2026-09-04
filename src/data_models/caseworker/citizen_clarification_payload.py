"""Caseworker incident review citizen clarification payload schema.

See: decisions/step2.0_canonical_domain_schemas.md#441-case-review-payload
See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.2 & 4.4)
See: decisions/step3.3_layer4_orchestrator_brain.md
"""

from pydantic import Field

from src.data_models.common import StrictBaseModel, UtcTimestamp

__all__ = ["CitizenClarificationPayload"]


class CitizenClarificationPayload(StrictBaseModel):
    """Data model representing a citizen clarification appended to an open case review ticket.

    Captures conversational follow-up input submitted by a citizen over conversational
    channels (WhatsApp, SMS, IVR, USSD) in response to a caseworker's `REQUEST_MORE_INFO`
    adjudication action.

    Lifecycle & Invariants:
    - Appended to `clarification_history` on `CaseworkerCaseReviewPayload` when transitioning
      an incident ticket from `INFO_REQUESTED` back to `UNDER_REVIEW` (marked "Clarification
      Received" in the caseworker dashboard).
    - `text`: Must be between 3 and 5000 characters, containing the citizen's response text
      (e.g., crop loss details, revised survey numbers, or clarification notes).
    - `received_at`: Immutable UTC timestamp recording when the clarification was ingested.

    See: decisions/step2.0_canonical_domain_schemas.md#441-case-review-payload
    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.2 & 4.4)
    See: decisions/step3.3_layer4_orchestrator_brain.md
    """

    text: str = Field(
        ...,
        min_length=3,
        max_length=5000,
        description="Citizen text reply providing requested clarification details",
    )
    received_at: UtcTimestamp = Field(
        ...,
        description="UTC timestamp when citizen clarification was received and ingested",
    )
