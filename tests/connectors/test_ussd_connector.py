from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.connectors import UssdConnector
from src.data_models.common import ChannelType, DeliveryStatus, GovernanceAction
from src.data_models.delivery import OutboundConfirmationPayload
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
    connector = UssdConnector()
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
    assert result["sigtran_interface"] == "SS7_SIGTRAN_CARRIER_GATEWAY"
    assert result["session_id"] == "sess_12345678"
    assert result["status"] == DeliveryStatus.DELIVERED
    assert result["ussd_menu_response"] == "AgriStack: Claim Approved."
