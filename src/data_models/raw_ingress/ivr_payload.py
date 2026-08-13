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
    """IVR Telephony SIP gateway ingress payload (Layer 1 -> Layer 2).

    See: decisions/step2.0_canonical_domain_schemas.md#ivr-telephony-ingress-payload
    """

    session_id: SessionId
    originating_phone_number: PhoneNumberE164
    audio_recording_url: HttpUrl = Field(..., description="Signed URL for .wav recording")
    duration_seconds: AudioDurationSeconds
    received_at: UtcTimestamp = Field(
        ..., description="UTC timestamp when SIP gateway received voice stream"
    )
