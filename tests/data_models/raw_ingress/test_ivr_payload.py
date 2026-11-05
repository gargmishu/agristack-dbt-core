from datetime import UTC, datetime

import pytest
from pydantic import HttpUrl, TypeAdapter, ValidationError

from src.data_models.raw_ingress import (
    DEFAULT_TELEPHONY_SAMPLE_RATE_HZ,
    WIDEBAND_TELEPHONY_SAMPLE_RATE_HZ,
    IvrIngressPayload,
    TelephonySampleRateHz,
)

http_url_adapter = TypeAdapter(HttpUrl)


def test_ivr_ingress_valid() -> None:
    url = http_url_adapter.validate_python("https://storage.agristack.gov.in/ivr/call.wav")
    payload = IvrIngressPayload(
        session_id="sip_call_987654321",
        originating_phone_number="+919876543210",
        audio_recording_url=url,
        audio_duration_seconds=300,
        received_at=datetime.now(UTC),
    )
    assert payload.audio_duration_seconds == 300  # noqa: PLR2004
    assert payload.sample_rate_hz == DEFAULT_TELEPHONY_SAMPLE_RATE_HZ


@pytest.mark.parametrize(
    "sample_rate_hz",
    [DEFAULT_TELEPHONY_SAMPLE_RATE_HZ, WIDEBAND_TELEPHONY_SAMPLE_RATE_HZ],
)
def test_ivr_ingress_accepts_8khz_and_16khz_telephony_sample_rates(
    sample_rate_hz: TelephonySampleRateHz,
) -> None:
    url = http_url_adapter.validate_python("https://storage.agristack.gov.in/ivr/call.wav")
    payload = IvrIngressPayload(
        session_id="sip_call_987654321",
        originating_phone_number="+919876543210",
        audio_recording_url=url,
        audio_duration_seconds=45,
        sample_rate_hz=sample_rate_hz,
        received_at=datetime.now(UTC),
    )
    assert payload.sample_rate_hz == sample_rate_hz


@pytest.mark.parametrize("invalid_sample_rate_hz", [0, -8000, 4000, 22050, 44100, 48000])
def test_ivr_ingress_rejects_unsupported_sample_rates(invalid_sample_rate_hz: int) -> None:
    url = http_url_adapter.validate_python("https://storage.agristack.gov.in/ivr/call.wav")
    with pytest.raises(ValidationError):
        IvrIngressPayload(
            session_id="sip_call_987654321",
            originating_phone_number="+919876543210",
            audio_recording_url=url,
            audio_duration_seconds=45,
            sample_rate_hz=invalid_sample_rate_hz,  # type: ignore[arg-type]
            received_at=datetime.now(UTC),
        )


def test_ivr_ingress_duration_exceeds_ceiling() -> None:
    url = http_url_adapter.validate_python("https://storage.agristack.gov.in/ivr/call.wav")
    with pytest.raises(ValidationError):
        IvrIngressPayload(
            session_id="sip_call_987654321",
            originating_phone_number="+919876543210",
            audio_recording_url=url,
            audio_duration_seconds=601,  # Exceeds max 600s ceiling
            received_at=datetime.now(UTC),
        )
