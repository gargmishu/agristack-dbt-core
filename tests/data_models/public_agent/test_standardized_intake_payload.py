from datetime import UTC, datetime
from typing import Final

import pytest
from pydantic import ValidationError

from src.data_models.common import (
    ChannelType,
    LanguageLocale,
    PayloadType,
    StructureLevel,
)
from src.data_models.public_agent import PublicAgentStandardizedIntakePayload

VALID_CITIZEN_TOKEN: Final[str] = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"  # noqa: S105


def test_standardized_intake_payload_valid() -> None:
    payload = PublicAgentStandardizedIntakePayload(
        session_id="sess_12345678",
        tokenized_citizen_id=VALID_CITIZEN_TOKEN,
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale=LanguageLocale.HINDI,
        unprocessed_input_content="Mujhe PM KISAN kist ki jankari chahiye",
        received_at=datetime.now(UTC),
    )
    assert payload.channel_type == ChannelType.WHATSAPP
    assert payload.language_locale == LanguageLocale.HINDI


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
    with pytest.raises(ValidationError, match="IVR_VOICE channel strictly requires AUDIO"):
        PublicAgentStandardizedIntakePayload(
            session_id="sess_12345678",
            tokenized_citizen_id=VALID_CITIZEN_TOKEN,
            channel_type=ChannelType.IVR_VOICE,
            payload_type=PayloadType.TEXT,  # IVR strictly requires AUDIO
            structure_level=StructureLevel.FREE_TEXT,
            unprocessed_input_content="Query text",
            received_at=datetime.now(UTC),
        )


def test_standardized_intake_payload_ussd_modality_mismatch() -> None:
    with pytest.raises(ValidationError, match="USSD channel strictly requires TEXT"):
        PublicAgentStandardizedIntakePayload(
            session_id="sess_12345678",
            tokenized_citizen_id=VALID_CITIZEN_TOKEN,
            channel_type=ChannelType.USSD,
            payload_type=PayloadType.AUDIO,
            structure_level=StructureLevel.DTMF_SELECTION,
            unprocessed_input_content="https://storage.agristack.gov.in/audio/recording.wav",
            received_at=datetime.now(UTC),
        )


def test_standardized_intake_payload_sms_modality_mismatch() -> None:
    with pytest.raises(ValidationError, match="SMS channel strictly requires TEXT"):
        PublicAgentStandardizedIntakePayload(
            session_id="sess_12345678",
            tokenized_citizen_id=VALID_CITIZEN_TOKEN,
            channel_type=ChannelType.SMS,
            payload_type=PayloadType.AUDIO,
            structure_level=StructureLevel.FREE_TEXT,
            unprocessed_input_content="https://storage.agristack.gov.in/audio/recording.wav",
            received_at=datetime.now(UTC),
        )

    valid_sms = PublicAgentStandardizedIntakePayload(
        session_id="sess_12345678",
        tokenized_citizen_id=VALID_CITIZEN_TOKEN,
        channel_type=ChannelType.SMS,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        unprocessed_input_content="SMS query",
        received_at=datetime.now(UTC),
    )
    assert valid_sms.channel_type == ChannelType.SMS


def test_standardized_intake_payload_whatsapp_audio_structure_mismatch() -> None:
    with pytest.raises(ValidationError, match="WHATSAPP AUDIO payload strictly requires FREE_TEXT"):
        PublicAgentStandardizedIntakePayload(
            session_id="sess_12345678",
            tokenized_citizen_id=VALID_CITIZEN_TOKEN,
            channel_type=ChannelType.WHATSAPP,
            payload_type=PayloadType.AUDIO,
            structure_level=StructureLevel.DTMF_SELECTION,
            unprocessed_input_content="https://storage.agristack.gov.in/audio/recording.wav",
            received_at=datetime.now(UTC),
        )


def test_standardized_intake_payload_whatsapp_text_structure_mismatch() -> None:
    with pytest.raises(
        ValidationError,
        match="WHATSAPP TEXT payload requires FREE_TEXT or MENU_SELECTION",
    ):
        PublicAgentStandardizedIntakePayload(
            session_id="sess_12345678",
            tokenized_citizen_id=VALID_CITIZEN_TOKEN,
            channel_type=ChannelType.WHATSAPP,
            payload_type=PayloadType.TEXT,
            structure_level=StructureLevel.DTMF_SELECTION,
            unprocessed_input_content="1*2*101",
            received_at=datetime.now(UTC),
        )


def test_standardized_intake_payload_valid_ussd_dtmf() -> None:
    payload = PublicAgentStandardizedIntakePayload(
        session_id="sess_12345678",
        tokenized_citizen_id=VALID_CITIZEN_TOKEN,
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
        tokenized_citizen_id=VALID_CITIZEN_TOKEN,
        channel_type=ChannelType.IVR_VOICE,
        payload_type=PayloadType.AUDIO,
        structure_level=StructureLevel.FREE_TEXT,
        unprocessed_input_content="https://storage.agristack.gov.in/audio/recording.wav",
        received_at=datetime.now(UTC),
    )
    assert payload.channel_type == ChannelType.IVR_VOICE


def test_standardized_intake_payload_invalid_audio_url() -> None:
    with pytest.raises(ValidationError, match="must be a valid signed HTTP/HTTPS URL"):
        PublicAgentStandardizedIntakePayload(
            session_id="sess_12345678",
            tokenized_citizen_id=VALID_CITIZEN_TOKEN,
            channel_type=ChannelType.IVR_VOICE,
            payload_type=PayloadType.AUDIO,
            structure_level=StructureLevel.FREE_TEXT,
            unprocessed_input_content="not_a_valid_url",
            received_at=datetime.now(UTC),
        )


def test_standardized_intake_payload_invalid_dtmf_format() -> None:
    with pytest.raises(ValidationError, match="must match DTMF keypad pattern"):
        PublicAgentStandardizedIntakePayload(
            session_id="sess_12345678",
            tokenized_citizen_id=VALID_CITIZEN_TOKEN,
            channel_type=ChannelType.USSD,
            payload_type=PayloadType.TEXT,
            structure_level=StructureLevel.DTMF_SELECTION,
            unprocessed_input_content="1*abc*2",  # Letters not allowed in DTMF
            received_at=datetime.now(UTC),
        )


def test_standardized_intake_payload_menu_selection_limits() -> None:
    valid_menu = PublicAgentStandardizedIntakePayload(
        session_id="sess_12345678",
        tokenized_citizen_id=VALID_CITIZEN_TOKEN,
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.MENU_SELECTION,
        unprocessed_input_content="Apply for wheat subsidy",
        received_at=datetime.now(UTC),
    )
    assert valid_menu.structure_level == StructureLevel.MENU_SELECTION

    with pytest.raises(ValidationError, match="cannot exceed 256 characters"):
        PublicAgentStandardizedIntakePayload(
            session_id="sess_12345678",
            tokenized_citizen_id=VALID_CITIZEN_TOKEN,
            channel_type=ChannelType.WHATSAPP,
            payload_type=PayloadType.TEXT,
            structure_level=StructureLevel.MENU_SELECTION,
            unprocessed_input_content="a" * 300,
            received_at=datetime.now(UTC),
        )


def test_standardized_intake_payload_empty_content() -> None:
    with pytest.raises(ValidationError, match="String should have at least 1 character"):
        PublicAgentStandardizedIntakePayload(
            session_id="sess_12345678",
            tokenized_citizen_id=VALID_CITIZEN_TOKEN,
            channel_type=ChannelType.WHATSAPP,
            payload_type=PayloadType.TEXT,
            structure_level=StructureLevel.FREE_TEXT,
            unprocessed_input_content="   ",  # Whitespace-only
            received_at=datetime.now(UTC),
        )


def test_standardized_intake_payload_valid_whatsapp_audio() -> None:
    payload = PublicAgentStandardizedIntakePayload(
        session_id="sess_12345678",
        tokenized_citizen_id=VALID_CITIZEN_TOKEN,
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.AUDIO,
        structure_level=StructureLevel.FREE_TEXT,
        unprocessed_input_content="https://storage.agristack.gov.in/audio/whatsapp_note.ogg",
        received_at=datetime.now(UTC),
    )
    assert payload.channel_type == ChannelType.WHATSAPP
    assert payload.payload_type == PayloadType.AUDIO


def test_standardized_intake_payload_whatsapp_invalid_modality() -> None:
    with pytest.raises(
        ValidationError, match="WHATSAPP channel requires AUDIO or TEXT payload_type"
    ):
        PublicAgentStandardizedIntakePayload(
            session_id="sess_12345678",
            tokenized_citizen_id=VALID_CITIZEN_TOKEN,
            channel_type=ChannelType.WHATSAPP,
            payload_type=PayloadType.IMAGE,
            structure_level=StructureLevel.FREE_TEXT,
            unprocessed_input_content="https://storage.agristack.gov.in/images/photo.jpg",
            received_at=datetime.now(UTC),
        )
