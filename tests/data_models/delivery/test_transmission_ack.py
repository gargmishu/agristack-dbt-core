"""Unit tests for TransmissionAck data model."""

import pytest
from pydantic import HttpUrl, ValidationError

from src.data_models.common import ChannelType, DeliveryStatus
from src.data_models.delivery import TransmissionAck


def test_transmission_ack_valid() -> None:
    ack = TransmissionAck(
        interface_id="WHATSAPP_GATEWAY_DEFAULT",
        channel_type=ChannelType.WHATSAPP,
        session_id="sess_12345678",
        status=DeliveryStatus.DELIVERED,
        message_id="wamid.HBgLOTE5",
        message="Claim Approved",
    )
    assert ack.interface_id == "WHATSAPP_GATEWAY_DEFAULT"
    assert ack.channel_type == ChannelType.WHATSAPP
    assert ack.session_id == "sess_12345678"
    assert ack.status == DeliveryStatus.DELIVERED
    assert ack.message_id == "wamid.HBgLOTE5"
    assert ack.message == "Claim Approved"
    assert ack.audio_playback_url is None
    assert ack.acknowledged_at is not None


def test_transmission_ack_ivr_with_audio_url() -> None:
    ack = TransmissionAck(
        interface_id="IVR_GATEWAY_DEFAULT",
        channel_type=ChannelType.IVR_VOICE,
        session_id="sess_12345678",
        status=DeliveryStatus.DELIVERED,
        audio_playback_url=HttpUrl("https://bhashini.ai/audio.wav"),
        message="Aapka aavedan swikrit ho gaya hai.",
    )
    assert ack.channel_type == ChannelType.IVR_VOICE
    assert str(ack.audio_playback_url) == "https://bhashini.ai/audio.wav"


def test_transmission_ack_invalid_empty_interface() -> None:
    with pytest.raises(ValidationError):
        TransmissionAck(
            interface_id="",
            channel_type=ChannelType.SMS,
            session_id="sess_12345678",
        )
