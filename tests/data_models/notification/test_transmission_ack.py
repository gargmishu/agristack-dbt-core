"""Unit tests for TransmissionAck data model."""

import pytest
from pydantic import ValidationError

from src.data_models.common import ChannelType, NotificationDeliveryStatus
from src.data_models.notification import TransmissionAck


def test_transmission_ack_valid() -> None:
    ack = TransmissionAck(
        interface_id="WHATSAPP_GATEWAY_DEFAULT",
        channel_type=ChannelType.WHATSAPP,
        session_id="sess_12345678",
        status=NotificationDeliveryStatus.DELIVERED,
        carrier_reference_id="wamid.HBgLOTE5",
    )
    assert ack.interface_id == "WHATSAPP_GATEWAY_DEFAULT"
    assert ack.channel_type == ChannelType.WHATSAPP
    assert ack.session_id == "sess_12345678"
    assert ack.status == NotificationDeliveryStatus.DELIVERED
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
            status=NotificationDeliveryStatus.DELIVERED,
            carrier_reference_id=f"ref-{channel.value}",
        )
        assert ack.channel_type == channel
        assert ack.carrier_reference_id == f"ref-{channel.value}"


def test_transmission_ack_invalid_short_interface() -> None:
    # min_length is 3
    with pytest.raises(ValidationError):
        TransmissionAck(
            interface_id="GW",  # 2 chars < 3
            channel_type=ChannelType.SMS,
            session_id="sess_12345678",
            carrier_reference_id="sms-dr-123",
        )


def test_transmission_ack_invalid_short_carrier_reference_id() -> None:
    # min_length is 4
    with pytest.raises(ValidationError):
        TransmissionAck(
            interface_id="SMS_GATEWAY_DEFAULT",
            channel_type=ChannelType.SMS,
            session_id="sess_12345678",
            carrier_reference_id="123",  # 3 chars < 4
        )


def test_transmission_ack_invalid_exceeds_max_length() -> None:
    # max_length is 128
    with pytest.raises(ValidationError):
        TransmissionAck(
            interface_id="A" * 129,
            channel_type=ChannelType.SMS,
            session_id="sess_12345678",
            carrier_reference_id="sms-dr-123",
        )
