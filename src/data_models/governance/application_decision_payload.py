from pydantic import Field, model_validator

from src.data_models.common import (
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
        description=(
            "Idempotency tracking key generated at approval time for "
            "AUTO_APPROVE / MANUAL_APPROVE / AUTOMATED_PAYOUT"
        ),
    )
    disbursement_status: DisbursementStatus | None = Field(
        None,
        description=(
            "Initialized to PENDING at decision time; transitioned to INITIATED by step_10 "
            "(or Treasury Dispatcher) upon wire dispatch; updated to SUCCESS/FAILED/RETURNED upon bank callback"
        ),
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
        if self.governance_decision in (
            GovernanceDecision.AUTO_APPROVE,
            GovernanceDecision.AUTOMATED_PAYOUT,
        ):
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
            if self.review_notes is not None:
                raise ValueError(
                    f"review_notes must be None for decision {self.governance_decision}"
                )
        elif self.governance_decision == GovernanceDecision.MANUAL_APPROVE:
            if not self.disbursement_txn_id:
                raise ValueError("disbursement_txn_id is required for MANUAL_APPROVE")
            if self.disbursement_status is None:
                raise ValueError("disbursement_status is required for MANUAL_APPROVE")
            if not self.escalation_case_id:
                raise ValueError("escalation_case_id is required for MANUAL_APPROVE")
            if self.rejection_reason is not None:
                raise ValueError("rejection_reason must be None for MANUAL_APPROVE")
            if self.review_notes is None:
                raise ValueError("review_notes is required for MANUAL_APPROVE")
            if not self.review_notes.strip():
                raise ValueError("review_notes cannot be empty or whitespace for MANUAL_APPROVE")
        return self

    @model_validator(mode="after")
    def validate_rejected_decision_fields(self) -> "ApplicationDecisionPayload":
        """Enforces field requirements for rejected decision outcomes."""
        if self.governance_decision == GovernanceDecision.AUTO_REJECT:
            if not self.rejection_reason:
                raise ValueError("rejection_reason is required for AUTO_REJECT")
            if self.disbursement_txn_id is not None:
                raise ValueError("disbursement_txn_id must be None for AUTO_REJECT")
            if self.disbursement_status is not None:
                raise ValueError("disbursement_status must be None for AUTO_REJECT")
            if self.escalation_case_id is not None:
                raise ValueError("escalation_case_id must be None for AUTO_REJECT")
            if self.review_notes is not None:
                raise ValueError("review_notes must be None for AUTO_REJECT")
        elif self.governance_decision == GovernanceDecision.MANUAL_REJECT:
            if not self.rejection_reason:
                raise ValueError("rejection_reason is required for MANUAL_REJECT")
            if not self.escalation_case_id:
                raise ValueError("escalation_case_id is required for MANUAL_REJECT")
            if self.disbursement_txn_id is not None:
                raise ValueError("disbursement_txn_id must be None for MANUAL_REJECT")
            if self.disbursement_status is not None:
                raise ValueError("disbursement_status must be None for MANUAL_REJECT")
            if self.review_notes is None:
                raise ValueError("review_notes is required for MANUAL_REJECT")
            if not self.review_notes.strip():
                raise ValueError("review_notes cannot be empty or whitespace for MANUAL_REJECT")
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
            if self.review_notes is not None:
                raise ValueError(
                    f"review_notes must be None for decision {self.governance_decision}"
                )
        return self
