"""Caseworker manual adjudication decision payload schema."""

from pydantic import Field, model_validator

from src.data_models.common import (
    EscalationCaseId,
    GovernanceDecision,
    StrictBaseModel,
    UtcTimestamp,
)


class CaseworkerManualDecisionPayload(StrictBaseModel):
    """Manual decision submitted by a human caseworker/officer reviewing an escalated case.

    This contract represents the authoritative adjudication outcome rendered by an officer on the
    Caseworker Review Dashboard. It governs human-in-the-loop resolutions for complex claims that
    exceeded automated confidence thresholds or triggered policy escalation gates.

    To preserve strict system auditability and financial clearing invariants, this schema enforces
    a rigorous state matrix: positive financial allowances are mandatory for approvals and forbidden
    otherwise, rejection justifications are mandatory for rejections and forbidden otherwise, and
    intermediate clarification requests strictly exclude both terminal attributes.

    See: decisions/step2.0_canonical_domain_schemas.md#442-caseworker-review-decision-payload
    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 4.4)
    """

    escalation_case_id: EscalationCaseId = Field(
        ..., description="Upstream incident ticket ID being adjudicated by caseworker"
    )
    reviewer_id: str = Field(
        ...,
        min_length=5,
        max_length=128,
        description="UUID or Officer ID of caseworker submitting decision",
    )
    governance_decision: GovernanceDecision = Field(
        ..., description="Must strictly be MANUAL_APPROVE, MANUAL_REJECT, or REQUEST_MORE_INFO"
    )
    review_notes: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Mandatory audit justification note or information request details",
    )
    approved_amount: float | None = Field(None, ge=0.0, description="Populated for MANUAL_APPROVE")
    rejection_reason: str | None = Field(
        None, max_length=512, description="Populated for MANUAL_REJECT"
    )
    decided_at: UtcTimestamp = Field(
        ..., description="UTC timestamp when officer rendered adjudication verdict"
    )

    @model_validator(mode="after")
    def validate_decision_type_and_audit_notes(self) -> "CaseworkerManualDecisionPayload":
        """Enforces allowed manual decisions and non-empty caseworker audit justification.

        Why restrict decision types and enforce non-empty review_notes?
        Automated decisions (e.g. AUTO_APPROVE or AUTOMATED_PAYOUT) are strictly forbidden within
        caseworker payloads to prevent automated system spoofing through administrative portals.
        Furthermore, national welfare audit regulations require every human adjudication to carry
        an immutable, meaningful textual justification (`review_notes`) in the governance ledger.
        """
        allowed_decisions = {
            GovernanceDecision.MANUAL_APPROVE,
            GovernanceDecision.MANUAL_REJECT,
            GovernanceDecision.REQUEST_MORE_INFO,
        }
        if self.governance_decision not in allowed_decisions:
            raise ValueError(
                "CaseworkerManualDecisionPayload decision must be MANUAL_APPROVE, "
                f"MANUAL_REJECT, or REQUEST_MORE_INFO, got {self.governance_decision}"
            )

        if not self.review_notes or not self.review_notes.strip():
            raise ValueError("review_notes cannot be empty or whitespace")

        return self

    @model_validator(mode="after")
    def validate_manual_approve_fields(self) -> "CaseworkerManualDecisionPayload":
        """Enforces positive approved amount and forbids rejection reason on approval.

        Why enforce approved_amount > 0.0 and reject rejection_reason?
        Under financial clearing invariants, a manual approval without a positive financial
        allowance cannot be cleared over NPCI/PFMS banking rails. Simultaneously, retaining any
        legacy or accidental rejection text on an approved claim violates state integrity and
        pollutes downstream audit records.
        """
        if self.governance_decision == GovernanceDecision.MANUAL_APPROVE:
            if self.approved_amount is None or self.approved_amount <= 0.0:
                raise ValueError("approved_amount > 0.0 is required for MANUAL_APPROVE")
            if self.rejection_reason is not None:
                raise ValueError("rejection_reason must be None for MANUAL_APPROVE")
        return self

    @model_validator(mode="after")
    def validate_manual_reject_fields(self) -> "CaseworkerManualDecisionPayload":
        """Enforces mandatory rejection justification and forbids approved amount on rejection.

        Why mandate rejection_reason and forbid approved_amount?
        Under citizen transparency mandates, every negative determination requires an explicit,
        legally defensible rejection reason to support citizen appeal workflows. Permitting a
        financial allowance on a rejected case violates financial clearing rules.
        """
        if self.governance_decision == GovernanceDecision.MANUAL_REJECT:
            if not self.rejection_reason or not self.rejection_reason.strip():
                raise ValueError("rejection_reason is required for MANUAL_REJECT")
            if self.approved_amount is not None:
                raise ValueError("approved_amount must be None for MANUAL_REJECT")
        return self

    @model_validator(mode="after")
    def validate_request_info_fields(self) -> "CaseworkerManualDecisionPayload":
        """Forbids both financial amount and rejection reason when requesting more info.

        Why exclude terminal attributes during information clarification requests?
        Requesting more information (`REQUEST_MORE_INFO`) transitions the claim into an intermediate
        conversational loop. Assigning a payout or rejection verdict would prematurely bias
        and corrupt subsequent automated re-evaluation passes once the citizen submits new data.
        """
        if self.governance_decision == GovernanceDecision.REQUEST_MORE_INFO:
            if self.approved_amount is not None:
                raise ValueError("approved_amount must be None for REQUEST_MORE_INFO")
            if self.rejection_reason is not None:
                raise ValueError("rejection_reason must be None for REQUEST_MORE_INFO")
        return self
