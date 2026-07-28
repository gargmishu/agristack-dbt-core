from pydantic import Field

from src.models.common import (
    PhoneNumberE164,
    SessionId,
    StrictBaseModel,
    UtcTimestamp,
)


class UssdIngressPayload(StrictBaseModel):
    """USSD Menu signaling ingress payload (Layer 1 -> Layer 2).

    Note: Unlike WhatsApp, USSD has no session_message_id because USSD is a transient
    synchronous GSM signaling session bound 1:1 to session_id rather than discrete messages.
    """

    session_id: SessionId
    originating_phone_number: PhoneNumberE164
    ussd_service_code: str = Field(
        ...,
        pattern=r"^\*\d+(\*\d+)*#$",
        description="USSD shortcode (e.g., *147#, *147*1*2#)",
    )
    ussd_user_digit_selection: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Concatenated digit selections and data entries separated by *",
    )
    ingress_timestamp: UtcTimestamp
