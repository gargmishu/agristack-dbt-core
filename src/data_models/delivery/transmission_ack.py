"""Carrier transmission acknowledgment receipt data model."""

from datetime import UTC, datetime

from pydantic import Field, HttpUrl

from src.data_models.common import (
    ChannelType,
    DeliveryStatus,
    SessionId,
    StrictBaseModel,
    UtcTimestamp,
)


class TransmissionAck(StrictBaseModel):
    """Authoritative carrier transmission acknowledgment receipt."""

    interface_id: str = Field(
        ...,
        min_length=1,
        description="Configured carrier interface or gateway identifier",
    )
    channel_type: ChannelType = Field(
        ...,
        description="Ingress/egress communication channel type",
    )
    session_id: SessionId = Field(
        ...,
        description="Canonical session tracking identifier",
    )
    status: DeliveryStatus = Field(
        default=DeliveryStatus.DELIVERED,
        description="Transmission delivery status outcome",
    )
    message_id: str | None = Field(
        default=None,
        description="External carrier message identifier (e.g., WhatsApp wamid.xxx)",
    )
    audio_playback_url: HttpUrl | None = Field(
        default=None,
        description="Synthesized voice audio stream URL for IVR playback",
    )
    message: str | None = Field(
        default=None,
        description="Transmitted message text or USSD menu response string",
    )
    acknowledged_at: UtcTimestamp = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when transmission was acknowledged by the carrier",
    )
