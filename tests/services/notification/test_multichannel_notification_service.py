"""Unit tests for MultichannelNotificationService."""

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
    DomainEntityKey,
    GovernanceAction,
    LanguageLocale,
    NotificationDeliveryStatus,
    RejectionReasonCode,
)
from src.data_models.notification import (
    MAX_USSD_CHARACTERS,
    NotificationRequestPayload,
    TransmissionAck,
)
from src.services.ai.bhashini_service import MockBhashiniService
from src.services.notification import MultichannelNotificationService


@pytest.fixture
def delivery_service() -> MultichannelNotificationService:
    return MultichannelNotificationService()


@pytest.mark.asyncio
async def test_prepare_whatsapp_auto_approve(
    delivery_service: MultichannelNotificationService,
) -> None:
    request = NotificationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.WHATSAPP,
        governance_action=GovernanceAction.AUTO_APPROVE,
        language_locale=LanguageLocale.ENGLISH,
        disbursement_txn_id="TXN-2026-981245",
    )
    payload = await delivery_service._prepare_notification(request)
    assert payload.session_id == "sess_12345678"
    assert payload.channel_type == ChannelType.WHATSAPP
    assert payload.delivery_status == NotificationDeliveryStatus.DELIVERED
    assert "TXN-2026-981245" in payload.formatted_message
    assert "APPROVED" in payload.formatted_message
    assert payload.audio_playback_url is None


@pytest.mark.asyncio
async def test_prepare_whatsapp_manual_review(
    delivery_service: MultichannelNotificationService,
) -> None:
    request = NotificationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.WHATSAPP,
        governance_action=GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
        language_locale=LanguageLocale.ENGLISH,
        escalation_case_id="SPP-CASE-2026-100200",
    )
    payload = await delivery_service._prepare_notification(request)
    assert "SPP-CASE-2026-100200" in payload.formatted_message
    assert "District Agricultural Officer" in payload.formatted_message


@pytest.mark.asyncio
async def test_prepare_whatsapp_auto_reject(
    delivery_service: MultichannelNotificationService,
) -> None:
    request = NotificationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.WHATSAPP,
        governance_action=GovernanceAction.AUTO_REJECT,
        rejection_reason=RejectionReasonCode.INELIGIBLE_LAND_SIZE,
    )
    payload = await delivery_service._prepare_notification(request)
    assert "INELIGIBLE_LAND_SIZE" in payload.formatted_message
    assert "1800-180-1551" in payload.formatted_message


@pytest.mark.asyncio
async def test_prepare_whatsapp_reprompt_clarification(
    delivery_service: MultichannelNotificationService,
) -> None:
    request = NotificationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.WHATSAPP,
        governance_action=GovernanceAction.REQUEST_MORE_INFO,
        missing_entity=DomainEntityKey.SURVEY_NUMBER,
    )
    payload = await delivery_service._prepare_notification(request)
    assert "survey number" in payload.formatted_message
    assert "Reply directly" in payload.formatted_message


@pytest.mark.asyncio
async def test_prepare_ivr_voice_hindi_synthesis(
    delivery_service: MultichannelNotificationService,
) -> None:
    request = NotificationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.IVR_VOICE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        language_locale=LanguageLocale.HINDI,
        disbursement_txn_id="TXN-2026-981245",
    )
    payload = await delivery_service._prepare_notification(request)
    assert payload.channel_type == ChannelType.IVR_VOICE
    assert payload.audio_playback_url is not None
    assert "https://" in str(payload.audio_playback_url)
    assert "fasal rahat aavedan swikrit" in payload.formatted_message


@pytest.mark.asyncio
async def test_prepare_ivr_voice_english_synthesis(
    delivery_service: MultichannelNotificationService,
) -> None:
    request = NotificationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.IVR_VOICE,
        governance_action=GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
        language_locale=LanguageLocale.ENGLISH,
        escalation_case_id="SPP-CASE-2026-100200",
    )
    payload = await delivery_service._prepare_notification(request)
    assert payload.audio_playback_url is not None
    assert "forwarded to the district officer" in payload.formatted_message


@pytest.mark.asyncio
async def test_prepare_ussd_length_boundary(
    delivery_service: MultichannelNotificationService,
) -> None:
    for action in (
        GovernanceAction.AUTO_APPROVE,
        GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
        GovernanceAction.AUTO_REJECT,
        GovernanceAction.REQUEST_MORE_INFO,
    ):
        request = NotificationRequestPayload(
            session_id="sess_12345678",
            channel_type=ChannelType.USSD,
            governance_action=action,
            disbursement_txn_id="TXN-2026-100200",
            escalation_case_id="SPP-CASE-2026-100200",
            rejection_reason=RejectionReasonCode.DUPLICATE_CLAIM_ACTIVE_SEASON,
            missing_entity=DomainEntityKey.VILLAGE,
        )
        payload = await delivery_service._prepare_notification(request)
        assert len(payload.formatted_message) <= MAX_USSD_CHARACTERS
        assert payload.audio_playback_url is None


@pytest.mark.asyncio
async def test_prepare_sms_delivery(
    delivery_service: MultichannelNotificationService,
) -> None:
    request = NotificationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.SMS,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-981245",
    )
    payload = await delivery_service._prepare_notification(request)
    assert payload.channel_type == ChannelType.SMS
    assert "TXN-2026-981245" in payload.formatted_message
    assert "DBT" in payload.formatted_message


@pytest.mark.asyncio
async def test_dispatch_notification_whatsapp(
    delivery_service: MultichannelNotificationService,
) -> None:
    request = NotificationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.WHATSAPP,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-981245",
    )
    result = await delivery_service.dispatch_notification(request)
    assert isinstance(result, TransmissionAck)
    assert result.session_id == "sess_12345678"
    assert result.channel_type == ChannelType.WHATSAPP
    assert result.status == NotificationDeliveryStatus.DELIVERED
    assert result.carrier_reference_id.startswith("wamid.")


@pytest.mark.asyncio
async def test_dispatch_notification_ivr_voice(
    delivery_service: MultichannelNotificationService,
) -> None:
    request = NotificationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.IVR_VOICE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-981245",
    )
    result = await delivery_service.dispatch_notification(request)
    assert isinstance(result, TransmissionAck)
    assert result.interface_id == DEFAULT_IVR_INTERFACE
    assert result.channel_type == ChannelType.IVR_VOICE
    assert result.carrier_reference_id.startswith("sip-call-")


@pytest.mark.asyncio
async def test_dispatch_notification_ussd(
    delivery_service: MultichannelNotificationService,
) -> None:
    request = NotificationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.USSD,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-981245",
    )
    result = await delivery_service.dispatch_notification(request)
    assert isinstance(result, TransmissionAck)
    assert result.interface_id == DEFAULT_USSD_INTERFACE
    assert result.channel_type == ChannelType.USSD


@pytest.mark.asyncio
async def test_dispatch_notification_sms(
    delivery_service: MultichannelNotificationService,
) -> None:
    request = NotificationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.SMS,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-981245",
    )
    result = await delivery_service.dispatch_notification(request)
    assert isinstance(result, TransmissionAck)
    assert result.interface_id == DEFAULT_SMS_INTERFACE
    assert result.channel_type == ChannelType.SMS


@pytest.mark.asyncio
async def test_env_and_custom_injection_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WHATSAPP_INTERFACE_ID", "CUSTOM_WHATSAPP_ENV")
    monkeypatch.setenv("IVR_INTERFACE_ID", "CUSTOM_IVR_ENV")
    monkeypatch.setenv("USSD_INTERFACE_ID", "CUSTOM_USSD_ENV")
    monkeypatch.setenv("SMS_INTERFACE_ID", "CUSTOM_SMS_ENV")

    env_service = MultichannelNotificationService()

    whatsapp_request = NotificationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.WHATSAPP,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-981245",
    )
    whatsapp_ack = await env_service.dispatch_notification(whatsapp_request)
    assert whatsapp_ack.interface_id == "CUSTOM_WHATSAPP_ENV"

    ivr_request = NotificationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.IVR_VOICE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-981245",
    )
    ivr_ack = await env_service.dispatch_notification(ivr_request)
    assert ivr_ack.interface_id == "CUSTOM_IVR_ENV"

    ussd_request = NotificationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.USSD,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-981245",
    )
    ussd_ack = await env_service.dispatch_notification(ussd_request)
    assert ussd_ack.interface_id == "CUSTOM_USSD_ENV"

    sms_request = NotificationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.SMS,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-981245",
    )
    sms_ack = await env_service.dispatch_notification(sms_request)
    assert sms_ack.interface_id == "CUSTOM_SMS_ENV"

    custom_whatsapp = WhatsAppConnector(interface_id="MANUAL_WHATSAPP")
    custom_ivr = IvrConnector(interface_id="MANUAL_IVR")
    custom_ussd = UssdConnector(interface_id="MANUAL_USSD")
    custom_sms = SmsConnector(interface_id="MANUAL_SMS")
    custom_service = MultichannelNotificationService(
        bhashini_service=MockBhashiniService(),
        whatsapp_connector=custom_whatsapp,
        ivr_connector=custom_ivr,
        ussd_connector=custom_ussd,
        sms_connector=custom_sms,
    )
    custom_whatsapp_ack = await custom_service.dispatch_notification(whatsapp_request)
    assert custom_whatsapp_ack.interface_id == "MANUAL_WHATSAPP"

    custom_ivr_ack = await custom_service.dispatch_notification(ivr_request)
    assert custom_ivr_ack.interface_id == "MANUAL_IVR"

    custom_ussd_ack = await custom_service.dispatch_notification(ussd_request)
    assert custom_ussd_ack.interface_id == "MANUAL_USSD"

    custom_sms_ack = await custom_service.dispatch_notification(sms_request)
    assert custom_sms_ack.interface_id == "MANUAL_SMS"


@pytest.mark.asyncio
async def test_prepare_ivr_voice_rejection_hindi_and_english(
    delivery_service: MultichannelNotificationService,
) -> None:
    request_hindi = NotificationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.IVR_VOICE,
        governance_action=GovernanceAction.AUTO_REJECT,
        language_locale=LanguageLocale.HINDI,
        rejection_reason=RejectionReasonCode.INELIGIBLE_LAND_SIZE,
    )
    payload_hindi = await delivery_service._prepare_notification(request_hindi)
    assert "Aapka aavedan aswikrit kiya gaya hai" in payload_hindi.formatted_message

    request_english = NotificationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.IVR_VOICE,
        governance_action=GovernanceAction.AUTO_REJECT,
        language_locale=LanguageLocale.ENGLISH,
        rejection_reason=RejectionReasonCode.INELIGIBLE_LAND_SIZE,
    )
    payload_english = await delivery_service._prepare_notification(request_english)
    assert "Your application could not be approved" in payload_english.formatted_message


@pytest.mark.asyncio
async def test_prepare_ivr_voice_reprompt_hindi_and_english(
    delivery_service: MultichannelNotificationService,
) -> None:
    request_hindi = NotificationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.IVR_VOICE,
        governance_action=GovernanceAction.REQUEST_MORE_INFO,
        language_locale=LanguageLocale.HINDI,
        missing_entity=DomainEntityKey.BANK_ACCOUNT_LAST4,
    )
    payload_hindi = await delivery_service._prepare_notification(request_hindi)
    assert "Kripya apna" in payload_hindi.formatted_message

    request_english = NotificationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.IVR_VOICE,
        governance_action=GovernanceAction.REQUEST_MORE_INFO,
        language_locale=LanguageLocale.ENGLISH,
        missing_entity=DomainEntityKey.DISTRICT,
    )
    payload_english = await delivery_service._prepare_notification(request_english)
    assert "Please provide your" in payload_english.formatted_message


def test_format_entity_label_edge_cases() -> None:
    assert (
        MultichannelNotificationService._format_entity_label(None, is_hindi=False)
        == "required details"
    )
    assert (
        MultichannelNotificationService._format_entity_label(None, is_hindi=True)
        == "kripya vivaran"
    )
    assert (
        MultichannelNotificationService._format_entity_label(DomainEntityKey.VILLAGE, is_hindi=True)
        == "gaon"
    )
    assert (
        MultichannelNotificationService._format_entity_label(
            DomainEntityKey.VILLAGE, is_hindi=False
        )
        == "village"
    )
