"""Outbound multichannel confirmation delivery payload schema (Step 12)."""

from pydantic import Field, HttpUrl, model_validator

from src.data_models.common import (
    ChannelType,
    DisbursementTxnId,
    EscalationCaseId,
    GovernanceAction,
    LanguageLocale,
    NotificationDeliveryStatus,
    SessionId,
    StrictBaseModel,
    UtcTimestamp,
)

# GSM 7-bit SS7/SIGTRAN maximum plain text character ceiling for USSD menus
MAX_USSD_CHARACTERS = 160


class OutboundConfirmationPayload(StrictBaseModel):
    """Channel-adapted outbound confirmation receipt payload dispatched to citizen (Step 12).

    See: decisions/step3.5_adaptive_multichannel_confirmation_delivery.md
    """

    session_id: SessionId
    channel_type: ChannelType
    language_locale: LanguageLocale = LanguageLocale.ENGLISH
    governance_action: GovernanceAction
    delivery_status: NotificationDeliveryStatus = NotificationDeliveryStatus.DELIVERED
    formatted_message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Channel-adapted plain text, rich markdown card, or menu response",
    )
    audio_playback_url: HttpUrl | None = Field(
        default=None,
        description="Pre-signed synthesized TTS audio stream URL for IVR voice playback",
    )
    disbursement_txn_id: DisbursementTxnId | None = Field(
        default=None,
        description="Populated when governance action is AUTO_APPROVE or MANUAL_APPROVE",
    )
    escalation_case_id: EscalationCaseId | None = Field(
        default=None,
        description="Populated when governance action is ROUTE_FOR_MANUAL_REVIEW or HUMAN_REVIEW",
    )
    delivered_at: UtcTimestamp = Field(
        ...,
        description="UTC timestamp when confirmation receipt was generated and dispatched",
    )

    @model_validator(mode="after")
    def validate_non_empty_message(self) -> "OutboundConfirmationPayload":
        """Ensures that formatted confirmation message is not empty or whitespace."""
        if not self.formatted_message or not self.formatted_message.strip():
            raise ValueError("formatted_message cannot be empty or whitespace-only")
        return self

    @model_validator(mode="after")
    def validate_ussd_character_ceiling(self) -> "OutboundConfirmationPayload":
        """Enforces 160-character ceiling for USSD channel to prevent carrier signaling errors."""
        if (
            self.channel_type == ChannelType.USSD
            and len(self.formatted_message) > MAX_USSD_CHARACTERS
        ):
            raise ValueError(
                f"USSD message length ({len(self.formatted_message)}) exceeds "
                f"maximum {MAX_USSD_CHARACTERS} character limit"
            )
        return self
