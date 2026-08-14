"""Outbound multichannel confirmation request payload schema."""

from pydantic import Field

from src.data_models.common import (
    ChannelType,
    DisbursementTxnId,
    EscalationCaseId,
    GovernanceAction,
    LanguageLocale,
    SessionId,
    StrictBaseModel,
)


class ConfirmationRequestPayload(StrictBaseModel):
    """Input request contract for generating outbound multichannel confirmation (Step 12).

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
    rejection_reason: str | None = Field(
        default=None,
        description="Populated when governance action is AUTO_REJECT or MANUAL_REJECT",
    )
    missing_entity: str | None = Field(
        default=None,
        description="Populated when governance action is REQUEST_MORE_INFO / clarification",
    )
