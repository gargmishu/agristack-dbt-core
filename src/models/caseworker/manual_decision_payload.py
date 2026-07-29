from pydantic import Field, model_validator

from src.models.common import (
    EscalationCaseId,
    GovernanceDecision,
    StrictBaseModel,
    UtcTimestamp,
)


class CaseworkerManualDecisionPayload(StrictBaseModel):
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
    approved_amount: float | None = Field(None, ge=0.0, description="Populated for MANUAL_APPROVE")
    rejection_reason: str | None = Field(
        None, max_length=512, description="Populated for MANUAL_REJECT"
    )
    decided_at: UtcTimestamp

    @model_validator(mode="after")
    def validate_caseworker_decision_fields(self) -> "CaseworkerManualDecisionPayload":
        """Enforces field rules for manual caseworker decisions."""
        allowed_decisions = {
            GovernanceDecision.MANUAL_APPROVE,
            GovernanceDecision.MANUAL_REJECT,
        }
        if self.governance_decision not in allowed_decisions:
            raise ValueError(
                "CaseworkerManualDecisionPayload decision must be MANUAL_APPROVE or "
                f"MANUAL_REJECT, got {self.governance_decision}"
            )

        if self.governance_decision == GovernanceDecision.MANUAL_APPROVE:
            if self.approved_amount is None or self.approved_amount <= 0.0:
                raise ValueError("approved_amount > 0.0 is required for MANUAL_APPROVE")
            if self.rejection_reason is not None:
                raise ValueError("rejection_reason must be None for MANUAL_APPROVE")
        elif self.governance_decision == GovernanceDecision.MANUAL_REJECT:
            if not self.rejection_reason or not self.rejection_reason.strip():
                raise ValueError("rejection_reason is required for MANUAL_REJECT")
            if self.approved_amount is not None:
                raise ValueError("approved_amount must be None for MANUAL_REJECT")

        return self
