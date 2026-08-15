from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.config import DEFAULT_USSD_INTERFACE
from src.connectors import UssdConnector
from src.data_models.common import ChannelType, DeliveryStatus, GovernanceAction
from src.data_models.delivery import OutboundConfirmationPayload, TransmissionAck
from src.data_models.raw_ingress import UssdIngressPayload


@pytest.mark.asyncio
async def test_ussd_connector_valid_session() -> None:
    connector = UssdConnector()
    payload_data = {
        "session_id": "sess_12345678",
        "originating_phone_number": "+919876543210",
        "ussd_service_code": "*147#",
        "ussd_user_digit_selection": "1*2*9876543210",
        "received_at": datetime.now(UTC).isoformat(),
    }
    result = await connector.process_ussd_session(payload_data)
    assert isinstance(result, UssdIngressPayload)
    assert result.ussd_service_code == "*147#"
    assert result.ussd_user_digit_selection == "1*2*9876543210"


@pytest.mark.asyncio
async def test_ussd_connector_json_string_and_bytes() -> None:
    connector = UssdConnector()
    payload_json = (
        '{"session_id": "sess_12345678", '
        '"originating_phone_number": "+919876543210", '
        '"ussd_service_code": "*147#", '
        '"ussd_user_digit_selection": "1*2*9876543210", '
        f'"received_at": "{datetime.now(UTC).isoformat()}"}}'
    )
    result_str = await connector.process_ussd_session(payload_json)
    assert isinstance(result_str, UssdIngressPayload)
    assert result_str.ussd_service_code == "*147#"

    result_bytes = await connector.process_ussd_session(payload_json.encode("utf-8"))
    assert isinstance(result_bytes, UssdIngressPayload)
    assert result_bytes.ussd_service_code == "*147#"


@pytest.mark.asyncio
async def test_ussd_connector_invalid_service_code() -> None:
    connector = UssdConnector()
    invalid_payload = {
        "session_id": "sess_12345678",
        "originating_phone_number": "+919876543210",
        "ussd_service_code": "147",  # Missing leading * and trailing #
        "ussd_user_digit_selection": "1*2",
        "received_at": datetime.now(UTC).isoformat(),
    }
    with pytest.raises(ValidationError):
        await connector.process_ussd_session(invalid_payload)


@pytest.mark.asyncio
async def test_ussd_connector_invalid_empty_digits() -> None:
    connector = UssdConnector()
    invalid_payload = {
        "session_id": "sess_12345678",
        "originating_phone_number": "+919876543210",
        "ussd_service_code": "*147#",
        "ussd_user_digit_selection": "",  # Min length 1
        "received_at": datetime.now(UTC).isoformat(),
    }
    with pytest.raises(ValidationError):
        await connector.process_ussd_session(invalid_payload)


@pytest.mark.asyncio
async def test_ussd_connector_send_outbound_confirmation() -> None:
    connector = UssdConnector(interface_id="CUSTOM_SS7_GATEWAY_01")
    assert connector.interface_id == "CUSTOM_SS7_GATEWAY_01"

    payload = OutboundConfirmationPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.USSD,
        governance_action=GovernanceAction.AUTO_APPROVE,
        delivery_status=DeliveryStatus.DELIVERED,
        formatted_message="AgriStack: Claim Approved.",
        disbursement_txn_id="TXN-2026-981245",
        delivered_at=datetime.now(UTC),
    )
    result = await connector.send_outbound_confirmation(payload)
    assert isinstance(result, TransmissionAck)
    assert result.interface_id == "CUSTOM_SS7_GATEWAY_01"
    assert result.channel_type == ChannelType.USSD
    assert result.session_id == "sess_12345678"
    assert result.status == DeliveryStatus.DELIVERED
    assert result.carrier_reference_id.startswith("ussd-sig-")


def test_ussd_connector_factories(monkeypatch: pytest.MonkeyPatch) -> None:
    default_conn = UssdConnector()
    assert default_conn.interface_id == DEFAULT_USSD_INTERFACE

    monkeypatch.setenv("USSD_INTERFACE_ID", "ENV_SS7_GATEWAY_02")
    env_conn = UssdConnector()
    assert env_conn.interface_id == "ENV_SS7_GATEWAY_02"
