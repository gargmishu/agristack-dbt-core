"""Unit tests for OutboundNotificationPayload schema."""

from datetime import UTC, datetime

import pytest
from pydantic import HttpUrl, ValidationError

from src.data_models.common import (
    ChannelType,
    GovernanceAction,
    LanguageLocale,
    NotificationDeliveryStatus,
)
from src.data_models.notification import (
    MAX_USSD_CHARACTERS,
    OutboundNotificationPayload,
)


def test_outbound_payload_valid_whatsapp() -> None:
    payload = OutboundNotificationPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.WHATSAPP,
        language_locale=LanguageLocale.ENGLISH,
        governance_action=GovernanceAction.AUTO_APPROVE,
        delivery_status=NotificationDeliveryStatus.DELIVERED,
        formatted_message="*AgriStack Relief Approved!* Txn: TXN-2026-981245.",
        delivered_at=datetime.now(UTC),
    )
    assert payload.session_id == "sess_12345678"
    assert payload.channel_type == ChannelType.WHATSAPP
    assert payload.delivery_status == NotificationDeliveryStatus.DELIVERED


def test_outbound_payload_valid_ivr_voice() -> None:
    payload = OutboundNotificationPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.IVR_VOICE,
        language_locale=LanguageLocale.HINDI,
        governance_action=GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
        formatted_message="Aapka aavedan jaanch ke liye bhej diya gaya hai.",
        audio_playback_url=HttpUrl("https://bhashini-gateway.ai/synth/2026_hi_response_824921.wav"),
        delivered_at=datetime.now(UTC),
    )
    assert payload.channel_type == ChannelType.IVR_VOICE
    assert payload.audio_playback_url is not None
    assert (
        str(payload.audio_playback_url)
        == "https://bhashini-gateway.ai/synth/2026_hi_response_824921.wav"
    )


def test_outbound_payload_valid_ussd() -> None:
    payload = OutboundNotificationPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.USSD,
        governance_action=GovernanceAction.AUTO_APPROVE,
        formatted_message="AgriStack: Claim Approved. Txn: TXN-2026-100200.",
        delivered_at=datetime.now(UTC),
    )
    assert payload.channel_type == ChannelType.USSD
    assert len(payload.formatted_message) <= MAX_USSD_CHARACTERS


def test_outbound_payload_empty_message_rejected() -> None:
    with pytest.raises(ValidationError) as exception_info:
        OutboundNotificationPayload(
            session_id="sess_12345678",
            channel_type=ChannelType.WHATSAPP,
            governance_action=GovernanceAction.AUTO_APPROVE,
            formatted_message="   ",
            delivered_at=datetime.now(UTC),
        )
    assert "String should have at least 1 character" in str(exception_info.value)


def test_outbound_payload_ussd_length_exceeded_rejected() -> None:
    with pytest.raises(ValidationError) as exception_info:
        OutboundNotificationPayload(
            session_id="sess_12345678",
            channel_type=ChannelType.USSD,
            governance_action=GovernanceAction.AUTO_APPROVE,
            formatted_message="A" * (MAX_USSD_CHARACTERS + 1),
            delivered_at=datetime.now(UTC),
        )
    assert f"exceeds maximum {MAX_USSD_CHARACTERS} character limit" in str(exception_info.value)
