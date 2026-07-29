from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.connectors import UssdConnector
from src.models.raw_ingress import UssdIngressPayload


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
