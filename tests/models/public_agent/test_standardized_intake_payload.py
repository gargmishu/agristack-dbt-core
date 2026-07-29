from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.models.common import ChannelType, PayloadType, StructureLevel
from src.models.public_agent import PublicAgentStandardizedIntakePayload


def test_standardized_intake_payload_valid() -> None:
    payload = PublicAgentStandardizedIntakePayload(
        session_id="sess_12345678",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale="hi-IN",
        unprocessed_input_content="Mujhe PM KISAN kist ki jankari chahiye",
        received_at=datetime.now(UTC),
    )
    assert payload.channel_type == ChannelType.WHATSAPP
    assert payload.language_locale == "hi-IN"


def test_standardized_intake_payload_invalid_hmac_length() -> None:
    with pytest.raises(ValidationError):
        PublicAgentStandardizedIntakePayload(
            session_id="sess_12345678",
            tokenized_citizen_id="short_token",  # Must be 64-char hex string
            channel_type=ChannelType.WHATSAPP,
            payload_type=PayloadType.TEXT,
            structure_level=StructureLevel.FREE_TEXT,
            unprocessed_input_content="Query text",
            received_at=datetime.now(UTC),
        )


def test_standardized_intake_payload_ivr_modality_mismatch() -> None:
    with pytest.raises(ValidationError) as exc:
        PublicAgentStandardizedIntakePayload(
            session_id="sess_12345678",
            tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
            channel_type=ChannelType.IVR_VOICE,
            payload_type=PayloadType.TEXT,  # IVR strictly requires AUDIO
            structure_level=StructureLevel.FREE_TEXT,
            unprocessed_input_content="Query text",
            received_at=datetime.now(UTC),
        )
    assert "IVR_VOICE channel strictly requires AUDIO payload_type" in str(exc.value)


def test_standardized_intake_payload_valid_ussd_dtmf() -> None:
    payload = PublicAgentStandardizedIntakePayload(
        session_id="sess_12345678",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        channel_type=ChannelType.USSD,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.DTMF_SELECTION,
        unprocessed_input_content="1*2*9876543210",
        received_at=datetime.now(UTC),
    )
    assert payload.structure_level == StructureLevel.DTMF_SELECTION


def test_standardized_intake_payload_valid_ivr_audio_url() -> None:
    payload = PublicAgentStandardizedIntakePayload(
        session_id="sess_12345678",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        channel_type=ChannelType.IVR_VOICE,
        payload_type=PayloadType.AUDIO,
        structure_level=StructureLevel.FREE_TEXT,
        unprocessed_input_content="https://storage.agristack.gov.in/audio/recording.wav",
        received_at=datetime.now(UTC),
    )
    assert payload.channel_type == ChannelType.IVR_VOICE


def test_standardized_intake_payload_invalid_audio_url() -> None:
    with pytest.raises(ValidationError) as exc:
        PublicAgentStandardizedIntakePayload(
            session_id="sess_12345678",
            tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
            channel_type=ChannelType.IVR_VOICE,
            payload_type=PayloadType.AUDIO,
            structure_level=StructureLevel.FREE_TEXT,
            unprocessed_input_content="not_a_valid_url",
            received_at=datetime.now(UTC),
        )
    assert "must be a valid signed HTTP/HTTPS URL" in str(exc.value)


def test_standardized_intake_payload_invalid_dtmf_format() -> None:
    with pytest.raises(ValidationError) as exc:
        PublicAgentStandardizedIntakePayload(
            session_id="sess_12345678",
            tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
            channel_type=ChannelType.USSD,
            payload_type=PayloadType.TEXT,
            structure_level=StructureLevel.DTMF_SELECTION,
            unprocessed_input_content="1*abc*2",  # Letters not allowed in DTMF
            received_at=datetime.now(UTC),
        )
    assert "must match DTMF keypad pattern" in str(exc.value)


def test_standardized_intake_payload_empty_content() -> None:
    with pytest.raises(ValidationError) as exc:
        PublicAgentStandardizedIntakePayload(
            session_id="sess_12345678",
            tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
            channel_type=ChannelType.WHATSAPP,
            payload_type=PayloadType.TEXT,
            structure_level=StructureLevel.FREE_TEXT,
            unprocessed_input_content="   ",  # Whitespace-only
            received_at=datetime.now(UTC),
        )
    assert "cannot be empty or whitespace-only" in str(exc.value)
