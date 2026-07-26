from datetime import datetime

from pydantic import Field

from src.models.base import StrictBaseModel


class USSDIngressPayload(StrictBaseModel):
    """USSD Menu signaling ingress payload (Layer 1 -> Layer 2)."""

    channel_session_id: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Telco network session ID",
    )
    originating_phone_number: str = Field(
        ...,
        pattern=r"^\+[1-9]\d{1,14}$",
        description="Originating MSISDN phone number (E.164 standard)",
    )
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
