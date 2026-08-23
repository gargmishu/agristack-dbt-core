from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from src.data_models.common import (
    ChannelType,
    LanguageLocale,
    PayloadType,
    StructureLevel,
)
from src.data_models.public_agent import PublicAgentStandardizedIntakePayload
from src.public_agent import PublicAgentApi
from src.public_agent.intake_payload_evaluator import (
    IntakeEvaluationResult,
    IntakePayloadEvaluator,
)


@pytest.mark.asyncio
async def test_public_agent_api_submit_valid_payload() -> None:
    api = PublicAgentApi()
    payload = PublicAgentStandardizedIntakePayload(
        session_id="sess_12345678",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        channel_type=ChannelType.IVR_VOICE,
        payload_type=PayloadType.AUDIO,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale=LanguageLocale.HINDI,
        unprocessed_input_content="https://sip-gateway.telecom.in/audio/voice_call.wav",
        received_at=datetime.now(UTC),
    )

    ret_payload, evaluation = await api.submit_payload(payload)
    assert ret_payload.session_id == "sess_12345678"
    assert evaluation.is_valid is True
    assert evaluation.requires_nlu_extraction is True


@pytest.mark.asyncio
async def test_public_agent_api_rejects_invalid_evaluator_outcome() -> None:
    mock_evaluator = MagicMock(spec=IntakePayloadEvaluator)
    mock_evaluator.evaluate_payload.return_value = IntakeEvaluationResult(
        is_valid=False,
        requires_nlu_extraction=False,
        evaluation_message="Malformed structural directive",
    )

    api = PublicAgentApi(evaluator=mock_evaluator)
    payload = PublicAgentStandardizedIntakePayload(
        session_id="sess_12345678",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale=LanguageLocale.HINDI,
        unprocessed_input_content="Mera khet",
        received_at=datetime.now(UTC),
    )

    with pytest.raises(ValueError, match="Invalid intake payload: Malformed structural directive"):
        await api.submit_payload(payload)
