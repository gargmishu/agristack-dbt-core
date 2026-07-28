from pydantic import Field, HttpUrl, model_validator

from src.models.common import (
    AudioDurationSeconds,
    PayloadType,
    PhoneNumberE164,
    SessionId,
    StrictBaseModel,
    UtcTimestamp,
)


class WhatsAppIngressPayload(StrictBaseModel):
    """WhatsApp messaging carrier ingress payload (Layer 1 -> Layer 2)."""

    session_id: SessionId
    originating_phone_number: PhoneNumberE164
    channel_message_id: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description=(
            "Carrier unique message ID (e.g. WhatsApp wamid). Needed for async discrete "
            "message deduplication; unlike IVR/USSD where interaction is bound to session."
        ),
    )
    payload_type: PayloadType = Field(
        ..., description="Ingress payload modality: audio, text, image, document"
    )
    audio_recording_url: HttpUrl | None = Field(
        None, description="Signed URL for .ogg audio file (populated for AUDIO)"
    )
    duration_seconds: AudioDurationSeconds | None = Field(
        None, description="Voice note audio duration in seconds (1 to 600s; populated for AUDIO)"
    )
    text_body: str | None = Field(
        None,
        max_length=1000,
        description="Raw text message (populated for TEXT)",
    )
    received_at: UtcTimestamp

    @model_validator(mode="after")
    def validate_content_mutual_exclusivity(self) -> "WhatsAppIngressPayload":
        """Enforces mutual exclusivity between audio and text content."""
        if str(self.payload_type) == PayloadType.AUDIO.value:
            if self.audio_recording_url is None:
                raise ValueError("audio_recording_url is required when payload_type is AUDIO")
            if self.duration_seconds is None:
                raise ValueError("duration_seconds is required when payload_type is AUDIO")
            if self.text_body is not None:
                raise ValueError("text_body must be None when payload_type is AUDIO")
        elif str(self.payload_type) == PayloadType.TEXT.value:
            if self.text_body is None or not self.text_body.strip():
                raise ValueError("text_body must be a non-empty string when payload_type is TEXT")
            if self.audio_recording_url is not None:
                raise ValueError("audio_recording_url must be None when payload_type is TEXT")
            if self.duration_seconds is not None:
                raise ValueError("duration_seconds must be None when payload_type is TEXT")
        return self
