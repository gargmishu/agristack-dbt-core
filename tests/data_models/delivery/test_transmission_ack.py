"""Unit tests for TransmissionAck data model."""

import pytest
from pydantic import ValidationError

from src.data_models.common import ChannelType, DeliveryStatus
from src.data_models.delivery import TransmissionAck


def test_transmission_ack_valid() -> None:
    ack = TransmissionAck(
        interface_id="WHATSAPP_GATEWAY_DEFAULT",
        channel_type=ChannelType.WHATSAPP,
        session_id="sess_12345678",
        status=DeliveryStatus.DELIVERED,
        carrier_reference_id="wamid.HBgLOTE5",
    )
    assert ack.interface_id == "WHATSAPP_GATEWAY_DEFAULT"
    assert ack.channel_type == ChannelType.WHATSAPP
    assert ack.session_id == "sess_12345678"
    assert ack.status == DeliveryStatus.DELIVERED
    assert ack.carrier_reference_id == "wamid.HBgLOTE5"
    assert ack.acknowledged_at is not None


def test_transmission_ack_all_channels() -> None:
    for channel in [
        ChannelType.WHATSAPP,
        ChannelType.IVR_VOICE,
        ChannelType.USSD,
        ChannelType.SMS,
    ]:
        ack = TransmissionAck(
            interface_id="CARRIER_GW_01",
            channel_type=channel,
            session_id="sess_12345678",
            status=DeliveryStatus.DELIVERED,
            carrier_reference_id=f"ref-{channel.value}",
        )
        assert ack.channel_type == channel
        assert ack.carrier_reference_id == f"ref-{channel.value}"


def test_transmission_ack_invalid_empty_interface() -> None:
    with pytest.raises(ValidationError):
        TransmissionAck(
            interface_id="",
            channel_type=ChannelType.SMS,
            session_id="sess_12345678",
            carrier_reference_id="sms-dr-123",
        )


def test_transmission_ack_invalid_empty_carrier_ref() -> None:
    with pytest.raises(ValidationError):
        TransmissionAck(
            interface_id="SMS_GATEWAY_DEFAULT",
            channel_type=ChannelType.SMS,
            session_id="sess_12345678",
            carrier_reference_id="",
        )
