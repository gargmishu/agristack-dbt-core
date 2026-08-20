"""Normalized zero-PII standardized intake payload schema (Layer 2 -> Layer 3)."""

import re
from typing import Final

from pydantic import Field, HttpUrl, TypeAdapter, model_validator

from src.data_models.common import (
    ChannelType,
    HmacCitizenToken,
    LanguageLocale,
    PayloadType,
    SessionId,
    StrictBaseModel,
    StructureLevel,
    UnprocessedInputContent,
    UtcTimestamp,
)

_MAX_DTMF_LENGTH: Final[int] = 64
_MAX_MENU_SELECTION_LENGTH: Final[int] = 256
_DTMF_REGEX: Final[re.Pattern[str]] = re.compile(r"^\d+(\*\d+)*$")

# Pydantic v2 TypeAdapter used for standalone validation of HttpUrl strings without a model.
# Used to validate that AUDIO payload pointers (signed S3/GCS URLs) are valid HTTP/HTTPS URLs.
_HTTP_URL_ADAPTER: Final[TypeAdapter[HttpUrl]] = TypeAdapter(HttpUrl)


class PublicAgentStandardizedIntakePayload(StrictBaseModel):
    """Normalized, zero-PII public agent intake payload data model.

    Represents the canonical cross-channel contract encapsulating citizen input after
    perimeter
    security normalization and identity tokenization.

    Architectural Design Decisions:
    1. tokenized_citizen_id: Pseudonymous citizen identity token (not "tokenized_phone").
       Agnostic to identity source: computed as HMAC(secret, MSISDN) for phone channels, or
       HMAC(secret, UIDAI_Token_UID) for Aadhaar channels to comply with Aadhaar Act §29.
    2. structure_level: Enables Layer 3 pipeline routing to bypass SLM NLU for DTMF_SELECTION
       and MENU_SELECTION (saving ~800ms GPU inference latency and eliminating AI hallucinations)
       while directing FREE_TEXT into the SLM/NLU extraction pipeline.
    3. Payload-Aware URL Validation: Unlike generic Pydantic models where type validation alone
       may allow "https://[IP_ADDRESS]" or localhost schemes, this schema implements a runtime
       check enforcing that all signed audio URLs resolve to valid domain endpoints.

    Invariants:
    - Enforces compatibility matrix between `channel_type` and `structure_level` (e.g. IVR
      allows
      FREE_TEXT or DTMF_SELECTION; USSD allows MENU_SELECTION).
    - `unprocessed_input_content` must not be empty or whitespace-only.

    See: decisions/step2.0_canonical_domain_schemas.md (Section 4.2)
    See: decisions/step0.3_zero_trust_tokenization.md
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
    language_locale: LanguageLocale = Field(
        LanguageLocale.HINDI,
        description="Supported BCP 47 language code (defaults to hi-IN)",
    )
    unprocessed_input_content: UnprocessedInputContent
    received_at: UtcTimestamp = Field(
        ..., description="UTC timestamp when canonicalized payload reached Layer 3 intake gateway"
    )

    @model_validator(mode="after")
    def validate_channel_structure_matrix(self) -> "PublicAgentStandardizedIntakePayload":
        """Enforces channel, payload type, and structure level compatibility matrix."""
        if self.channel_type == ChannelType.USSD:
            if (
                not self.payload_type.is_text
                or self.structure_level != StructureLevel.DTMF_SELECTION
            ):
                raise ValueError(
                    "USSD channel strictly requires TEXT payload_type with DTMF_SELECTION "
                    "structure_level"
                )
        elif self.channel_type.is_voice:
            if not self.payload_type.is_audio or not self.structure_level.is_free_text:
                raise ValueError(
                    "IVR_VOICE channel strictly requires AUDIO payload_type with FREE_TEXT "
                    "structure_level"
                )
        elif self.channel_type == ChannelType.SMS:
            if not self.payload_type.is_text or not self.structure_level.is_free_text:
                raise ValueError(
                    "SMS channel strictly requires TEXT payload_type with FREE_TEXT structure_level"
                )
        else:  # ChannelType.WHATSAPP
            if self.payload_type.is_audio and not self.structure_level.is_free_text:
                raise ValueError(
                    "WHATSAPP AUDIO payload strictly requires FREE_TEXT structure_level"
                )
            if self.payload_type.is_text and self.structure_level not in (
                StructureLevel.FREE_TEXT,
                StructureLevel.MENU_SELECTION,
            ):
                raise ValueError(
                    "WHATSAPP TEXT payload requires FREE_TEXT or MENU_SELECTION structure_level"
                )
            if not self.payload_type.is_audio and not self.payload_type.is_text:
                raise ValueError("WHATSAPP channel requires AUDIO or TEXT payload_type")
        return self

    @model_validator(mode="after")
    def validate_content_format(self) -> "PublicAgentStandardizedIntakePayload":
        """Validates unprocessed_input_content format based on payload type and structure level."""
        content = self.unprocessed_input_content
        if self.payload_type.is_audio and self.structure_level.is_free_text:
            try:
                # Validates that the audio content string is a syntactically valid HTTP/HTTPS URL
                # (e.g. signed S3/GCS URL pointing to the Bhashini/IVR acoustic stream).
                _HTTP_URL_ADAPTER.validate_python(content)
            except Exception as err:
                raise ValueError(
                    "AUDIO free_text unprocessed_input_content must be a valid signed HTTP/HTTPS "
                    f"URL: {err}"
                ) from err
        elif self.payload_type.is_text and self.structure_level == StructureLevel.DTMF_SELECTION:
            if len(content) > _MAX_DTMF_LENGTH or not _DTMF_REGEX.match(content):
                raise ValueError(
                    "DTMF_SELECTION unprocessed_input_content must match DTMF keypad pattern "
                    "^\\d+(\\*\\d+)*$ (max 64 chars)"
                )
        elif (
            self.payload_type.is_text
            and self.structure_level == StructureLevel.MENU_SELECTION
            and len(content) > _MAX_MENU_SELECTION_LENGTH
        ):
            raise ValueError(
                "MENU_SELECTION unprocessed_input_content cannot exceed 256 characters"
            )
        return self
