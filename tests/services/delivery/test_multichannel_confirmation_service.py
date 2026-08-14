"""Unit tests for MultichannelConfirmationService."""

import pytest

from src.data_models.common import (
    ChannelType,
    DeliveryStatus,
    GovernanceAction,
    LanguageLocale,
)
from src.data_models.delivery import MAX_USSD_CHARACTERS
from src.services.ai.bhashini_service import BhashiniService
from src.services.delivery import (
    ConfirmationRequest,
    MultichannelConfirmationService,
)


@pytest.fixture
def delivery_service() -> MultichannelConfirmationService:
    return MultichannelConfirmationService.from_default()


@pytest.mark.asyncio
async def test_prepare_whatsapp_auto_approve(
    delivery_service: MultichannelConfirmationService,
) -> None:
    req = ConfirmationRequest(
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
    req = ConfirmationRequest(
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
    req = ConfirmationRequest(
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
    req = ConfirmationRequest(
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
    req = ConfirmationRequest(
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
    req = ConfirmationRequest(
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
        req = ConfirmationRequest(
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
    req = ConfirmationRequest(
        session_id="sess_12345678",
        channel_type=ChannelType.SMS,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-981245",
    )
    payload = await delivery_service.prepare_confirmation(req)
    assert payload.channel_type == ChannelType.SMS
    assert "TXN-2026-981245" in payload.formatted_message
    assert "DBT" in payload.formatted_message


def test_custom_bhashini_injection() -> None:
    custom_bhashini = BhashiniService()
    service = MultichannelConfirmationService(bhashini_service=custom_bhashini)
    assert service._bhashini_service is custom_bhashini
