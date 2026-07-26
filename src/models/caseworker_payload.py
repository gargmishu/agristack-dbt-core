from datetime import datetime

from pydantic import Field, model_validator

from src.models.base import StrictBaseModel
from src.models.enums import ApplicationIntent, DomainEntityKey, GovernanceDecision
from src.models.validators import (
    ChannelSessionId,
    EscalationCaseId,
    HMACCitizenToken,
)


class CaseworkerIncidentStagingPayload(StrictBaseModel):
    """Payload emitted by Step 11 to stage case ticket in Caseworker Review Dashboard."""

    escalation_case_id: EscalationCaseId
    channel_session_id: ChannelSessionId
    payload_id: str = Field(
        ...,
        description="Foreign key referencing original extraction payload (payload_id)",
    )
    tokenized_citizen_id: HMACCitizenToken
    application_intent: ApplicationIntent = Field(
        ..., description="Target scheme intent"
    )
    extracted_entities: dict[DomainEntityKey, str | float | int] = Field(
        default_factory=dict, description="Extracted domain parameters"
    )
    unprocessed_input_content: str = Field(
        ..., max_length=5000, description="Raw citizen text or signed audio URL"
    )
    escalation_reason: str = Field(
        ..., max_length=512, description="Reason for escalation"
    )
    staged_at_timestamp: datetime = Field(
        ..., description="UTC timestamp when staged into caseworker queue"
    )


class CaseworkerReviewPayload(StrictBaseModel):
    """Manual decision submitted by a human caseworker/officer reviewing an escalated case."""

    escalation_case_id: EscalationCaseId
    reviewer_id: str = Field(
        ...,
        min_length=5,
        max_length=128,
        description="UUID or Officer ID of caseworker submitting decision",
    )
    governance_decision: GovernanceDecision = Field(
        ..., description="Must strictly be MANUAL_APPROVE or MANUAL_REJECT"
    )
    review_notes: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Mandatory audit justification note",
    )
    approved_amount: float | None = Field(
        None, ge=0.0, description="Populated for MANUAL_APPROVE"
    )
    rejection_reason: str | None = Field(
        None, max_length=512, description="Populated for MANUAL_REJECT"
    )
    decision_timestamp: datetime = Field(
        ..., description="UTC timestamp when officer submitted decision"
    )

    @model_validator(mode="after")
    def validate_caseworker_decision_fields(self) -> "CaseworkerReviewPayload":
        """Enforces field rules for manual caseworker decisions."""
        allowed_decisions = {
            GovernanceDecision.MANUAL_APPROVE.value,
            GovernanceDecision.MANUAL_REJECT.value,
        }
        decision_str = str(self.governance_decision)
        if decision_str not in allowed_decisions:
            raise ValueError(
                f"CaseworkerReviewPayload decision must be MANUAL_APPROVE or MANUAL_REJECT, "
                f"got {decision_str}"
            )

        if decision_str == GovernanceDecision.MANUAL_APPROVE.value:
            if self.approved_amount is None or self.approved_amount <= 0.0:
                raise ValueError("approved_amount > 0.0 is required for MANUAL_APPROVE")
            if self.rejection_reason is not None:
                raise ValueError("rejection_reason must be None for MANUAL_APPROVE")
        elif decision_str == GovernanceDecision.MANUAL_REJECT.value:
            if not self.rejection_reason or not self.rejection_reason.strip():
                raise ValueError("rejection_reason is required for MANUAL_REJECT")
            if self.approved_amount is not None:
                raise ValueError("approved_amount must be None for MANUAL_REJECT")

        return self
