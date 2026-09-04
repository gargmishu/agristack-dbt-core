"""Outbound multichannel notification request payload schema."""

from pydantic import Field, model_validator

from src.data_models.common import (
    ChannelType,
    DisbursementTxnId,
    DomainEntityKey,
    EscalationCaseId,
    GovernanceAction,
    LanguageLocale,
    RejectionReasonCode,
    SessionId,
    StrictBaseModel,
)

__all__ = ["NotificationRequestPayload"]


class NotificationRequestPayload(StrictBaseModel):
    """Data model representing a request to generate and dispatch an outbound notification.

    Encapsulates recipient channel targeting, governance determination outcome, and
    contextual parameters.

    Invariants:
    - Approvals require `disbursement_txn_id`.
    - Escalations require `escalation_case_id`.
    - Rejections require `rejection_reason`.
    - Clarifications (`REQUEST_MORE_INFO`) require `missing_entity`.

    See: decisions/step3.5_adaptive_multichannel_confirmation_delivery.md
    """

    session_id: SessionId
    channel_type: ChannelType
    governance_action: GovernanceAction
    language_locale: LanguageLocale = LanguageLocale.ENGLISH
    disbursement_txn_id: DisbursementTxnId | None = Field(
        default=None,
        description="Populated for automated or manual approvals",
    )
    escalation_case_id: EscalationCaseId | None = Field(
        default=None,
        description="Populated for caseworker escalation reviews",
    )
    rejection_reason: RejectionReasonCode | None = Field(
        default=None,
        description="Populated when governance action is AUTO_REJECT or MANUAL_REJECT",
    )
    missing_entity: DomainEntityKey | None = Field(
        default=None,
        description="Populated when governance action is REQUEST_MORE_INFO / clarification",
    )

    @model_validator(mode="after")
    def validate_action_specific_requirements(self) -> "NotificationRequestPayload":
        """Enforces mandatory field matrix depending on governance action."""
        if self.governance_action.is_approval and not self.disbursement_txn_id:
            raise ValueError(
                f"disbursement_txn_id is required for approval action '{self.governance_action}'"
            )
        if self.governance_action.is_review and not self.escalation_case_id:
            raise ValueError(
                f"escalation_case_id is required for review action '{self.governance_action}'"
            )
        if self.governance_action.is_rejection and not self.rejection_reason:
            raise ValueError(
                f"rejection_reason is required for rejection action '{self.governance_action}'"
            )
        if self.governance_action == GovernanceAction.REQUEST_MORE_INFO and not self.missing_entity:
            raise ValueError("missing_entity is required for action 'REQUEST_MORE_INFO'")
        return self
