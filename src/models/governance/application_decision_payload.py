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
    """Application decision payload emitted by Layer 4 rules engine.

    See: decisions/step2.0_canonical_domain_schemas.md#application-decision-payload
    """

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
    review_notes: str | None = Field(
        None,
        max_length=2000,
        description="Internal caseworker audit notes carried from manual adjudication",
    )
    decided_at: UtcTimestamp

    @model_validator(mode="after")
    def validate_approved_decision_fields(self) -> "ApplicationDecisionPayload":
        """Enforces field requirements for approved decision outcomes."""
        approved_decisions = {
            GovernanceDecision.AUTO_APPROVE,
            GovernanceDecision.MANUAL_APPROVE,
            GovernanceDecision.AUTOMATED_PAYOUT,
        }
        if self.governance_decision in approved_decisions:
            if not self.disbursement_txn_id:
                raise ValueError(
                    f"disbursement_txn_id is required for decision {self.governance_decision}"
                )
            if self.disbursement_status is None:
                raise ValueError(
                    f"disbursement_status is required for decision {self.governance_decision}"
                )
            if self.rejection_reason is not None:
                raise ValueError(
                    f"rejection_reason must be None for decision {self.governance_decision}"
                )
            if self.escalation_case_id is not None:
                raise ValueError(
                    f"escalation_case_id must be None for decision {self.governance_decision}"
                )
        return self

    @model_validator(mode="after")
    def validate_rejected_decision_fields(self) -> "ApplicationDecisionPayload":
        """Enforces field requirements for rejected decision outcomes."""
        rejected_decisions = {
            GovernanceDecision.AUTO_REJECT,
            GovernanceDecision.MANUAL_REJECT,
        }
        if self.governance_decision in rejected_decisions:
            if not self.rejection_reason:
                raise ValueError(
                    f"rejection_reason is required for decision {self.governance_decision}"
                )
            if self.disbursement_txn_id is not None:
                raise ValueError(
                    f"disbursement_txn_id must be None for decision {self.governance_decision}"
                )
            if self.disbursement_status is not None:
                raise ValueError(
                    f"disbursement_status must be None for decision {self.governance_decision}"
                )
            if self.escalation_case_id is not None:
                raise ValueError(
                    f"escalation_case_id must be None for decision {self.governance_decision}"
                )
        return self

    @model_validator(mode="after")
    def validate_review_decision_fields(self) -> "ApplicationDecisionPayload":
        """Enforces field requirements for escalation review decision outcomes."""
        review_decisions = {
            GovernanceDecision.ROUTE_FOR_MANUAL_REVIEW,
            GovernanceDecision.HUMAN_REVIEW,
            GovernanceDecision.REQUEST_MORE_INFO,
        }
        if self.governance_decision in review_decisions:
            if not self.escalation_case_id:
                raise ValueError(
                    f"escalation_case_id is required for decision {self.governance_decision}"
                )
            if self.disbursement_txn_id is not None:
                raise ValueError(
                    f"disbursement_txn_id must be None for decision {self.governance_decision}"
                )
            if self.disbursement_status is not None:
                raise ValueError(
                    f"disbursement_status must be None for decision {self.governance_decision}"
                )
            if self.rejection_reason is not None:
                raise ValueError(
                    f"rejection_reason must be None for decision {self.governance_decision}"
                )
        return self
