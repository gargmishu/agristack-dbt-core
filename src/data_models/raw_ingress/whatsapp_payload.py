"""WhatsApp messaging carrier ingress payload schema (Layer 1 -> Layer 2)."""

from pydantic import Field, HttpUrl, model_validator

from src.data_models.common import (
    AudioDurationSeconds,
    PayloadType,
    PhoneNumberE164,
    SessionId,
    StrictBaseModel,
    UtcTimestamp,
)


class WhatsAppIngressPayload(StrictBaseModel):
    """WhatsApp messaging carrier ingress payload (Layer 1 -> Layer 2).

    See: decisions/step2.0_canonical_domain_schemas.md#whatsapp-ingress-payload

    Note: channel_message_id is unique to WhatsApp (e.g. wamid). It is required for
    async discrete message deduplication. IVR and USSD do not carry this field because
    their interactions are bound 1:1 to session_id (continuous voice stream and transient
    GSM signaling session, respectively).
    """

    session_id: SessionId = Field(..., description="Unified channel messaging session identifier")
    originating_phone_number: PhoneNumberE164 = Field(
        ..., description="Citizen WhatsApp Business E.164 mobile account number"
    )
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
    # min_length=1 allows single-digit menu selections or quick affirmative replies
    # (e.g., "1", "2", "Y", "हाँ") while empty strings are stripped and rejected.
    text_body: str | None = Field(
        None,
        min_length=1,
        max_length=1000,
        description="Raw text message (populated for TEXT)",
    )
    received_at: UtcTimestamp = Field(
        ..., description="UTC timestamp when Meta webhook payload arrived"
    )

    @model_validator(mode="after")
    def validate_audio_modality_fields(self) -> "WhatsAppIngressPayload":
        """Enforces mandatory voice parameters and excludes text when modality is AUDIO.

        Why strictly separate audio URLs from text messages?
        Carrier webhooks must present a single unambiguous modality to Layer 2 canonicalization
        services. Requiring both signed audio recording URLs and voice note durations while
        rejecting text bodies avoids multi-modal parsing complexity and prevents silent attribute
        truncation during ASR audio transcription staging.
        """
        if self.payload_type == PayloadType.AUDIO:
            if self.audio_recording_url is None:
                raise ValueError("audio_recording_url is required when payload_type is AUDIO")
            if self.duration_seconds is None:
                raise ValueError("duration_seconds is required when payload_type is AUDIO")
            if self.text_body is not None:
                raise ValueError("text_body must be None when payload_type is AUDIO")
        return self

    @model_validator(mode="after")
    def validate_text_modality_fields(self) -> "WhatsAppIngressPayload":
        """Enforces non-empty text body and excludes audio pointers when modality is TEXT.

        Why strictly exclude audio attributes on text webhooks?
        Guaranteeing that text payloads carry zero acoustic references prevents edge connectors
        from accidentally invoking expensive ASR translation workers on text interactions, ensuring
        optimal CPU/GPU resource utilization and deterministic routing.
        """
        if self.payload_type == PayloadType.TEXT:
            if self.text_body is None:
                raise ValueError("text_body is required when payload_type is TEXT")
            if self.audio_recording_url is not None:
                raise ValueError("audio_recording_url must be None when payload_type is TEXT")
            if self.duration_seconds is not None:
                raise ValueError("duration_seconds must be None when payload_type is TEXT")
        return self
