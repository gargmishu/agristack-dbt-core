"""IVR Telephony SIP gateway ingress payload schema (Layer 1 -> Layer 2)."""

from pydantic import Field, HttpUrl

from src.data_models.common import (
    AudioDurationSeconds,
    PhoneNumberE164,
    SessionId,
    StrictBaseModel,
    UtcTimestamp,
)


class IvrIngressPayload(StrictBaseModel):
    """Data model representing an IVR voice call ingress payload.

    Captures telephony call metadata and audio recording pointers delivered by SIP gateways.

    Invariants:
    - `session_id` acts as the primary call key; discrete message IDs are not used because
      one SIP call represents a continuous interaction session.
    - `audio_duration_seconds` must be between 1 and 600 seconds inclusive.

    See: decisions/step2.0_canonical_domain_schemas.md#ivr-telephony-ingress-payload
    See: decisions/step3.2_security_and_ingestion_firewalls.md
    """

    session_id: SessionId
    originating_phone_number: PhoneNumberE164
    audio_recording_url: HttpUrl = Field(..., description="Signed URL for .wav recording")
    audio_duration_seconds: AudioDurationSeconds
    received_at: UtcTimestamp = Field(
        ..., description="UTC timestamp when SIP gateway received voice stream"
    )
