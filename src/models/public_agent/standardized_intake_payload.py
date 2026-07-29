from pydantic import Field, model_validator

from src.models.common import (
    ChannelType,
    HmacCitizenToken,
    PayloadType,
    SessionId,
    StrictBaseModel,
    StructureLevel,
    UtcTimestamp,
)


class PublicAgentStandardizedIntakePayload(StrictBaseModel):
    """Normalized, zero-PII public agent intake payload (Layer 2 -> Layer 3)."""

    session_id: SessionId
    tokenized_citizen_id: HmacCitizenToken
    channel_type: ChannelType = Field(
        ..., description="Originating channel type: whatsapp, ivr_voice, ussd, sms"
    )
    payload_type: PayloadType = Field(
        ..., description="Modality of input: text, audio, image, document"
    )
    structure_level: StructureLevel = Field(
        ..., description="Input structure: free_text, menu_selection, dtmf_selection"
    )
    language_locale: str = Field(
        "hi-IN",
        pattern=r"^[a-z]{2}-[A-Z]{2}$",
        description="BCP 47 language code (defaults to hi-IN)",
    )
    unprocessed_input_content: str = Field(
        ...,
        max_length=5000,
        description="Raw citizen text or signed audio URL pointer",
    )
    received_at: UtcTimestamp

    @model_validator(mode="after")
    def validate_type_tuple_rules(self) -> "PublicAgentStandardizedIntakePayload":
        """Enforces 2-type tuple input rules for channel and modality compatibility."""
        # 1. Payload Modality & Structure Level Compatibility
        if (
            self.payload_type == PayloadType.AUDIO
            and self.structure_level != StructureLevel.FREE_TEXT
        ):
            raise ValueError("AUDIO payload_type strictly requires FREE_TEXT structure_level")

        # 2. Channel & Payload Type Compatibility
        if self.channel_type == ChannelType.IVR_VOICE and self.payload_type != PayloadType.AUDIO:
            raise ValueError("IVR_VOICE channel strictly requires AUDIO payload_type")
        if (
            self.channel_type in (ChannelType.USSD, ChannelType.SMS)
            and self.payload_type != PayloadType.TEXT
        ):
            raise ValueError(f"{self.channel_type} channel strictly requires TEXT payload_type")

        return self
