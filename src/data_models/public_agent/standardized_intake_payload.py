"""Normalized zero-PII standardized intake payload schema (Layer 2 -> Layer 3)."""

import re

from pydantic import Field, HttpUrl, TypeAdapter, model_validator

from src.data_models.common import (
    ChannelType,
    HmacCitizenToken,
    PayloadType,
    SessionId,
    StrictBaseModel,
    StructureLevel,
    UtcTimestamp,
)

MAX_DTMF_LENGTH = 64
MAX_MENU_SELECTION_LENGTH = 256
DTMF_REGEX = re.compile(r"^\d+(\*\d+)*$")

# Pydantic v2 TypeAdapter used for standalone validation of HttpUrl strings without a model.
# Used to validate that AUDIO payload pointers (signed S3/GCS URLs) are valid HTTP/HTTPS URLs.
http_url_adapter = TypeAdapter(HttpUrl)


class PublicAgentStandardizedIntakePayload(StrictBaseModel):
    """Normalized, zero-PII public agent intake payload (Layer 2 -> Layer 3).

    See: decisions/step2.0_canonical_domain_schemas.md (Section 4.2)
    See: decisions/step0.3_zero_trust_tokenization.md

    Architectural Design Decisions:
    1. tokenized_citizen_id: Pseudonymous citizen identity token (not "tokenized_phone").
       Agnostic to identity source: computed as HMAC(secret, MSISDN) for phone channels, or
       HMAC(secret, UIDAI_Token_UID) for Aadhaar channels to comply with Aadhaar Act §29.
    2. structure_level: Enables Layer 3 pipeline routing to bypass SLM NLU for DTMF_SELECTION
       and MENU_SELECTION (saving ~800ms GPU inference latency and eliminating AI hallucinations)
       while directing FREE_TEXT into the SLM/NLU extraction pipeline.
    """

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
    def validate_non_empty_content(self) -> "PublicAgentStandardizedIntakePayload":
        """Ensures unprocessed_input_content is non-empty and non-whitespace."""
        if not self.unprocessed_input_content or not self.unprocessed_input_content.strip():
            raise ValueError("unprocessed_input_content cannot be empty or whitespace-only")
        return self

    @model_validator(mode="after")
    def validate_channel_structure_matrix(self) -> "PublicAgentStandardizedIntakePayload":
        """Enforces channel, payload type, and structure level compatibility matrix."""
        if self.channel_type == ChannelType.USSD:
            if (
                self.payload_type != PayloadType.TEXT
                or self.structure_level != StructureLevel.DTMF_SELECTION
            ):
                raise ValueError(
                    "USSD channel strictly requires TEXT payload_type with DTMF_SELECTION "
                    "structure_level"
                )
        elif self.channel_type == ChannelType.IVR_VOICE:
            if (
                self.payload_type != PayloadType.AUDIO
                or self.structure_level != StructureLevel.FREE_TEXT
            ):
                raise ValueError(
                    "IVR_VOICE channel strictly requires AUDIO payload_type with FREE_TEXT "
                    "structure_level"
                )
        elif self.channel_type == ChannelType.SMS:
            if (
                self.payload_type != PayloadType.TEXT
                or self.structure_level != StructureLevel.FREE_TEXT
            ):
                raise ValueError(
                    "SMS channel strictly requires TEXT payload_type with FREE_TEXT structure_level"
                )
        elif self.channel_type == ChannelType.WHATSAPP:
            if (
                self.payload_type == PayloadType.AUDIO
                and self.structure_level != StructureLevel.FREE_TEXT
            ):
                raise ValueError(
                    "WHATSAPP AUDIO payload strictly requires FREE_TEXT structure_level"
                )
            if self.payload_type == PayloadType.TEXT and self.structure_level not in (
                StructureLevel.FREE_TEXT,
                StructureLevel.MENU_SELECTION,
            ):
                raise ValueError(
                    "WHATSAPP TEXT payload requires FREE_TEXT or MENU_SELECTION structure_level"
                )
            if self.payload_type not in (PayloadType.AUDIO, PayloadType.TEXT):
                raise ValueError("WHATSAPP channel requires AUDIO or TEXT payload_type")
        return self

    @model_validator(mode="after")
    def validate_content_format(self) -> "PublicAgentStandardizedIntakePayload":
        """Validates unprocessed_input_content format based on payload type and structure level."""
        content = self.unprocessed_input_content
        if (
            self.payload_type == PayloadType.AUDIO
            and self.structure_level == StructureLevel.FREE_TEXT
        ):
            try:
                # Validates that the audio content string is a syntactically valid HTTP/HTTPS URL
                # (e.g. signed S3/GCS URL pointing to the Bhashini/IVR acoustic stream).
                http_url_adapter.validate_python(content)
            except Exception as err:
                raise ValueError(
                    "AUDIO free_text unprocessed_input_content must be a valid signed HTTP/HTTPS "
                    f"URL: {err}"
                ) from err
        elif (
            self.payload_type == PayloadType.TEXT
            and self.structure_level == StructureLevel.DTMF_SELECTION
        ):
            if len(content) > MAX_DTMF_LENGTH or not DTMF_REGEX.match(content):
                raise ValueError(
                    "DTMF_SELECTION unprocessed_input_content must match DTMF keypad pattern "
                    "^\\d+(\\*\\d+)*$ (max 64 chars)"
                )
        elif (
            self.payload_type == PayloadType.TEXT
            and self.structure_level == StructureLevel.MENU_SELECTION
            and len(content) > MAX_MENU_SELECTION_LENGTH
        ):
            raise ValueError(
                "MENU_SELECTION unprocessed_input_content cannot exceed 256 characters"
            )
        return self
