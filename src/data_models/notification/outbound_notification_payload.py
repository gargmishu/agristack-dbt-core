"""Outbound multichannel notification delivery payload schema (Step 12)."""

from pydantic import Field, HttpUrl, model_validator

from src.data_models.common import (
    ChannelType,
    GovernanceAction,
    LanguageLocale,
    NotificationDeliveryStatus,
    SessionId,
    StrictBaseModel,
    UtcTimestamp,
)

# GSM 7-bit SS7/SIGTRAN maximum plain text character ceiling for USSD menus
MAX_USSD_CHARACTERS = 160

__all__ = [
    "MAX_USSD_CHARACTERS",
    "OutboundNotificationPayload",
]


class OutboundNotificationPayload(StrictBaseModel):
    """Data model representing a channel-adapted outbound notification message.

    Encapsulates the rendered message text and optional audio playback stream for outbound
    dispatch.

    Invariants:
    - `formatted_message` must contain non-empty, non-whitespace content.
    - For `ChannelType.USSD`, `formatted_message` length is strictly capped at 160
      characters.

    See: decisions/step3.5_adaptive_multichannel_confirmation_delivery.md
    """

    session_id: SessionId
    channel_type: ChannelType
    governance_action: GovernanceAction
    formatted_message: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Channel-adapted plain text, rich markdown card, or menu response",
    )
    delivered_at: UtcTimestamp = Field(
        ...,
        description="UTC timestamp when notification receipt was generated and dispatched",
    )
    language_locale: LanguageLocale = LanguageLocale.ENGLISH
    delivery_status: NotificationDeliveryStatus = NotificationDeliveryStatus.DELIVERED
    audio_playback_url: HttpUrl | None = Field(
        default=None,
        description="Pre-signed synthesized TTS audio stream URL for IVR voice playback",
    )

    @model_validator(mode="after")
    def validate_ussd_character_ceiling(self) -> "OutboundNotificationPayload":
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
