from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.config import DEFAULT_SMS_INTERFACE
from src.connectors import SmsConnector
from src.data_models.common import ChannelType, DeliveryStatus, GovernanceAction
from src.data_models.delivery import OutboundConfirmationPayload, TransmissionAck
from src.data_models.raw_ingress import SmsIngressPayload


@pytest.mark.asyncio
async def test_sms_connector_process_inbound_sms_valid() -> None:
    connector = SmsConnector()
    payload_data = {
        "session_id": "sess_12345678",
        "originating_phone_number": "+919876543210",
        "channel_message_id": "sms_msg_998877",
        "text_body": "STATUS PM-KISAN",
        "received_at": datetime.now(UTC).isoformat(),
    }
    result = await connector.process_inbound_sms(payload_data)
    assert isinstance(result, SmsIngressPayload)
    assert result.session_id == "sess_12345678"
    assert result.originating_phone_number == "+919876543210"
    assert result.channel_message_id == "sms_msg_998877"
    assert result.text_body == "STATUS PM-KISAN"


@pytest.mark.asyncio
async def test_sms_connector_process_inbound_sms_json_string_and_bytes() -> None:
    connector = SmsConnector()
    payload_json = (
        '{"session_id": "sess_12345678", '
        '"originating_phone_number": "+919876543210", '
        '"channel_message_id": "sms_msg_998877", '
        '"text_body": "STATUS PM-KISAN", '
        f'"received_at": "{datetime.now(UTC).isoformat()}"}}'
    )
    result_str = await connector.process_inbound_sms(payload_json)
    assert isinstance(result_str, SmsIngressPayload)
    assert result_str.text_body == "STATUS PM-KISAN"

    result_bytes = await connector.process_inbound_sms(payload_json.encode("utf-8"))
    assert isinstance(result_bytes, SmsIngressPayload)
    assert result_bytes.text_body == "STATUS PM-KISAN"


@pytest.mark.asyncio
async def test_sms_connector_process_inbound_sms_invalid() -> None:
    connector = SmsConnector()
    invalid_payload = {
        "session_id": "sess_12345678",
        "originating_phone_number": "invalid_phone",
        "channel_message_id": "sms_msg_998877",
        "text_body": "STATUS",
        "received_at": datetime.now(UTC).isoformat(),
    }
    with pytest.raises(ValidationError):
        await connector.process_inbound_sms(invalid_payload)


@pytest.mark.asyncio
async def test_sms_connector_send_outbound_confirmation() -> None:
    connector = SmsConnector(interface_id="CUSTOM_SMS_GATEWAY_01")
    assert connector.interface_id == "CUSTOM_SMS_GATEWAY_01"

    payload = OutboundConfirmationPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.SMS,
        governance_action=GovernanceAction.AUTO_APPROVE,
        delivery_status=DeliveryStatus.DELIVERED,
        formatted_message="AgriStack: Claim Approved. Txn: TXN-2026-981245.",
        disbursement_txn_id="TXN-2026-981245",
        delivered_at=datetime.now(UTC),
    )
    result = await connector.send_outbound_confirmation(payload)
    assert isinstance(result, TransmissionAck)
    assert result.interface_id == "CUSTOM_SMS_GATEWAY_01"
    assert result.channel_type == ChannelType.SMS
    assert result.session_id == "sess_12345678"
    assert result.status == DeliveryStatus.DELIVERED
    assert result.carrier_reference_id.startswith("sms-dr-")


def test_sms_connector_defaults_and_env(monkeypatch: pytest.MonkeyPatch) -> None:
    default_conn = SmsConnector()
    assert default_conn.interface_id == DEFAULT_SMS_INTERFACE

    monkeypatch.setenv("SMS_INTERFACE_ID", "ENV_SMS_GATEWAY_02")
    env_conn = SmsConnector()
    assert env_conn.interface_id == "ENV_SMS_GATEWAY_02"
