from datetime import UTC, datetime

import pytest
from pydantic import HttpUrl, ValidationError

from src.config import DEFAULT_IVR_INTERFACE
from src.connectors import IvrConnector
from src.data_models.common import ChannelType, GovernanceAction, NotificationDeliveryStatus
from src.data_models.notification import OutboundNotificationPayload, TransmissionAck
from src.data_models.raw_ingress import IvrIngressPayload

EXPECTED_DURATION = 45


@pytest.mark.asyncio
async def test_ivr_connector_valid_session() -> None:
    connector = IvrConnector()
    payload_data = {
        "session_id": "sess_12345678",
        "originating_phone_number": "+919876543210",
        "audio_recording_url": "https://sip-gateway.telecom.in/audio/call_987.wav",
        "audio_duration_seconds": EXPECTED_DURATION,
        "received_at": datetime.now(UTC).isoformat(),
    }
    result = await connector.process_call_session(payload_data)
    assert isinstance(result, IvrIngressPayload)
    assert result.audio_duration_seconds == EXPECTED_DURATION
    assert str(result.audio_recording_url) == "https://sip-gateway.telecom.in/audio/call_987.wav"


@pytest.mark.asyncio
async def test_ivr_connector_invalid_audio_url() -> None:
    connector = IvrConnector()
    invalid_payload = {
        "session_id": "sess_12345678",
        "originating_phone_number": "+919876543210",
        "audio_recording_url": "not_a_valid_url",
        "audio_duration_seconds": EXPECTED_DURATION,
        "received_at": datetime.now(UTC).isoformat(),
    }
    with pytest.raises(ValidationError):
        await connector.process_call_session(invalid_payload)


@pytest.mark.asyncio
async def test_ivr_connector_invalid_duration_zero() -> None:
    connector = IvrConnector()
    invalid_payload = {
        "session_id": "sess_12345678",
        "originating_phone_number": "+919876543210",
        "audio_recording_url": "https://sip-gateway.telecom.in/audio/call_987.wav",
        "audio_duration_seconds": 0,  # Min duration is 1 second
        "received_at": datetime.now(UTC).isoformat(),
    }
    with pytest.raises(ValidationError):
        await connector.process_call_session(invalid_payload)


@pytest.mark.asyncio
async def test_ivr_connector_send_outbound_notification() -> None:
    connector = IvrConnector(interface_id="CUSTOM_SIP_TRUNK_01")
    assert connector.interface_id == "CUSTOM_SIP_TRUNK_01"

    payload = OutboundNotificationPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.IVR_VOICE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        delivery_status=NotificationDeliveryStatus.DELIVERED,
        formatted_message="Aapka aavedan swikrit ho gaya hai.",
        audio_playback_url=HttpUrl("https://bhashini.ai/audio_1.wav"),
        disbursement_txn_id="TXN-2026-981245",
        delivered_at=datetime.now(UTC),
    )
    result = await connector.send_outbound_notification(payload)
    assert isinstance(result, TransmissionAck)
    assert result.interface_id == "CUSTOM_SIP_TRUNK_01"
    assert result.channel_type == ChannelType.IVR_VOICE
    assert result.session_id == "sess_12345678"
    assert result.status == NotificationDeliveryStatus.DELIVERED
    assert result.carrier_reference_id.startswith("sip-call-")


def test_ivr_connector_factories(monkeypatch: pytest.MonkeyPatch) -> None:
    default_conn = IvrConnector()
    assert default_conn.interface_id == DEFAULT_IVR_INTERFACE

    monkeypatch.setenv("IVR_INTERFACE_ID", "ENV_SIP_TRUNK_02")
    env_conn = IvrConnector()
    assert env_conn.interface_id == "ENV_SIP_TRUNK_02"
