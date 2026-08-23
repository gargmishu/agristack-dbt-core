"""Multichannel notification dispatch outcome data model."""

from pydantic import Field

from src.data_models.common import StrictBaseModel
from src.data_models.notification.outbound_notification_payload import (
    OutboundNotificationPayload,
)
from src.data_models.notification.transmission_ack import TransmissionAck


class NotificationDispatchResult(StrictBaseModel):
    """Data model representing the outcome of an outbound notification dispatch.

    Pairs the generated channel-adapted notification payload with the carrier transmission
    acknowledgment.

    Attributes:
        payload: Channel-adapted notification payload generated for transmission.
        transmission_ack: Authoritative carrier transmission acknowledgment receipt.

    See: decisions/step3.5_adaptive_multichannel_confirmation_delivery.md
    """

    payload: OutboundNotificationPayload = Field(
        ...,
        description="Channel-adapted notification payload generated for transmission",
    )
    transmission_ack: TransmissionAck = Field(
        ...,
        description="Authoritative carrier transmission acknowledgment receipt",
    )
