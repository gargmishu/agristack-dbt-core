from pydantic import Field, model_validator

from src.models.common import (
    AiConfidenceScore,
    DisbursementStatus,
    DisbursementTxnId,
    EligibilityStatus,
    EscalationCaseId,
    ExtractionPayloadId,
    GovernanceDecision,
    SessionId,
    StrictBaseModel,
    UtcTimestamp,
)


class ApplicationDecisionPayload(StrictBaseModel):
    """Application decision payload emitted by Layer 4 rules engine."""

    session_id: SessionId
    payload_id: ExtractionPayloadId
    ai_confidence_score: AiConfidenceScore
    eligibility_status: EligibilityStatus = Field(
        ...,
        description="Computed citizen scheme eligibility status from DPI registry cross-matching",
    )
    governance_decision: GovernanceDecision = Field(
        ..., description="Automated or manual governance routing action"
    )
    disbursement_txn_id: DisbursementTxnId | None = Field(
        None,
        description="Populated for AUTO_APPROVE / MANUAL_APPROVE / AUTOMATED_PAYOUT",
    )
    disbursement_status: DisbursementStatus | None = Field(
        None,
        description="Initialized to PENDING/INITIATED for approved payouts; None otherwise",
    )
    escalation_case_id: EscalationCaseId | None = None
    rejection_reason: str | None = Field(
        None, description="Populated for AUTO_REJECT / MANUAL_REJECT"
    )
    decided_at: UtcTimestamp

    @model_validator(mode="after")
    def validate_conditional_decision_fields(self) -> "ApplicationDecisionPayload":  # noqa: PLR0912
        """Enforces conditional field population based on governance decision outcome."""
        approved_decisions = {
            GovernanceDecision.AUTO_APPROVE.value,
            GovernanceDecision.MANUAL_APPROVE.value,
            GovernanceDecision.AUTOMATED_PAYOUT.value,
        }
        rejected_decisions = {
            GovernanceDecision.AUTO_REJECT.value,
            GovernanceDecision.MANUAL_REJECT.value,
        }
        review_decisions = {
            GovernanceDecision.ROUTE_FOR_MANUAL_REVIEW.value,
            GovernanceDecision.HUMAN_REVIEW.value,
            GovernanceDecision.REQUEST_MORE_INFO.value,
        }

        decision_str = str(self.governance_decision)

        if decision_str in approved_decisions:
            if not self.disbursement_txn_id:
                raise ValueError(f"disbursement_txn_id is required for decision {decision_str}")
            if self.disbursement_status is None:
                raise ValueError(f"disbursement_status is required for decision {decision_str}")
            if self.rejection_reason is not None:
                raise ValueError(f"rejection_reason must be None for decision {decision_str}")
            if self.escalation_case_id is not None:
                raise ValueError(f"escalation_case_id must be None for decision {decision_str}")
        elif decision_str in rejected_decisions:
            if not self.rejection_reason:
                raise ValueError(f"rejection_reason is required for decision {decision_str}")
            if self.disbursement_txn_id is not None:
                raise ValueError(f"disbursement_txn_id must be None for decision {decision_str}")
            if self.disbursement_status is not None:
                raise ValueError(f"disbursement_status must be None for decision {decision_str}")
            if self.escalation_case_id is not None:
                raise ValueError(f"escalation_case_id must be None for decision {decision_str}")
        elif decision_str in review_decisions:
            if not self.escalation_case_id:
                raise ValueError(f"escalation_case_id is required for decision {decision_str}")
            if self.disbursement_txn_id is not None:
                raise ValueError(f"disbursement_txn_id must be None for decision {decision_str}")
            if self.disbursement_status is not None:
                raise ValueError(f"disbursement_status must be None for decision {decision_str}")
            if self.rejection_reason is not None:
                raise ValueError(f"rejection_reason must be None for decision {decision_str}")

        return self
