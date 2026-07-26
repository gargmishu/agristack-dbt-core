from datetime import datetime

from pydantic import Field

from src.models.base import StrictBaseModel
from src.models.validators import ChannelSessionId, PhoneNumberE164


class USSDIngressPayload(StrictBaseModel):
    """USSD Menu signaling ingress payload (Layer 1 -> Layer 2)."""

    channel_session_id: ChannelSessionId
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
    ingress_timestamp: datetime = Field(
        ..., description="UTC timestamp when telco received USSD code"
    )
