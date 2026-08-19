"""SMS messaging carrier ingress payload schema (Layer 1 -> Layer 2)."""

from pydantic import Field, model_validator

from src.data_models.common import (
    ChannelMessageId,
    PhoneNumberE164,
    SessionId,
    StrictBaseModel,
    UtcTimestamp,
)


class SmsIngressPayload(StrictBaseModel):
    """SMS carrier webhook ingress payload (Layer 1 -> Layer 2).

    See: decisions/step2.0_canonical_domain_schemas.md
    """

    session_id: SessionId
    originating_phone_number: PhoneNumberE164
    channel_message_id: ChannelMessageId
    text_body: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Raw incoming cleartext SMS message body",
    )
    received_at: UtcTimestamp = Field(
        ...,
        description="UTC timestamp when carrier SMS gateway received message",
    )

    @model_validator(mode="after")
    def validate_non_empty_text(self) -> "SmsIngressPayload":
        """Ensures that text_body is not whitespace-only."""
        if not self.text_body or not self.text_body.strip():
            raise ValueError("text_body cannot be whitespace-only")
        return self
