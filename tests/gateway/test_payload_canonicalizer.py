from datetime import UTC, datetime

from src.data_models.common import ChannelType, PayloadType, StructureLevel
from src.data_models.raw_ingress import (
    IvrIngressPayload,
    UssdIngressPayload,
    WhatsAppIngressPayload,
)
from src.gateway import IngressCanonicalizer


def test_canonicalize_whatsapp_text() -> None:
    canonicalizer = IngressCanonicalizer()
    payload = WhatsAppIngressPayload(
        session_id="sess_12345678",
        originating_phone_number="+919876543210",
        channel_message_id="wamid.HBgLOTE5ODc2NTQzMjEwFQIAERgSQTU1MzI0MTk0Nzc3MzRCOUEwAA==",
        payload_type=PayloadType.TEXT,
        text_body="Mujhe PM KISAN kist ki jankari chahiye",
        received_at=datetime.now(UTC),
    )

    intake = canonicalizer.canonicalize(payload, language_locale="hi-IN")
    assert intake.session_id == "sess_12345678"
    assert intake.channel_type == ChannelType.WHATSAPP
    assert intake.payload_type == PayloadType.TEXT
    assert intake.structure_level == StructureLevel.FREE_TEXT
    assert intake.unprocessed_input_content == "Mujhe PM KISAN kist ki jankari chahiye"
    assert len(intake.tokenized_citizen_id) == 64


def test_canonicalize_whatsapp_audio() -> None:
    canonicalizer = IngressCanonicalizer()
    payload = WhatsAppIngressPayload(
        session_id="sess_12345678",
        originating_phone_number="+919876543210",
        channel_message_id="wamid.HBgLOTE5ODc2NTQzMjEwFQIAERgSQTU1MzI0MTk0Nzc3MzRCOUEwAA==",
        payload_type=PayloadType.AUDIO,
        audio_recording_url="https://s3.ap-south-1.amazonaws.com/bhashini/audio.ogg",
        duration_seconds=15,
        received_at=datetime.now(UTC),
    )

    intake = canonicalizer.canonicalize(payload)
    assert intake.channel_type == ChannelType.WHATSAPP
    assert intake.payload_type == PayloadType.AUDIO
    assert intake.structure_level == StructureLevel.FREE_TEXT
    assert intake.unprocessed_input_content == "https://s3.ap-south-1.amazonaws.com/bhashini/audio.ogg"


def test_canonicalize_ivr() -> None:
    canonicalizer = IngressCanonicalizer()
    payload = IvrIngressPayload(
        session_id="sess_12345678",
        originating_phone_number="+919876543210",
        audio_recording_url="https://sip-gateway.telecom.in/call.wav",
        duration_seconds=30,
        received_at=datetime.now(UTC),
    )

    intake = canonicalizer.canonicalize(payload)
    assert intake.channel_type == ChannelType.IVR_VOICE
    assert intake.payload_type == PayloadType.AUDIO
    assert intake.structure_level == StructureLevel.FREE_TEXT
    assert intake.unprocessed_input_content == "https://sip-gateway.telecom.in/call.wav"


def test_canonicalize_ussd() -> None:
    canonicalizer = IngressCanonicalizer()
    payload = UssdIngressPayload(
        session_id="sess_12345678",
        originating_phone_number="+919876543210",
        ussd_service_code="*147#",
        ussd_user_digit_selection="1*2*9876543210",
        received_at=datetime.now(UTC),
    )

    intake = canonicalizer.canonicalize(payload)
    assert intake.channel_type == ChannelType.USSD
    assert intake.payload_type == PayloadType.TEXT
    assert intake.structure_level == StructureLevel.DTMF_SELECTION
    assert intake.unprocessed_input_content == "1*2*9876543210"
