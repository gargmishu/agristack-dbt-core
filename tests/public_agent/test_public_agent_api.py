from datetime import UTC, datetime

import pytest

from src.data_models.common import ChannelType, PayloadType, StructureLevel
from src.data_models.public_agent import PublicAgentStandardizedIntakePayload
from src.public_agent import PublicAgentApi


@pytest.mark.asyncio
async def test_public_agent_api_submit_valid_payload() -> None:
    api = PublicAgentApi()
    payload = PublicAgentStandardizedIntakePayload(
        session_id="sess_12345678",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        channel_type=ChannelType.IVR_VOICE,
        payload_type=PayloadType.AUDIO,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale="hi-IN",
        unprocessed_input_content="https://sip-gateway.telecom.in/audio/voice_call.wav",
        received_at=datetime.now(UTC),
    )

    ret_payload, validation = await api.submit_payload(payload)
    assert ret_payload.session_id == "sess_12345678"
    assert validation.is_valid is True
    assert validation.requires_nlu_extraction is True
