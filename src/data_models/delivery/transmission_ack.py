"""Carrier transmission acknowledgment receipt data model."""

from datetime import UTC, datetime

from pydantic import Field

from src.data_models.common import (
    ChannelType,
    NotificationDeliveryStatus,
    SessionId,
    StrictBaseModel,
    UtcTimestamp,
)


class TransmissionAck(StrictBaseModel):
    """Authoritative carrier transmission wire receipt."""

    interface_id: str = Field(
        ...,
        min_length=3,
        max_length=128,
        description=(
            "Configured carrier interface or gateway identifier (e.g. WHATSAPP_GATEWAY_DEFAULT)"
        ),
    )
    channel_type: ChannelType = Field(
        ...,
        description="Ingress/egress communication channel type",
    )
    session_id: SessionId = Field(
        ...,
        description="Canonical session tracking identifier",
    )
    status: NotificationDeliveryStatus = Field(
        default=NotificationDeliveryStatus.DELIVERED,
        description="Transmission delivery status outcome",
    )
    carrier_reference_id: str = Field(
        ...,
        min_length=4,
        max_length=128,
        description=(
            "Unique carrier dispatch reference ID "
            "(e.g. wamid.xxx, sip-call-id, ussd-sig-id, sms-dr-id)"
        ),
    )
    acknowledged_at: UtcTimestamp = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when transmission was acknowledged by the carrier",
    )
