from datetime import UTC, datetime

import pytest

from src.config import DEFAULT_SMS_INTERFACE
from src.connectors import SmsConnector
from src.data_models.common import ChannelType, DeliveryStatus, GovernanceAction
from src.data_models.delivery import OutboundConfirmationPayload


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
    assert result["interface_id"] == "CUSTOM_SMS_GATEWAY_01"
    assert result["messaging_product"] == "sms"
    assert result["session_id"] == "sess_12345678"
    assert result["status"] == DeliveryStatus.DELIVERED
    assert result["message"] == "AgriStack: Claim Approved. Txn: TXN-2026-981245."


def test_sms_connector_defaults_and_env(monkeypatch: pytest.MonkeyPatch) -> None:
    default_conn = SmsConnector()
    assert default_conn.interface_id == DEFAULT_SMS_INTERFACE

    monkeypatch.setenv("SMS_INTERFACE_ID", "ENV_SMS_GATEWAY_02")
    env_conn = SmsConnector()
    assert env_conn.interface_id == "ENV_SMS_GATEWAY_02"
