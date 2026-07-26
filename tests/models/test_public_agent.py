from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.models.enums import ChannelType, PayloadType, StructureLevel
from src.models.public_agent import StandardizedPublicAgentPayload


def test_standardized_public_agent_valid() -> None:
    payload = StandardizedPublicAgentPayload(
        channel_session_id="sess_12345678",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale="hi-IN",
        unprocessed_input_content="Mujhe PM KISAN kist ki jankari chahiye",
        public_agent_timestamp=datetime.now(UTC),
    )
    assert payload.channel_type == ChannelType.WHATSAPP
    assert payload.language_locale == "hi-IN"


def test_standardized_public_agent_invalid_hmac_length() -> None:
    with pytest.raises(ValidationError):
        StandardizedPublicAgentPayload(
            channel_session_id="sess_12345678",
            tokenized_citizen_id="short_token",  # Must be 64-char hex string
            channel_type=ChannelType.WHATSAPP,
            payload_type=PayloadType.TEXT,
            structure_level=StructureLevel.FREE_TEXT,
            unprocessed_input_content="Query text",
            public_agent_timestamp=datetime.now(UTC),
        )


def test_standardized_public_agent_ivr_modality_mismatch() -> None:
    with pytest.raises(ValidationError) as exc:
        StandardizedPublicAgentPayload(
            channel_session_id="sess_12345678",
            tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
            channel_type=ChannelType.IVR_VOICE,
            payload_type=PayloadType.TEXT,  # IVR strictly requires AUDIO
            structure_level=StructureLevel.FREE_TEXT,
            unprocessed_input_content="Query text",
            public_agent_timestamp=datetime.now(UTC),
        )
    assert "IVR_VOICE channel strictly requires AUDIO payload_type" in str(exc.value)
