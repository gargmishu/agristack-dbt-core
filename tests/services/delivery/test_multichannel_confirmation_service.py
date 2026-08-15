"""Unit tests for MultichannelConfirmationService."""

import pytest

from src.config import (
    DEFAULT_IVR_INTERFACE,
    DEFAULT_SMS_INTERFACE,
    DEFAULT_USSD_INTERFACE,
)
from src.connectors import (
    IvrConnector,
    SmsConnector,
    UssdConnector,
    WhatsAppConnector,
)
from src.data_models.common import (
    ChannelType,
    DeliveryStatus,
    DomainEntityKey,
    GovernanceAction,
    LanguageLocale,
    RejectionReasonCode,
)
from src.data_models.delivery import (
    MAX_USSD_CHARACTERS,
    ConfirmationDispatchResult,
    ConfirmationRequestPayload,
    TransmissionAck,
)
from src.services.ai.bhashini_service import BhashiniService
from src.services.delivery import MultichannelConfirmationService


@pytest.fixture
def delivery_service() -> MultichannelConfirmationService:
    return MultichannelConfirmationService()


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
        rejection_reason=RejectionReasonCode.INELIGIBLE_LAND_SIZE,
    )
    payload = await delivery_service.prepare_confirmation(req)
    assert "INELIGIBLE_LAND_SIZE" in payload.formatted_message
    assert "1800-180-1551" in payload.formatted_message


@pytest.mark.asyncio
async def test_prepare_whatsapp_reprompt_clarification(
    delivery_service: MultichannelConfirmationService,
) -> None:
    req = ConfirmationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.WHATSAPP,
        governance_action=GovernanceAction.REQUEST_MORE_INFO,
        missing_entity=DomainEntityKey.SURVEY_NUMBER,
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
            rejection_reason=RejectionReasonCode.DUPLICATE_CLAIM_ACTIVE_SEASON,
            missing_entity=DomainEntityKey.VILLAGE,
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
    assert isinstance(result, ConfirmationDispatchResult)
    assert result.payload.session_id == "sess_12345678"
    assert isinstance(result.transmission_ack, TransmissionAck)
    assert result.transmission_ack.channel_type == ChannelType.WHATSAPP
    assert result.transmission_ack.status == DeliveryStatus.DELIVERED
    assert result.transmission_ack.message_id is not None
    assert result.transmission_ack.message_id.startswith("wamid.")


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
    assert isinstance(result, ConfirmationDispatchResult)
    assert result.transmission_ack.interface_id == DEFAULT_IVR_INTERFACE
    assert result.transmission_ack.channel_type == ChannelType.IVR_VOICE
    assert result.transmission_ack.audio_playback_url is not None


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
    assert isinstance(result, ConfirmationDispatchResult)
    assert result.transmission_ack.interface_id == DEFAULT_USSD_INTERFACE
    assert result.transmission_ack.channel_type == ChannelType.USSD


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
    assert isinstance(result, ConfirmationDispatchResult)
    assert result.transmission_ack.interface_id == DEFAULT_SMS_INTERFACE
    assert result.transmission_ack.channel_type == ChannelType.SMS


@pytest.mark.asyncio
async def test_env_and_custom_injection_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WHATSAPP_INTERFACE_ID", "CUSTOM_WHATSAPP_ENV")
    monkeypatch.setenv("IVR_INTERFACE_ID", "CUSTOM_IVR_ENV")
    monkeypatch.setenv("USSD_INTERFACE_ID", "CUSTOM_USSD_ENV")
    monkeypatch.setenv("SMS_INTERFACE_ID", "CUSTOM_SMS_ENV")

    env_service = MultichannelConfirmationService()

    wa_req = ConfirmationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.WHATSAPP,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-981245",
    )
    wa_res = await env_service.dispatch_confirmation(wa_req)
    assert wa_res.transmission_ack.interface_id == "CUSTOM_WHATSAPP_ENV"

    ivr_req = ConfirmationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.IVR_VOICE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-981245",
    )
    ivr_res = await env_service.dispatch_confirmation(ivr_req)
    assert ivr_res.transmission_ack.interface_id == "CUSTOM_IVR_ENV"

    ussd_req = ConfirmationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.USSD,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-981245",
    )
    ussd_res = await env_service.dispatch_confirmation(ussd_req)
    assert ussd_res.transmission_ack.interface_id == "CUSTOM_USSD_ENV"

    sms_req = ConfirmationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.SMS,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-981245",
    )
    sms_res = await env_service.dispatch_confirmation(sms_req)
    assert sms_res.transmission_ack.interface_id == "CUSTOM_SMS_ENV"

    custom_whatsapp = WhatsAppConnector(interface_id="MANUAL_WHATSAPP")
    custom_ivr = IvrConnector(interface_id="MANUAL_IVR")
    custom_ussd = UssdConnector(interface_id="MANUAL_USSD")
    custom_sms = SmsConnector(interface_id="MANUAL_SMS")
    custom_service = MultichannelConfirmationService(
        bhashini_service=BhashiniService(),
        whatsapp_connector=custom_whatsapp,
        ivr_connector=custom_ivr,
        ussd_connector=custom_ussd,
        sms_connector=custom_sms,
    )
    res_custom_wa = await custom_service.dispatch_confirmation(wa_req)
    assert res_custom_wa.transmission_ack.interface_id == "MANUAL_WHATSAPP"

    res_custom_ivr = await custom_service.dispatch_confirmation(ivr_req)
    assert res_custom_ivr.transmission_ack.interface_id == "MANUAL_IVR"

    res_custom_ussd = await custom_service.dispatch_confirmation(ussd_req)
    assert res_custom_ussd.transmission_ack.interface_id == "MANUAL_USSD"

    res_custom_sms = await custom_service.dispatch_confirmation(sms_req)
    assert res_custom_sms.transmission_ack.interface_id == "MANUAL_SMS"
