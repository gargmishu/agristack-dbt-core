from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.connectors import IvrConnector
from src.models.raw_ingress import IvrIngressPayload


@pytest.mark.asyncio
async def test_ivr_connector_valid_session() -> None:
    connector = IvrConnector()
    payload_data = {
        "session_id": "sess_12345678",
        "originating_phone_number": "+919876543210",
        "audio_recording_url": "https://sip-gateway.telecom.in/audio/call_987.wav",
        "duration_seconds": 45,
        "received_at": datetime.now(UTC).isoformat(),
    }
    result = await connector.process_call_session(payload_data)
    assert isinstance(result, IvrIngressPayload)
    assert result.duration_seconds == 45
    assert str(result.audio_recording_url) == "https://sip-gateway.telecom.in/audio/call_987.wav"


@pytest.mark.asyncio
async def test_ivr_connector_invalid_audio_url() -> None:
    connector = IvrConnector()
    invalid_payload = {
        "session_id": "sess_12345678",
        "originating_phone_number": "+919876543210",
        "audio_recording_url": "not_a_valid_url",
        "duration_seconds": 45,
        "received_at": datetime.now(UTC).isoformat(),
    }
    with pytest.raises(ValidationError):
        await connector.process_call_session(invalid_invalid := invalid_payload)


@pytest.mark.asyncio
async def test_ivr_connector_invalid_duration_zero() -> None:
    connector = IvrConnector()
    invalid_payload = {
        "session_id": "sess_12345678",
        "originating_phone_number": "+919876543210",
        "audio_recording_url": "https://sip-gateway.telecom.in/audio/call_987.wav",
        "duration_seconds": 0,  # Min duration is 1 second
        "received_at": datetime.now(UTC).isoformat(),
    }
    with pytest.raises(ValidationError):
        await connector.process_call_session(invalid_payload)
