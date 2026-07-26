from datetime import UTC, datetime

import pytest
from pydantic import HttpUrl, TypeAdapter, ValidationError

from src.models.enums import PayloadType
from src.models.raw_ingress import (
    IVRIngressPayload,
    USSDIngressPayload,
    WhatsAppIngressPayload,
)

http_url_adapter = TypeAdapter(HttpUrl)


def test_whatsapp_ingress_valid_text() -> None:
    payload = WhatsAppIngressPayload(
        channel_session_id="sess_12345678",
        originating_phone_number="+919876543210",
        channel_message_id="wamid.HBgLMTIzNDU2Nzg5MA==",
        payload_type=PayloadType.TEXT,
        ingress_timestamp=datetime.now(UTC),
        text_body="Hello AgriStack",
    )
    assert payload.payload_type == PayloadType.TEXT
    assert payload.text_body == "Hello AgriStack"
    assert payload.audio_recording_url is None


def test_whatsapp_ingress_valid_audio() -> None:
    url = http_url_adapter.validate_python("https://storage.agristack.gov.in/audio/voice.ogg")
    payload = WhatsAppIngressPayload(
        channel_session_id="sess_12345678",
        originating_phone_number="+919876543210",
        channel_message_id="wamid.HBgLMTIzNDU2Nzg5MA==",
        payload_type=PayloadType.AUDIO,
        ingress_timestamp=datetime.now(UTC),
        audio_recording_url=url,
        duration_seconds=120,
    )
    assert payload.payload_type == PayloadType.AUDIO
    assert str(payload.audio_recording_url) == "https://storage.agristack.gov.in/audio/voice.ogg"
    assert payload.duration_seconds == 120  # noqa: PLR2004


def test_whatsapp_ingress_invalid_audio_missing_url() -> None:
    with pytest.raises(ValidationError) as exc:
        WhatsAppIngressPayload(
            channel_session_id="sess_12345678",
            originating_phone_number="+919876543210",
            channel_message_id="wamid.HBgLMTIzNDU2Nzg5MA==",
            payload_type=PayloadType.AUDIO,
            ingress_timestamp=datetime.now(UTC),
            duration_seconds=120,
        )
    assert "audio_recording_url is required" in str(exc.value)


def test_whatsapp_ingress_invalid_phone_number() -> None:
    with pytest.raises(ValidationError):
        WhatsAppIngressPayload(
            channel_session_id="sess_12345678",
            originating_phone_number="9876543210",  # Missing leading +
            channel_message_id="wamid.HBgLMTIzNDU2Nzg5MA==",
            payload_type=PayloadType.TEXT,
            ingress_timestamp=datetime.now(UTC),
            text_body="Hello",
        )


def test_ivr_ingress_valid() -> None:
    url = http_url_adapter.validate_python("https://storage.agristack.gov.in/ivr/call.wav")
    payload = IVRIngressPayload(
        channel_session_id="sip_call_987654321",
        originating_phone_number="+919876543210",
        audio_recording_url=url,
        duration_seconds=300,
        ingress_timestamp=datetime.now(UTC),
    )
    assert payload.duration_seconds == 300  # noqa: PLR2004


def test_ivr_ingress_duration_exceeds_ceiling() -> None:
    url = http_url_adapter.validate_python("https://storage.agristack.gov.in/ivr/call.wav")
    with pytest.raises(ValidationError):
        IVRIngressPayload(
            channel_session_id="sip_call_987654321",
            originating_phone_number="+919876543210",
            audio_recording_url=url,
            duration_seconds=601,  # Exceeds max 600s ceiling
            ingress_timestamp=datetime.now(UTC),
        )


def test_ussd_ingress_valid() -> None:
    payload = USSDIngressPayload(
        channel_session_id="ussd_sess_998877",
        originating_phone_number="+919876543210",
        ussd_service_code="*147*1*2#",
        ussd_user_digit_selection="1*2*9876543210",
        ingress_timestamp=datetime.now(UTC),
    )
    assert payload.ussd_service_code == "*147*1*2#"


def test_ussd_ingress_invalid_shortcode() -> None:
    with pytest.raises(ValidationError):
        USSDIngressPayload(
            channel_session_id="ussd_sess_998877",
            originating_phone_number="+919876543210",
            ussd_service_code="147#",  # Missing leading *
            ussd_user_digit_selection="1*2",
            ingress_timestamp=datetime.now(UTC),
        )
