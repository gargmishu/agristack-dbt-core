from pydantic import Field, HttpUrl

from src.models.base import StrictBaseModel
from src.models.validators import (
    AudioDurationSeconds,
    ChannelSessionId,
    PhoneNumberE164,
    UtcTimestamp,
)


class IVRIngressPayload(StrictBaseModel):
    """IVR Telephony SIP gateway ingress payload (Layer 1 -> Layer 2)."""

    channel_session_id: ChannelSessionId
    originating_phone_number: PhoneNumberE164
    audio_recording_url: HttpUrl = Field(
        ..., description="Signed URL for .wav recording"
    )
    duration_seconds: AudioDurationSeconds
    ingress_timestamp: UtcTimestamp
