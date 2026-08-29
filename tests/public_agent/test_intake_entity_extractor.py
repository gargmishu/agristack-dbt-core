from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from src.data_models.common import (
    ApplicationIntent,
    ChannelType,
    DomainEntityKey,
    LanguageLocale,
    PayloadType,
    StructureLevel,
)
from src.data_models.public_agent import PublicAgentStandardizedIntakePayload
from src.public_agent.intake_entity_extractor import IntakeEntityExtractor
from src.services.ai import MockBhashiniService, MockSlmExtractor

MOCK_CITIZEN_TOKEN = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"  # noqa: S105


@pytest.mark.asyncio
async def test_intake_entity_extractor_structured_menu_bypass() -> None:
    extractor = IntakeEntityExtractor()
    intake = PublicAgentStandardizedIntakePayload(
        session_id="sess_ussd_bypass_1",
        tokenized_citizen_id=MOCK_CITIZEN_TOKEN,
        channel_type=ChannelType.USSD,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.DTMF_SELECTION,
        language_locale=LanguageLocale.HINDI,
        unprocessed_input_content="1*2*101",
        received_at=datetime.now(UTC),
    )

    extracted = await extractor.extract_entities(intake)
    assert extracted.is_structured_menu_bypass is True
    assert extracted.ai_confidence_score == 1.0
    assert extracted.application_intent == ApplicationIntent.APPLY_SUBSIDY
    assert extracted.domain_entities[DomainEntityKey.DISTRICT] == "Karnal"
    assert extracted.domain_entities[DomainEntityKey.CROP_NAME] == "Wheat"


@pytest.mark.asyncio
async def test_intake_entity_extractor_audio_transcription() -> None:
    extractor = IntakeEntityExtractor()
    intake = PublicAgentStandardizedIntakePayload(
        session_id="sess_ivr_audio_1",
        tokenized_citizen_id=MOCK_CITIZEN_TOKEN,
        channel_type=ChannelType.IVR_VOICE,
        payload_type=PayloadType.AUDIO,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale=LanguageLocale.HINDI,
        unprocessed_input_content="https://sip-gateway.telecom.in/audio/voice_call.wav",
        received_at=datetime.now(UTC),
    )

    extracted = await extractor.extract_entities(intake)
    assert extracted.is_structured_menu_bypass is False
    assert extracted.application_intent == ApplicationIntent.APPLY_SUBSIDY
    assert extracted.ai_confidence_score >= 0.90  # noqa: PLR2004


@pytest.mark.asyncio
async def test_intake_entity_extractor_audio_failure_fallback() -> None:
    mock_bhashini = MockBhashiniService()
    mock_bhashini.transcribe_audio = AsyncMock(side_effect=RuntimeError("ASR Timeout"))  # type: ignore[method-assign]

    extractor = IntakeEntityExtractor(bhashini_service=mock_bhashini)
    intake = PublicAgentStandardizedIntakePayload(
        session_id="sess_ivr_fail_1",
        tokenized_citizen_id=MOCK_CITIZEN_TOKEN,
        channel_type=ChannelType.IVR_VOICE,
        payload_type=PayloadType.AUDIO,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale=LanguageLocale.HINDI,
        unprocessed_input_content="https://sip-gateway.telecom.in/audio/voice_call.wav",
        received_at=datetime.now(UTC),
    )

    extracted = await extractor.extract_entities(intake)
    assert extracted.application_intent == ApplicationIntent.UNKNOWN
    assert extracted.ai_confidence_score == 0.40  # noqa: PLR2004
    assert extracted.domain_entities == {}


@pytest.mark.asyncio
async def test_intake_entity_extractor_slm_none_fallback() -> None:
    mock_slm = MockSlmExtractor()
    mock_slm.extract_entities = AsyncMock(return_value=None)  # type: ignore[method-assign]

    extractor = IntakeEntityExtractor(slm_extractor=mock_slm)
    intake = PublicAgentStandardizedIntakePayload(
        session_id="sess_text_fail_1",
        tokenized_citizen_id=MOCK_CITIZEN_TOKEN,
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale=LanguageLocale.HINDI,
        unprocessed_input_content="Some unparseable text",
        received_at=datetime.now(UTC),
    )

    extracted = await extractor.extract_entities(intake)
    assert extracted.application_intent == ApplicationIntent.UNKNOWN
    assert extracted.ai_confidence_score == 0.40  # noqa: PLR2004
    assert extracted.domain_entities == {}
