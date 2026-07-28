from pydantic import Field, HttpUrl

from src.models.common import (
    AudioDurationSeconds,
    PhoneNumberE164,
    SessionId,
    StrictBaseModel,
    UtcTimestamp,
)


class IvrIngressPayload(StrictBaseModel):
    """IVR Telephony SIP gateway ingress payload (Layer 1 -> Layer 2).

    Note: Unlike WhatsApp, IVR has no channel_message_id because a phone call is a
    continuous voice stream bound 1:1 to session_id rather than discrete messages.
    """

    session_id: SessionId
    originating_phone_number: PhoneNumberE164
    audio_recording_url: HttpUrl = Field(..., description="Signed URL for .wav recording")
    duration_seconds: AudioDurationSeconds
    ingress_timestamp: UtcTimestamp
