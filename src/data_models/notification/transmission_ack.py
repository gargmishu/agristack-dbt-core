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

__all__ = ["TransmissionAck"]


class TransmissionAck(StrictBaseModel):
    """Data model representing an authoritative carrier transmission wire receipt.

    Captures transport acknowledgment telemetry returned upon dispatching an outbound
    notification.

    See: decisions/step3.5_adaptive_multichannel_confirmation_delivery.md
    """

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
