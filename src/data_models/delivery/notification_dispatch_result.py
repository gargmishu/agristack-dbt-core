"""Multichannel notification dispatch outcome data model."""

from pydantic import Field

from src.data_models.common import StrictBaseModel
from src.data_models.delivery.outbound_notification_payload import (
    OutboundNotificationPayload,
)
from src.data_models.delivery.transmission_ack import TransmissionAck


class NotificationDispatchResult(StrictBaseModel):
    """End-to-end notification preparation and carrier dispatch outcome."""

    payload: OutboundNotificationPayload = Field(
        ...,
        description="Channel-adapted notification payload generated for transmission",
    )
    transmission_ack: TransmissionAck = Field(
        ...,
        description="Authoritative carrier transmission acknowledgment receipt",
    )
