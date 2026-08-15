"""Multichannel confirmation dispatch outcome data model."""

from pydantic import Field

from src.data_models.common import StrictBaseModel
from src.data_models.delivery.outbound_confirmation_payload import (
    OutboundConfirmationPayload,
)
from src.data_models.delivery.transmission_ack import TransmissionAck


class ConfirmationDispatchResult(StrictBaseModel):
    """End-to-end confirmation preparation and carrier dispatch outcome."""

    payload: OutboundConfirmationPayload = Field(
        ...,
        description="Channel-adapted confirmation payload generated for transmission",
    )
    transmission_ack: TransmissionAck = Field(
        ...,
        description="Authoritative carrier transmission acknowledgment receipt",
    )
