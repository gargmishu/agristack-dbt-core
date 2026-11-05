"""IVR Telephony SIP gateway ingress payload schema (Layer 1 -> Layer 2)."""

from typing import Final, Literal

from pydantic import Field, HttpUrl

from src.data_models.common import (
    AudioDurationSeconds,
    PhoneNumberE164,
    SessionId,
    StrictBaseModel,
    UtcTimestamp,
)

__all__ = [
    "DEFAULT_TELEPHONY_SAMPLE_RATE_HZ",
    "WIDEBAND_TELEPHONY_SAMPLE_RATE_HZ",
    "IvrIngressPayload",
    "TelephonySampleRateHz",
]

DEFAULT_TELEPHONY_SAMPLE_RATE_HZ: Final[Literal[8000]] = 8000
WIDEBAND_TELEPHONY_SAMPLE_RATE_HZ: Final[Literal[16000]] = 16000
TelephonySampleRateHz = Literal[8000, 16000]


class IvrIngressPayload(StrictBaseModel):
    """Data model representing a Layer 1 IVR voice call ingress payload.

    Captures telephony call metadata, acoustic sample rate profile, and audio recording
    pointers delivered by SIP trunks and self-hosted real-time voice telephony runtimes
    (such as the open-source COSS/EkStep VoicEra platform handling 8kHz PSTN/SIP call
    termination, Pipecat bidirectional streaming, Voice Activity Detection [VAD],
    barge-in interruption, and MinIO .wav storage at <₹1/min) before Layer 2 Zero-Trust
    tokenization and Layer 3 Bhashini ASR/NMT/TTS model perception.

    Invariants:
    - `session_id` acts as the primary call key; discrete message IDs are not used because
      one SIP call represents a continuous interaction session.
    - `audio_duration_seconds` must be between 1 and 600 seconds inclusive.
    - `sample_rate_hz` is strictly constrained to 8000 Hz (8kHz narrowband PSTN/GSM rural
      telephony default) or 16000 Hz (16kHz wideband SIP/WebRTC PCM).

    See: decisions/step2.0_canonical_domain_schemas.md#ivr-telephony-ingress-payload
    See: decisions/step3.2_security_and_ingestion_firewalls.md
    See: decisions/step3.6_speech_and_translation_evaluation.md
    """

    session_id: SessionId
    originating_phone_number: PhoneNumberE164
    audio_recording_url: HttpUrl = Field(..., description="Signed URL for .wav recording")
    audio_duration_seconds: AudioDurationSeconds
    sample_rate_hz: TelephonySampleRateHz = Field(
        default=DEFAULT_TELEPHONY_SAMPLE_RATE_HZ,
        description=(
            "Telephony audio sample rate in Hz: 8000 (8kHz narrowband PSTN/GSM default) "
            "or 16000 (16kHz wideband PCM)"
        ),
    )
    received_at: UtcTimestamp = Field(
        ..., description="UTC timestamp when SIP gateway received voice stream"
    )
