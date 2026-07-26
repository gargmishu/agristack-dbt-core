from datetime import datetime

from pydantic import Field, HttpUrl

from src.models.base import StrictBaseModel


class IVRIngressPayload(StrictBaseModel):
    """IVR Telephony SIP gateway ingress payload (Layer 1 -> Layer 2)."""

    channel_session_id: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Telephony Provider Call Session ID",
    )
    originating_phone_number: str = Field(
        ...,
        pattern=r"^\+[1-9]\d{1,14}$",
        description="Originating ANI phone number (E.164 standard)",
    )
    audio_recording_url: HttpUrl = Field(
        ..., description="Signed URL for .wav recording"
    )
    duration_seconds: int = Field(
        ...,
        ge=1,
        le=600,
        description="Total call audio duration in seconds (1 to 600s)",
    )
    ingress_timestamp: datetime = Field(
        ..., description="UTC timestamp when call arrived at SIP trunk"
    )
