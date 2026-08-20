from datetime import UTC, datetime

import pytest
from pydantic import HttpUrl

from src.data_models.common import (
    ChannelType,
    LanguageLocale,
    PayloadType,
    StructureLevel,
)
from src.data_models.raw_ingress import (
    IvrIngressPayload,
    SmsIngressPayload,
    UssdIngressPayload,
    WhatsAppIngressPayload,
)
from src.gateway import PayloadCanonicalizer

EXPECTED_TOKEN_LEN = 64


@pytest.fixture(autouse=True)
def _setup_pepper_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGRISTACK_PEPPER_SECRET", "test_canonicalizer_pepper_key")


def test_canonicalize_whatsapp_text() -> None:
    canonicalizer = PayloadCanonicalizer.from_env()
    payload = WhatsAppIngressPayload(
        session_id="sess_12345678",
        originating_phone_number="+919876543210",
        channel_message_id="wamid.HBgLOTE5ODc2NTQzMjEwFQIAERgSQTU1MzI0MTk0Nzc3MzRCOUEwAA==",
        payload_type=PayloadType.TEXT,
        text_body="Mujhe PM KISAN kist ki jankari chahiye",
        received_at=datetime.now(UTC),
    )

    intake = canonicalizer.canonicalize(payload, language_locale=LanguageLocale.HINDI)
    assert intake.session_id == "sess_12345678"
    assert intake.channel_type == ChannelType.WHATSAPP
    assert intake.payload_type == PayloadType.TEXT
    assert intake.structure_level == StructureLevel.FREE_TEXT
    assert intake.unprocessed_input_content == "Mujhe PM KISAN kist ki jankari chahiye"
    assert len(intake.tokenized_citizen_id) == EXPECTED_TOKEN_LEN


def test_canonicalize_whatsapp_audio() -> None:
    canonicalizer = PayloadCanonicalizer.from_env()
    payload = WhatsAppIngressPayload(
        session_id="sess_12345678",
        originating_phone_number="+919876543210",
        channel_message_id="wamid.HBgLOTE5ODc2NTQzMjEwFQIAERgSQTU1MzI0MTk0Nzc3MzRCOUEwAA==",
        payload_type=PayloadType.AUDIO,
        audio_recording_url=HttpUrl("https://s3.ap-south-1.amazonaws.com/bhashini/audio.ogg"),
        audio_duration_seconds=15,
        received_at=datetime.now(UTC),
    )

    intake = canonicalizer.canonicalize(payload)
    assert intake.channel_type == ChannelType.WHATSAPP
    assert intake.payload_type == PayloadType.AUDIO
    assert intake.structure_level == StructureLevel.FREE_TEXT
    assert (
        intake.unprocessed_input_content == "https://s3.ap-south-1.amazonaws.com/bhashini/audio.ogg"
    )


def test_canonicalize_ivr() -> None:
    canonicalizer = PayloadCanonicalizer.from_env()
    payload = IvrIngressPayload(
        session_id="sess_12345678",
        originating_phone_number="+919876543210",
        audio_recording_url=HttpUrl("https://sip-gateway.telecom.in/call.wav"),
        audio_duration_seconds=30,
        received_at=datetime.now(UTC),
    )

    intake = canonicalizer.canonicalize(payload)
    assert intake.channel_type == ChannelType.IVR_VOICE
    assert intake.payload_type == PayloadType.AUDIO
    assert intake.structure_level == StructureLevel.FREE_TEXT
    assert intake.unprocessed_input_content == "https://sip-gateway.telecom.in/call.wav"


def test_canonicalize_ussd() -> None:
    canonicalizer = PayloadCanonicalizer.from_env()
    payload = UssdIngressPayload(
        session_id="sess_12345678",
        originating_phone_number="+919876543210",
        ussd_service_code="*147#",
        ussd_user_digit_selection="1*2*101",
        received_at=datetime.now(UTC),
    )

    intake = canonicalizer.canonicalize(payload)
    assert intake.channel_type == ChannelType.USSD
    assert intake.payload_type == PayloadType.TEXT
    assert intake.structure_level == StructureLevel.DTMF_SELECTION
    assert intake.unprocessed_input_content == "1*2*101"


def test_canonicalize_sms() -> None:
    canonicalizer = PayloadCanonicalizer.from_env()
    payload = SmsIngressPayload(
        session_id="sess_12345678",
        originating_phone_number="+919876543210",
        channel_message_id="sms_msg_12345",
        text_body="Mujhe PM KISAN kist ki jankari chahiye",
        received_at=datetime.now(UTC),
    )

    intake = canonicalizer.canonicalize(payload, language_locale=LanguageLocale.HINDI)
    assert intake.session_id == "sess_12345678"
    assert intake.channel_type == ChannelType.SMS
    assert intake.payload_type == PayloadType.TEXT
    assert intake.structure_level == StructureLevel.FREE_TEXT
    assert intake.unprocessed_input_content == "Mujhe PM KISAN kist ki jankari chahiye"
    assert len(intake.tokenized_citizen_id) == EXPECTED_TOKEN_LEN


def test_canonicalize_redacts_embedded_pii_in_text() -> None:
    canonicalizer = PayloadCanonicalizer.from_env()
    payload = WhatsAppIngressPayload(
        session_id="sess_pii_redaction",
        originating_phone_number="+919876543210",
        channel_message_id="wamid.HBgLOTE5ODc2NTQzMjEwFQIAERgSQTU1MzI0MTk0Nzc3MzRCOUEwAA==",
        payload_type=PayloadType.TEXT,
        text_body="Mera phone 9876543210 aur Aadhaar 1234 5678 9012 hai",
        received_at=datetime.now(UTC),
    )

    intake = canonicalizer.canonicalize(payload)
    assert "[REDACTED]" in intake.unprocessed_input_content
    assert "9876543210" not in intake.unprocessed_input_content
    assert "1234 5678 9012" not in intake.unprocessed_input_content
    assert intake.unprocessed_input_content == "Mera phone [REDACTED] aur Aadhaar [REDACTED] hai"


def test_canonicalize_unsupported_payload_type() -> None:
    canonicalizer = PayloadCanonicalizer.from_env()
    with pytest.raises(ValueError, match="Unsupported ingress payload type"):
        canonicalizer.canonicalize("invalid_payload")  # type: ignore[arg-type]
