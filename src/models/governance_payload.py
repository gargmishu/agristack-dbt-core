from datetime import datetime

from pydantic import Field, model_validator

from src.models.base import StrictBaseModel
from src.models.enums import (
    ApplicationIntent,
    DisbursementStatus,
    DomainEntityKey,
    EligibilityStatus,
    GovernanceDecision,
)
from src.models.validators import (
    AiConfidenceScore,
    ChannelSessionId,
    DisbursementTxnId,
    EscalationCaseId,
    ExtractionPayloadId,
)


class ExtractedEntityPayload(StrictBaseModel):
    """SLM structured entity extraction payload (Layer 3 -> Layer 4)."""

    application_intent: ApplicationIntent = Field(
        ..., description="Classified citizen intent (e.g. apply_subsidy, check_status)"
    )
    ai_confidence_score: AiConfidenceScore
    domain_entities: dict[DomainEntityKey, str | float | int] = Field(
        default_factory=dict,
        description="Parsed domain fields keyed by canonical DomainEntityKey",
    )
    is_adversarial_attempt: bool = Field(
        False, description="Flagged by prompt injection firewall"
    )
    is_structured_menu_bypass: bool = Field(
        False, description="True for USSD/DTMF structured menu selections"
    )

    @model_validator(mode="after")
    def validate_adversarial_zeroing(self) -> "ExtractedEntityPayload":
        """Enforces confidence zeroing and entity wipe when adversarial attempt is flagged."""
        if self.is_adversarial_attempt:
            object.__setattr__(self, "ai_confidence_score", 0.0)
            object.__setattr__(self, "domain_entities", {})
        return self


class GovernanceRoutingPayload(StrictBaseModel):
    """Governance routing decision payload emitted by Layer 4 rules engine."""

    channel_session_id: ChannelSessionId
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
    decided_at_timestamp: datetime = Field(
        ..., description="UTC timestamp when Layer 4 finalized governance decision"
    )

    @model_validator(mode="after")
    def validate_conditional_decision_fields(self) -> "GovernanceRoutingPayload":  # noqa: PLR0912
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
                raise ValueError(
                    f"disbursement_txn_id is required for decision {decision_str}"
                )
            if self.disbursement_status is None:
                raise ValueError(
                    f"disbursement_status is required for decision {decision_str}"
                )
            if self.rejection_reason is not None:
                raise ValueError(
                    f"rejection_reason must be None for decision {decision_str}"
                )
            if self.escalation_case_id is not None:
                raise ValueError(
                    f"escalation_case_id must be None for decision {decision_str}"
                )
        elif decision_str in rejected_decisions:
            if not self.rejection_reason:
                raise ValueError(
                    f"rejection_reason is required for decision {decision_str}"
                )
            if self.disbursement_txn_id is not None:
                raise ValueError(
                    f"disbursement_txn_id must be None for decision {decision_str}"
                )
            if self.disbursement_status is not None:
                raise ValueError(
                    f"disbursement_status must be None for decision {decision_str}"
                )
            if self.escalation_case_id is not None:
                raise ValueError(
                    f"escalation_case_id must be None for decision {decision_str}"
                )
        elif decision_str in review_decisions:
            if not self.escalation_case_id:
                raise ValueError(
                    f"escalation_case_id is required for decision {decision_str}"
                )
            if self.disbursement_txn_id is not None:
                raise ValueError(
                    f"disbursement_txn_id must be None for decision {decision_str}"
                )
            if self.disbursement_status is not None:
                raise ValueError(
                    f"disbursement_status must be None for decision {decision_str}"
                )
            if self.rejection_reason is not None:
                raise ValueError(
                    f"rejection_reason must be None for decision {decision_str}"
                )

        return self
