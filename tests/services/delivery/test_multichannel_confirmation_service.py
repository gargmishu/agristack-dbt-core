"""Unit tests for MultichannelConfirmationService."""

import pytest

from src.config import (
    DEFAULT_SIGTRAN_INTERFACE,
    DEFAULT_SIP_TRUNK_INTERFACE,
    DEFAULT_SMS_GATEWAY,
)
from src.connectors import IvrConnector, UssdConnector, WhatsAppConnector
from src.data_models.common import (
    ChannelType,
    DeliveryStatus,
    GovernanceAction,
    LanguageLocale,
)
from src.data_models.delivery import (
    MAX_USSD_CHARACTERS,
    ConfirmationRequestPayload,
)
from src.services.ai.bhashini_service import BhashiniService
from src.services.delivery import MultichannelConfirmationService


@pytest.fixture
def delivery_service() -> MultichannelConfirmationService:
    return MultichannelConfirmationService.from_default()


@pytest.mark.asyncio
async def test_prepare_whatsapp_auto_approve(
    delivery_service: MultichannelConfirmationService,
) -> None:
    req = ConfirmationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.WHATSAPP,
        governance_action=GovernanceAction.AUTO_APPROVE,
        language_locale=LanguageLocale.ENGLISH,
        disbursement_txn_id="TXN-2026-981245",
    )
    payload = await delivery_service.prepare_confirmation(req)
    assert payload.session_id == "sess_12345678"
    assert payload.channel_type == ChannelType.WHATSAPP
    assert payload.delivery_status == DeliveryStatus.DELIVERED
    assert "TXN-2026-981245" in payload.formatted_message
    assert "APPROVED" in payload.formatted_message
    assert payload.audio_playback_url is None


@pytest.mark.asyncio
async def test_prepare_whatsapp_manual_review(
    delivery_service: MultichannelConfirmationService,
) -> None:
    req = ConfirmationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.WHATSAPP,
        governance_action=GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
        language_locale=LanguageLocale.ENGLISH,
        escalation_case_id="SPP-CASE-2026-100200",
    )
    payload = await delivery_service.prepare_confirmation(req)
    assert payload.escalation_case_id == "SPP-CASE-2026-100200"
    assert "SPP-CASE-2026-100200" in payload.formatted_message
    assert "District Agricultural Officer" in payload.formatted_message


@pytest.mark.asyncio
async def test_prepare_whatsapp_auto_reject(
    delivery_service: MultichannelConfirmationService,
) -> None:
    req = ConfirmationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.WHATSAPP,
        governance_action=GovernanceAction.AUTO_REJECT,
        rejection_reason="Ineligible land parcel size",
    )
    payload = await delivery_service.prepare_confirmation(req)
    assert "Ineligible land parcel size" in payload.formatted_message
    assert "1800-180-1551" in payload.formatted_message


@pytest.mark.asyncio
async def test_prepare_whatsapp_reprompt_clarification(
    delivery_service: MultichannelConfirmationService,
) -> None:
    req = ConfirmationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.WHATSAPP,
        governance_action=GovernanceAction.REQUEST_MORE_INFO,
        missing_entity="survey number",
    )
    payload = await delivery_service.prepare_confirmation(req)
    assert "survey number" in payload.formatted_message
    assert "Reply directly" in payload.formatted_message


@pytest.mark.asyncio
async def test_prepare_ivr_voice_hindi_synthesis(
    delivery_service: MultichannelConfirmationService,
) -> None:
    req = ConfirmationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.IVR_VOICE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        language_locale=LanguageLocale.HINDI,
        disbursement_txn_id="TXN-2026-981245",
    )
    payload = await delivery_service.prepare_confirmation(req)
    assert payload.channel_type == ChannelType.IVR_VOICE
    assert payload.audio_playback_url is not None
    assert "https://" in str(payload.audio_playback_url)
    assert "fasal rahat aavedan swikrit" in payload.formatted_message


@pytest.mark.asyncio
async def test_prepare_ivr_voice_english_synthesis(
    delivery_service: MultichannelConfirmationService,
) -> None:
    req = ConfirmationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.IVR_VOICE,
        governance_action=GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
        language_locale=LanguageLocale.ENGLISH,
        escalation_case_id="SPP-CASE-2026-100200",
    )
    payload = await delivery_service.prepare_confirmation(req)
    assert payload.audio_playback_url is not None
    assert "forwarded to the district officer" in payload.formatted_message


@pytest.mark.asyncio
async def test_prepare_ussd_length_boundary(
    delivery_service: MultichannelConfirmationService,
) -> None:
    for action in (
        GovernanceAction.AUTO_APPROVE,
        GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
        GovernanceAction.AUTO_REJECT,
        GovernanceAction.REQUEST_MORE_INFO,
    ):
        req = ConfirmationRequestPayload(
            session_id="sess_12345678",
            channel_type=ChannelType.USSD,
            governance_action=action,
            disbursement_txn_id="TXN-2026-100200",
            escalation_case_id="SPP-CASE-2026-100200",
            rejection_reason="Duplicate claim detected for active crop season",
            missing_entity="village",
        )
        payload = await delivery_service.prepare_confirmation(req)
        assert len(payload.formatted_message) <= MAX_USSD_CHARACTERS
        assert payload.audio_playback_url is None


@pytest.mark.asyncio
async def test_prepare_sms_delivery(
    delivery_service: MultichannelConfirmationService,
) -> None:
    req = ConfirmationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.SMS,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-981245",
    )
    payload = await delivery_service.prepare_confirmation(req)
    assert payload.channel_type == ChannelType.SMS
    assert "TXN-2026-981245" in payload.formatted_message
    assert "DBT" in payload.formatted_message


@pytest.mark.asyncio
async def test_dispatch_confirmation_whatsapp(
    delivery_service: MultichannelConfirmationService,
) -> None:
    req = ConfirmationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.WHATSAPP,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-981245",
    )
    result = await delivery_service.dispatch_confirmation(req)
    assert result["payload"].session_id == "sess_12345678"
    assert result["transmission_ack"]["messaging_product"] == "whatsapp"
    assert result["transmission_ack"]["status"] == DeliveryStatus.DELIVERED


@pytest.mark.asyncio
async def test_dispatch_confirmation_ivr_voice(
    delivery_service: MultichannelConfirmationService,
) -> None:
    req = ConfirmationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.IVR_VOICE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-981245",
    )
    result = await delivery_service.dispatch_confirmation(req)
    assert result["transmission_ack"]["telephony_gateway"] == DEFAULT_SIP_TRUNK_INTERFACE
    assert result["transmission_ack"]["audio_playback_url"] is not None


@pytest.mark.asyncio
async def test_dispatch_confirmation_ussd(
    delivery_service: MultichannelConfirmationService,
) -> None:
    req = ConfirmationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.USSD,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-981245",
    )
    result = await delivery_service.dispatch_confirmation(req)
    assert result["transmission_ack"]["sigtran_interface"] == DEFAULT_SIGTRAN_INTERFACE


@pytest.mark.asyncio
async def test_dispatch_confirmation_sms(
    delivery_service: MultichannelConfirmationService,
) -> None:
    req = ConfirmationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.SMS,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-981245",
    )
    result = await delivery_service.dispatch_confirmation(req)
    assert result["transmission_ack"]["sms_gateway"] == DEFAULT_SMS_GATEWAY


def test_factories_and_custom_injection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WHATSAPP_INTERFACE_ID", "CUSTOM_WHATSAPP_ENV")
    monkeypatch.setenv("IVR_SIP_TRUNK_INTERFACE_ID", "CUSTOM_IVR_ENV")
    monkeypatch.setenv("USSD_SIGTRAN_INTERFACE_ID", "CUSTOM_USSD_ENV")
    monkeypatch.setenv("SMS_GATEWAY_INTERFACE_ID", "CUSTOM_SMS_ENV")

    env_service = MultichannelConfirmationService.from_env()
    assert env_service.whatsapp_connector.interface_id == "CUSTOM_WHATSAPP_ENV"
    assert env_service.ivr_connector.interface_id == "CUSTOM_IVR_ENV"
    assert env_service.ussd_connector.interface_id == "CUSTOM_USSD_ENV"
    assert env_service.sms_gateway_id == "CUSTOM_SMS_ENV"

    custom_whatsapp = WhatsAppConnector(interface_id="MANUAL_WHATSAPP")
    custom_ivr = IvrConnector(interface_id="MANUAL_IVR")
    custom_ussd = UssdConnector(interface_id="MANUAL_USSD")
    custom_service = MultichannelConfirmationService(
        bhashini_service=BhashiniService(),
        whatsapp_connector=custom_whatsapp,
        ivr_connector=custom_ivr,
        ussd_connector=custom_ussd,
        sms_gateway_id="MANUAL_SMS",
    )
    assert custom_service.whatsapp_connector.interface_id == "MANUAL_WHATSAPP"
    assert custom_service.ivr_connector.interface_id == "MANUAL_IVR"
    assert custom_service.ussd_connector.interface_id == "MANUAL_USSD"
    assert custom_service.sms_gateway_id == "MANUAL_SMS"
