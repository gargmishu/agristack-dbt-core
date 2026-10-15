"""Caseworker portal review outcome and adjudication payload schema."""

from pydantic import Field, model_validator

from src.data_models.common import (
    EscalationCaseId,
    GovernanceAction,
    RejectionReasonCode,
    StrictBaseModel,
    UtcTimestamp,
)

__all__ = ["CaseworkerReviewOutcomePayload"]


class CaseworkerReviewOutcomePayload(StrictBaseModel):
    """Data model representing an adjudication decision submitted by a human caseworker.

    Encapsulates the officer's determination, financial allowances, rejection reasons, and
    audit notes. It governs human-in-the-loop resolutions for complex claims that
    exceeded automated confidence thresholds or triggered policy escalation gates.

    Invariants:
    - `MANUAL_APPROVE`: Requires `approved_amount > 0.0` and forbids `rejection_reason`.
    - `MANUAL_REJECT`: Requires `rejection_reason` and forbids `approved_amount`.
    - `REQUEST_MORE_INFO`: Forbids both `approved_amount` and `rejection_reason`.

    See: decisions/step2.0_canonical_domain_schemas.md#442-caseworker-review-decision-payload
    See: decisions/step2.3_governance_flows_and_state_transitions.md (Section 4.4)
    """

    escalation_case_id: EscalationCaseId
    reviewer_id: str = Field(
        ...,
        min_length=5,
        max_length=128,
        description="UUID or Officer ID of caseworker submitting decision",
    )
    governance_action: GovernanceAction = Field(
        ..., description="Must strictly be MANUAL_APPROVE, MANUAL_REJECT, or REQUEST_MORE_INFO"
    )
    review_notes: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Mandatory audit justification note or information request details",
    )
    reviewed_at: UtcTimestamp = Field(
        ..., description="UTC timestamp when officer submitted review outcome on dashboard"
    )
    approved_amount: float | None = Field(None, ge=0.0, description="Populated for MANUAL_APPROVE")
    rejection_reason: RejectionReasonCode | None = Field(
        None, description="Populated for MANUAL_REJECT"
    )

    @model_validator(mode="after")
    def validate_action_type_and_audit_notes(self) -> "CaseworkerReviewOutcomePayload":
        """Enforces allowed manual review actions and non-empty caseworker audit justification.

        Why restrict action types and enforce non-empty review_notes?
        Automated actions (e.g. AUTO_APPROVE or AUTOMATED_PAYOUT) are strictly forbidden
        within
        caseworker payloads to prevent automated system spoofing through administrative
        portals.
        Furthermore, national welfare audit regulations require every human adjudication to
        carry
        an immutable, meaningful textual justification (`review_notes`) in the governance
        ledger.
        """
        allowed_actions = {
            GovernanceAction.MANUAL_APPROVE,
            GovernanceAction.MANUAL_REJECT,
            GovernanceAction.REQUEST_MORE_INFO,
        }
        if self.governance_action not in allowed_actions:
            raise ValueError(
                "CaseworkerReviewOutcomePayload action must be MANUAL_APPROVE, "
                f"MANUAL_REJECT, or REQUEST_MORE_INFO, got {self.governance_action}"
            )

        return self

    @model_validator(mode="after")
    def validate_manual_approve_fields(self) -> "CaseworkerReviewOutcomePayload":
        """Enforces positive approved amount and forbids rejection reason on approval.

        Why enforce approved_amount > 0.0 and reject rejection_reason?
        Under financial clearing invariants, a manual approval without a positive financial
        allowance cannot be cleared over NPCI/PFMS banking rails. Simultaneously, retaining
        any
        legacy or accidental rejection text on an approved claim violates state integrity
        and
        pollutes downstream audit records.
        """
        if self.governance_action == GovernanceAction.MANUAL_APPROVE:
            if self.approved_amount is None or self.approved_amount <= 0.0:
                raise ValueError("approved_amount > 0.0 is required for MANUAL_APPROVE")
            if self.rejection_reason is not None:
                raise ValueError("rejection_reason must be None for MANUAL_APPROVE")
        return self

    @model_validator(mode="after")
    def validate_manual_reject_fields(self) -> "CaseworkerReviewOutcomePayload":
        """Enforces mandatory rejection justification and forbids approved amount on rejection.

        Why mandate rejection_reason and forbid approved_amount?
        Under citizen transparency mandates, every negative determination requires an
        explicit,
        legally defensible rejection reason to support citizen appeal workflows. Permitting
        a
        financial allowance on a rejected case violates financial clearing rules.
        """
        if self.governance_action == GovernanceAction.MANUAL_REJECT:
            if not self.rejection_reason or not self.rejection_reason.strip():
                raise ValueError("rejection_reason is required for MANUAL_REJECT")
            if self.approved_amount is not None:
                raise ValueError("approved_amount must be None for MANUAL_REJECT")
        return self

    @model_validator(mode="after")
    def validate_request_info_fields(self) -> "CaseworkerReviewOutcomePayload":
        """Forbids both financial amount and rejection reason when requesting more info.

        Why exclude terminal attributes during information clarification requests?
        Requesting more information (`REQUEST_MORE_INFO`) transitions the claim into an
        intermediate
        conversational loop. Assigning a payout or rejection verdict would prematurely bias
        and corrupt subsequent automated re-evaluation passes once the citizen submits new
        data.
        """
        if self.governance_action == GovernanceAction.REQUEST_MORE_INFO:
            if self.approved_amount is not None:
                raise ValueError("approved_amount must be None for REQUEST_MORE_INFO")
            if self.rejection_reason is not None:
                raise ValueError("rejection_reason must be None for REQUEST_MORE_INFO")
        return self
