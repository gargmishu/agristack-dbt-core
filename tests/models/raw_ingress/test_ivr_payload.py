from datetime import UTC, datetime

import pytest
from pydantic import HttpUrl, TypeAdapter, ValidationError

from src.models.raw_ingress import IvrIngressPayload

http_url_adapter = TypeAdapter(HttpUrl)


def test_ivr_ingress_valid() -> None:
    url = http_url_adapter.validate_python("https://storage.agristack.gov.in/ivr/call.wav")
    payload = IvrIngressPayload(
        session_id="sip_call_987654321",
        originating_phone_number="+919876543210",
        audio_recording_url=url,
        duration_seconds=300,
        ingress_timestamp=datetime.now(UTC),
    )
    assert payload.duration_seconds == 300  # noqa: PLR2004


def test_ivr_ingress_duration_exceeds_ceiling() -> None:
    url = http_url_adapter.validate_python("https://storage.agristack.gov.in/ivr/call.wav")
    with pytest.raises(ValidationError):
        IvrIngressPayload(
            session_id="sip_call_987654321",
            originating_phone_number="+919876543210",
            audio_recording_url=url,
            duration_seconds=601,  # Exceeds max 600s ceiling
            ingress_timestamp=datetime.now(UTC),
        )
