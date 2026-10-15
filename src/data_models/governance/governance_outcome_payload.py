"""Layer 4 Governance Outcome payload schema.

Represents authoritative adjudication verdicts, state transitions, and disbursement actions.

See: decisions/step2.0_canonical_domain_schemas.md#governance-outcome-payload
See: decisions/step2.3_governance_flows_and_state_transitions.md
"""

from pydantic import Field, model_validator

from src.data_models.common import (
    AiConfidenceScore,
    DisbursementStatus,
    DisbursementTxnId,
    EligibilityStatus,
    EscalationCaseId,
    ExtractionPayloadId,
    GovernanceAction,
    RejectionReasonCode,
    SessionId,
    StrictBaseModel,
    UtcTimestamp,
)

__all__ = ["GovernanceOutcomePayload"]


class GovernanceOutcomePayload(StrictBaseModel):
    """Data model representing an authoritative governance adjudication verdict.

    Encapsulates the adjudication action, entitlement status, financial clearing keys, and
    audit justifications.

    Invariants:
    - Approvals (`AUTO_APPROVE`, `AUTOMATED_PAYOUT`, `MANUAL_APPROVE`): Require
      `disbursement_txn_id`
      and forbid rejection fields.
    - Escalations (`ROUTE_FOR_MANUAL_REVIEW`, `HUMAN_REVIEW`, `REQUEST_MORE_INFO`): Require
      `escalation_case_id`
      and forbid `disbursement_txn_id`.
    - Rejections (`AUTO_REJECT`, `MANUAL_REJECT`): Require `rejection_reason` and
      `rejection_explanation`,
      and forbid `disbursement_txn_id`.

    See: decisions/step2.0_canonical_domain_schemas.md#governance-outcome-payload
    See: decisions/step2.3_governance_flows_and_state_transitions.md (Section 4.1)
    """

    session_id: SessionId
    payload_id: ExtractionPayloadId
    ai_confidence_score: AiConfidenceScore
    eligibility_status: EligibilityStatus = Field(
        ...,
        description="Computed citizen scheme eligibility status from DPI registry cross-matching",
    )
    governance_action: GovernanceAction = Field(
        ..., description="Automated or manual governance routing action"
    )
    evaluated_at: UtcTimestamp = Field(
        ...,
        description="UTC timestamp when automated governance evaluation or review was rendered",
    )
    disbursement_txn_id: DisbursementTxnId | None = Field(
        default=None,
        description=(
            "Idempotency tracking key generated at approval time for "
            "AUTO_APPROVE / MANUAL_APPROVE / AUTOMATED_PAYOUT"
        ),
    )
    disbursement_status: DisbursementStatus | None = Field(
        default=None,
        description=(
            "Initialized to PENDING at decision time; transitioned to INITIATED upon "
            "wire dispatch; updated to SUCCESS/FAILED/RETURNED upon bank callback"
        ),
    )
    escalation_case_id: EscalationCaseId | None = Field(
        default=None,
        description=(
            "Incident ticket tracking key (SPP-CASE-YYYY-XXXXXX) required for "
            "manual review routing, info requests, and caseworker adjudications"
        ),
    )
    rejection_reason: RejectionReasonCode | None = Field(
        default=None,
        description="Populated for AUTO_REJECT / MANUAL_REJECT",
    )
    review_notes: str | None = Field(
        default=None,
        min_length=5,
        max_length=2000,
        description="Internal caseworker audit notes carried from manual adjudication",
    )

    @model_validator(mode="after")
    def validate_auto_approve_fields(self) -> "GovernanceOutcomePayload":
        """Enforces state matrix invariants for automated approval and payout outcomes.

        For automated approvals (`AUTO_APPROVE` and `AUTOMATED_PAYOUT`), the system must
        decouple
        governance adjudication from financial clearing by establishing an idempotent
        transaction
        key (`disbursement_txn_id`) initialized to `PENDING` status. To guarantee clean
        auditability
        and prevent state confusion, all human adjudication fields (`escalation_case_id`,
        `review_notes`) and rejection reasons must be absent.
        """
        if self.governance_action in (
            GovernanceAction.AUTO_APPROVE,
            GovernanceAction.AUTOMATED_PAYOUT,
        ):
            if not self.disbursement_txn_id:
                raise ValueError(
                    f"disbursement_txn_id is required for action {self.governance_action}"
                )
            if self.disbursement_status is None:
                raise ValueError(
                    f"disbursement_status is required for action {self.governance_action}"
                )
            if self.rejection_reason is not None:
                raise ValueError(
                    f"rejection_reason must be None for action {self.governance_action}"
                )
            if self.escalation_case_id is not None:
                raise ValueError(
                    f"escalation_case_id must be None for action {self.governance_action}"
                )
            if self.review_notes is not None:
                raise ValueError(f"review_notes must be None for action {self.governance_action}")
        return self

    @model_validator(mode="after")
    def validate_manual_approve_fields(self) -> "GovernanceOutcomePayload":
        """Enforces state matrix invariants for human caseworker approval decisions.

        When a caseworker approves a staged claim (`MANUAL_APPROVE`), the payout transaction
        keys
        must be assigned to initiate wire clearing. To preserve system auditability
        invariants,
        the
        outcome must explicitly bind to the upstream escalation ticket
        (`escalation_case_id`)
        and
        carry non-empty officer audit notes (`review_notes`) explaining the justification.
        """
        if self.governance_action == GovernanceAction.MANUAL_APPROVE:
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
        return self

    @model_validator(mode="after")
    def validate_auto_reject_fields(self) -> "GovernanceOutcomePayload":
        """Enforces state matrix invariants for automated rules engine rejections.

        When an application fails automated threshold or eligibility gates (`AUTO_REJECT`),
        a
        deterministic rejection justification (`rejection_reason`) is strictly required.
        Financial
        disbursement keys and human escalation context must be completely omitted to prevent
        illegal
        state transitions or accidental financial clearing.
        """
        if self.governance_action == GovernanceAction.AUTO_REJECT:
            if self.rejection_reason is None:
                raise ValueError("rejection_reason is required for AUTO_REJECT")
            if self.disbursement_txn_id is not None:
                raise ValueError("disbursement_txn_id must be None for AUTO_REJECT")
            if self.disbursement_status is not None:
                raise ValueError("disbursement_status must be None for AUTO_REJECT")
            if self.escalation_case_id is not None:
                raise ValueError("escalation_case_id must be None for AUTO_REJECT")
            if self.review_notes is not None:
                raise ValueError("review_notes must be None for AUTO_REJECT")
        return self

    @model_validator(mode="after")
    def validate_manual_reject_fields(self) -> "GovernanceOutcomePayload":
        """Enforces state matrix invariants for caseworker manual adjudication rejections.

        When an officer rejects a case (`MANUAL_REJECT`), both an explicit rejection
        justification
        (`rejection_reason`) and officer audit notes (`review_notes`) are mandatory. The
        outcome
        must reference the staged escalation ticket (`escalation_case_id`), while financial
        payout
        keys remain strictly forbidden.
        """
        if self.governance_action == GovernanceAction.MANUAL_REJECT:
            if self.rejection_reason is None:
                raise ValueError("rejection_reason is required for MANUAL_REJECT")
            if not self.escalation_case_id:
                raise ValueError("escalation_case_id is required for MANUAL_REJECT")
            if self.disbursement_txn_id is not None:
                raise ValueError("disbursement_txn_id must be None for MANUAL_REJECT")
            if self.disbursement_status is not None:
                raise ValueError("disbursement_status must be None for MANUAL_REJECT")
            if self.review_notes is None:
                raise ValueError("review_notes is required for MANUAL_REJECT")
        return self

    @model_validator(mode="after")
    def validate_review_action_fields(self) -> "GovernanceOutcomePayload":
        """Enforces state matrix invariants for intermediate escalation and review routing outcomes.

        For non-terminal actions (`ROUTE_FOR_MANUAL_REVIEW`, `HUMAN_REVIEW`,
        `REQUEST_MORE_INFO`),
        the rules engine halts automated disbursement and routes the claim for intervention.
        This
        requires an active escalation incident ticket (`escalation_case_id`). Financial
        clearing
        attributes, rejection verdicts, and review notes must remain absent until terminal
        adjudication occurs.
        """
        review_actions = {
            GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
            GovernanceAction.HUMAN_REVIEW,
            GovernanceAction.REQUEST_MORE_INFO,
        }
        if self.governance_action in review_actions:
            if not self.escalation_case_id:
                raise ValueError(
                    f"escalation_case_id is required for action {self.governance_action}"
                )
            if self.disbursement_txn_id is not None:
                raise ValueError(
                    f"disbursement_txn_id must be None for action {self.governance_action}"
                )
            if self.disbursement_status is not None:
                raise ValueError(
                    f"disbursement_status must be None for action {self.governance_action}"
                )
            if self.rejection_reason is not None:
                raise ValueError(
                    f"rejection_reason must be None for action {self.governance_action}"
                )
            if self.review_notes is not None:
                raise ValueError(f"review_notes must be None for action {self.governance_action}")
        return self
