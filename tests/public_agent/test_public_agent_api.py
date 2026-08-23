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
from src.data_models.raw_ingress import WhatsAppIngressPayload
from src.gateway import IngestionFirewall, RateLimiter, ZeroTrustIdentityTokenizer
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


@pytest.mark.asyncio
async def test_public_agent_api_process_claim_intake_e2e() -> None:
    api = PublicAgentApi()
    payload = PublicAgentStandardizedIntakePayload(
        session_id="sess_e2e_100",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale=LanguageLocale.HINDI,
        unprocessed_input_content="Mera khet 2.5 acre hai, fasal gehu, survey 101/2, zila Meerut",
        received_at=datetime.now(UTC),
    )

    result = await api.process_claim_intake(payload)
    assert result.session_id == "sess_e2e_100"
    assert result.evaluation_result.is_valid is True
    assert result.orchestration_result.governance_outcome.governance_action.is_approval
    assert result.transmission_ack.carrier_reference_id.startswith("wamid.")


@pytest.mark.asyncio
async def test_public_agent_api_process_claim_intake_reprompt() -> None:
    api = PublicAgentApi()
    payload = PublicAgentStandardizedIntakePayload(
        session_id="sess_reprompt_100",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale=LanguageLocale.HINDI,
        unprocessed_input_content="missing crop details",
        received_at=datetime.now(UTC),
    )

    result = await api.process_claim_intake(payload, attempt_count=1)
    assert result.session_id == "sess_reprompt_100"
    assert result.orchestration_result.requires_reprompt is True
    assert result.transmission_ack.carrier_reference_id.startswith("wamid.")


@pytest.mark.asyncio
async def test_public_agent_api_process_raw_ingress_e2e(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGRISTACK_PEPPER_SECRET", "test_pepper_public_agent_123")
    api = PublicAgentApi()
    raw_whatsapp = WhatsAppIngressPayload(
        session_id="sess_raw_200",
        originating_phone_number="+919876543210",
        channel_message_id="wamid.123456",
        payload_type=PayloadType.TEXT,
        text_body="Mera khet 2.5 acre hai, fasal gehu, survey 101/2, zila Meerut",
        received_at=datetime.now(UTC),
    )

    result = await api.process_raw_ingress(
        raw_payload=raw_whatsapp,
    )
    assert result.session_id == "sess_raw_200"
    assert result.channel_type == ChannelType.WHATSAPP
    assert result.orchestration_result.governance_outcome.governance_action.is_approval
    assert result.transmission_ack.carrier_reference_id.startswith("wamid.")


@pytest.mark.asyncio
async def test_public_agent_api_with_custom_firewall_injection() -> None:
    custom_firewall = IngestionFirewall(
        tokenizer=ZeroTrustIdentityTokenizer(pepper_key="a" * 32),
        rate_limiter=RateLimiter(),
    )
    api = PublicAgentApi(firewall=custom_firewall)
    assert api.firewall is custom_firewall
