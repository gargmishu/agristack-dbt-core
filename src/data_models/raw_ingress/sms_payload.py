"""SMS messaging carrier ingress payload schema (Layer 1 -> Layer 2)."""

from pydantic import Field

from src.data_models.common import (
    ChannelMessageId,
    PhoneNumberE164,
    SessionId,
    StrictBaseModel,
    UtcTimestamp,
)

__all__ = ["SmsIngressPayload"]


class SmsIngressPayload(StrictBaseModel):
    """Data model representing an SMS message ingress payload.

    Captures text message content and carrier delivery metadata from SMS gateway webhooks.

    Invariants:
    - `text_body` must contain at least one non-whitespace character.
    - `channel_message_id` is required for tracking and deduplicating discrete messages.

    See: decisions/step2.0_canonical_domain_schemas.md#41-raw-carrier-ingress-payloads
    See: decisions/step3.2_security_and_ingestion_firewalls.md
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
