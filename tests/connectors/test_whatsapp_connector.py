from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.config import DEFAULT_WHATSAPP_INTERFACE
from src.connectors import WhatsAppConnector
from src.data_models.common import ChannelType, DeliveryStatus, GovernanceAction, PayloadType
from src.data_models.delivery import OutboundConfirmationPayload
from src.data_models.raw_ingress import WhatsAppIngressPayload

EXPECTED_DURATION = 15


@pytest.mark.asyncio
async def test_whatsapp_connector_valid_text_payload() -> None:
    connector = WhatsAppConnector()
    payload_data = {
        "session_id": "sess_12345678",
        "originating_phone_number": "+919876543210",
        "channel_message_id": "wamid.HBgLOTE5ODc2NTQzMjEwFQIAERgSQTU1MzI0MTk0Nzc3MzRCOUEwAA==",
        "payload_type": PayloadType.TEXT,
        "text_body": "Mujhe PM KISAN kist ki jankari chahiye",
        "received_at": datetime.now(UTC).isoformat(),
    }
    result = await connector.process_webhook(payload_data)
    assert isinstance(result, WhatsAppIngressPayload)
    assert result.channel_message_id.startswith("wamid.")
    assert result.text_body == "Mujhe PM KISAN kist ki jankari chahiye"


@pytest.mark.asyncio
async def test_whatsapp_connector_valid_audio_payload() -> None:
    connector = WhatsAppConnector()
    payload_data = {
        "session_id": "sess_12345678",
        "originating_phone_number": "+919876543210",
        "channel_message_id": "wamid.HBgLOTE5ODc2NTQzMjEwFQIAERgSQTU1MzI0MTk0Nzc3MzRCOUEwAA==",
        "payload_type": PayloadType.AUDIO,
        "audio_recording_url": "https://s3.ap-south-1.amazonaws.com/bhashini-audio/recordings/audio_123.ogg",
        "duration_seconds": EXPECTED_DURATION,
        "received_at": datetime.now(UTC).isoformat(),
    }
    result = await connector.process_webhook(payload_data)
    assert isinstance(result, WhatsAppIngressPayload)
    assert result.payload_type == PayloadType.AUDIO
    assert result.duration_seconds == EXPECTED_DURATION


@pytest.mark.asyncio
async def test_whatsapp_connector_invalid_phone() -> None:
    connector = WhatsAppConnector()
    invalid_payload = {
        "session_id": "sess_12345678",
        "originating_phone_number": "invalid_phone",
        "channel_message_id": "wamid.HBgLOTE5ODc2NTQzMjEwFQIAERgSQTU1MzI0MTk0Nzc3MzRCOUEwAA==",
        "payload_type": PayloadType.TEXT,
        "text_body": "Test message",
        "received_at": datetime.now(UTC).isoformat(),
    }
    with pytest.raises(ValidationError):
        await connector.process_webhook(invalid_payload)


@pytest.mark.asyncio
async def test_whatsapp_connector_invalid_message_id_short() -> None:
    connector = WhatsAppConnector()
    invalid_payload = {
        "session_id": "sess_12345678",
        "originating_phone_number": "+919876543210",
        "channel_message_id": "short",  # Min length 8
        "payload_type": PayloadType.TEXT,
        "text_body": "Test message",
        "received_at": datetime.now(UTC).isoformat(),
    }
    with pytest.raises(ValidationError):
        await connector.process_webhook(invalid_payload)


@pytest.mark.asyncio
async def test_whatsapp_connector_send_outbound_confirmation() -> None:
    connector = WhatsAppConnector(interface_id="CUSTOM_META_WHATSAPP_API")
    assert connector.interface_id == "CUSTOM_META_WHATSAPP_API"

    payload = OutboundConfirmationPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.WHATSAPP,
        governance_action=GovernanceAction.AUTO_APPROVE,
        delivery_status=DeliveryStatus.DELIVERED,
        formatted_message="Claim Approved",
        disbursement_txn_id="TXN-2026-981245",
        delivered_at=datetime.now(UTC),
    )
    result = await connector.send_outbound_confirmation(payload)
    assert result["interface_id"] == "CUSTOM_META_WHATSAPP_API"
    assert result["messaging_product"] == "whatsapp"
    assert result["session_id"] == "sess_12345678"
    assert result["status"] == DeliveryStatus.DELIVERED
    assert result["message"] == "Claim Approved"


def test_whatsapp_connector_factories(monkeypatch: pytest.MonkeyPatch) -> None:
    default_conn = WhatsAppConnector()
    assert default_conn.interface_id == DEFAULT_WHATSAPP_INTERFACE

    monkeypatch.setenv("WHATSAPP_INTERFACE_ID", "ENV_WHATSAPP_API")
    env_conn = WhatsAppConnector()
    assert env_conn.interface_id == "ENV_WHATSAPP_API"
