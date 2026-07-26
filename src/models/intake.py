from datetime import datetime

from pydantic import Field, model_validator

from src.models.base import StrictBaseModel
from src.models.enums import ChannelType, PayloadType, StructureLevel


class StandardizedIntakePayload(StrictBaseModel):
    """Normalized, zero-PII public agent intake payload (Layer 2 -> Layer 3)."""

    channel_session_id: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Unified channel session ID",
    )
    tokenized_citizen_id: str = Field(
        ...,
        pattern=r"^[a-fA-F0-9]{64}$",
        description="Zero-PII SHA-256 HMAC citizen identity token",
    )
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
    intake_timestamp: datetime = Field(
        ..., description="UTC timestamp when intake API accepted event"
    )

    @model_validator(mode="after")
    def validate_type_tuple_rules(self) -> "StandardizedIntakePayload":
        """Enforces 2-type tuple input rules for channel and modality compatibility."""
        payload_str = str(self.payload_type)
        structure_str = str(self.structure_level)
        channel_str = str(self.channel_type)

        # 1. Payload Modality & Structure Level Compatibility
        if (
            payload_str == PayloadType.AUDIO.value
            and structure_str != StructureLevel.FREE_TEXT.value
        ):
            raise ValueError("AUDIO payload_type strictly requires FREE_TEXT structure_level")

        # 2. Channel & Payload Type Compatibility
        if channel_str == ChannelType.IVR_VOICE.value and payload_str != PayloadType.AUDIO.value:
            raise ValueError("IVR_VOICE channel strictly requires AUDIO payload_type")
        if (
            channel_str in (ChannelType.USSD.value, ChannelType.SMS.value)
            and payload_str != PayloadType.TEXT.value
        ):
            raise ValueError(
                f"{channel_str} channel strictly requires TEXT payload_type"
            )

        return self
