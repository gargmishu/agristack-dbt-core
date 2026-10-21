from datetime import UTC, datetime

import pytest

from src.data_models.common import (
    ChannelType,
    PayloadType,
)
from src.data_models.raw_ingress import WhatsAppIngressPayload
from src.gateway import IngestionFirewall, RateLimiter, ZeroTrustIdentityTokenizer
from src.public_agent import IntakeEntityExtractor, PublicAgentApi


@pytest.mark.asyncio
async def test_public_agent_api_process_raw_ingress_approval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGRISTACK_PEPPER_SECRET", "test_pepper_public_agent_123")
    api = PublicAgentApi()
    raw_whatsapp = WhatsAppIngressPayload(
        session_id="sess_e2e_100",
        originating_phone_number="+919876543210",
        channel_message_id="wamid.123456",
        payload_type=PayloadType.TEXT,
        text_body="Mera khet 2.5 acre hai, fasal gehu, survey 101/2, zila Meerut",
        received_at=datetime.now(UTC),
    )

    result = await api.process_raw_ingress(raw_payload=raw_whatsapp)
    assert result.session_id == "sess_e2e_100"
    assert result.orchestration_result.governance_outcome.governance_action.is_approval
    assert result.transmission_ack.carrier_reference_id.startswith("wamid.")


@pytest.mark.asyncio
async def test_public_agent_api_process_raw_ingress_reprompt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGRISTACK_PEPPER_SECRET", "test_pepper_public_agent_123")
    api = PublicAgentApi()
    raw_whatsapp = WhatsAppIngressPayload(
        session_id="sess_reprompt_100",
        originating_phone_number="+919876543210",
        channel_message_id="wamid.reprompt_123",
        payload_type=PayloadType.TEXT,
        text_body="missing crop details",
        received_at=datetime.now(UTC),
    )

    result = await api.process_raw_ingress(raw_payload=raw_whatsapp, attempt_count=1)
    assert result.session_id == "sess_reprompt_100"
    assert result.orchestration_result.requires_reprompt is True
    assert result.transmission_ack.carrier_reference_id.startswith("wamid.")

    crop_missing_whatsapp = WhatsAppIngressPayload(
        session_id="sess_reprompt_101",
        originating_phone_number="+919876543210",
        channel_message_id="wamid.reprompt_124",
        payload_type=PayloadType.TEXT,
        text_body="zila Karnal missing crop details",
        received_at=datetime.now(UTC),
    )
    crop_missing_result = await api.process_raw_ingress(
        raw_payload=crop_missing_whatsapp,
        attempt_count=1,
    )
    assert crop_missing_result.orchestration_result.requires_reprompt is True
    assert "crop_name" in (crop_missing_result.orchestration_result.reprompt_message or "")


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
    raw_whatsapp = WhatsAppIngressPayload(
        session_id="sess_custom_fw_1",
        originating_phone_number="+919876543210",
        channel_message_id="wamid.custom_fw",
        payload_type=PayloadType.TEXT,
        text_body="Mera khet 2.5 acre hai, fasal gehu, survey 101/2, zila Meerut",
        received_at=datetime.now(UTC),
    )
    result = await api.process_raw_ingress(raw_payload=raw_whatsapp)
    assert result.session_id == "sess_custom_fw_1"


@pytest.mark.asyncio
async def test_public_agent_api_with_custom_extractor_injection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGRISTACK_PEPPER_SECRET", "test_pepper_public_agent_123")
    custom_extractor = IntakeEntityExtractor()
    api = PublicAgentApi(extractor=custom_extractor)
    raw_whatsapp = WhatsAppIngressPayload(
        session_id="sess_custom_ext_1",
        originating_phone_number="+919876543210",
        channel_message_id="wamid.custom_ext",
        payload_type=PayloadType.TEXT,
        text_body="Mera khet 2.5 acre hai, fasal gehu, survey 101/2, zila Meerut",
        received_at=datetime.now(UTC),
    )
    result = await api.process_raw_ingress(raw_payload=raw_whatsapp)
    assert result.session_id == "sess_custom_ext_1"
    assert result.orchestration_result.governance_outcome.governance_action.is_approval
