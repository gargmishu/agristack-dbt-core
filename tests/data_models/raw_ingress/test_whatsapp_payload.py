from datetime import UTC, datetime

import pytest
from pydantic import HttpUrl, TypeAdapter, ValidationError

from src.data_models.common import PayloadType
from src.data_models.raw_ingress import WhatsAppIngressPayload

http_url_adapter = TypeAdapter(HttpUrl)


def test_whatsapp_ingress_valid_text() -> None:
    payload = WhatsAppIngressPayload(
        session_id="sess_12345678",
        originating_phone_number="+919876543210",
        channel_message_id="wamid.HBgLMTIzNDU2Nzg5MA==",
        payload_type=PayloadType.TEXT,
        received_at=datetime.now(UTC),
        text_body="Hello AgriStack",
    )
    assert payload.payload_type == PayloadType.TEXT
    assert payload.text_body == "Hello AgriStack"
    assert payload.audio_recording_url is None


def test_whatsapp_ingress_valid_audio() -> None:
    url = http_url_adapter.validate_python("https://storage.agristack.gov.in/audio/voice.ogg")
    payload = WhatsAppIngressPayload(
        session_id="sess_12345678",
        originating_phone_number="+919876543210",
        channel_message_id="wamid.HBgLMTIzNDU2Nzg5MA==",
        payload_type=PayloadType.AUDIO,
        received_at=datetime.now(UTC),
        audio_recording_url=url,
        duration_seconds=120,
    )
    assert payload.payload_type == PayloadType.AUDIO
    assert str(payload.audio_recording_url) == "https://storage.agristack.gov.in/audio/voice.ogg"
    assert payload.duration_seconds == 120  # noqa: PLR2004


def test_whatsapp_ingress_invalid_audio_missing_url() -> None:
    with pytest.raises(ValidationError) as exc:
        WhatsAppIngressPayload(
            session_id="sess_12345678",
            originating_phone_number="+919876543210",
            channel_message_id="wamid.HBgLMTIzNDU2Nzg5MA==",
            payload_type=PayloadType.AUDIO,
            received_at=datetime.now(UTC),
            duration_seconds=120,
        )
    assert "audio_recording_url is required" in str(exc.value)


def test_whatsapp_ingress_invalid_phone_number() -> None:
    with pytest.raises(ValidationError):
        WhatsAppIngressPayload(
            session_id="sess_12345678",
            originating_phone_number="9876543210",  # Missing leading +
            channel_message_id="wamid.HBgLMTIzNDU2Nzg5MA==",
            payload_type=PayloadType.TEXT,
            received_at=datetime.now(UTC),
            text_body="Hello",
        )
