"""USSD Menu signaling ingress payload schema (Layer 1 -> Layer 2)."""

from pydantic import Field

from src.data_models.common import (
    PhoneNumberE164,
    SessionId,
    StrictBaseModel,
    UtcTimestamp,
)


class UssdIngressPayload(StrictBaseModel):
    """Data model representing a USSD menu signaling ingress payload.

    Captures network routing shortcodes and citizen menu digit selections from cellular
    signaling frames.

    Invariants:
    - Decouples network routing shortcodes from user digit selections to maintain clean
      parsing boundaries.
    - `ussd_user_digit_selection` length is bounded to 64 characters based on menu depth
      formula.

    See: decisions/step2.0_canonical_domain_schemas.md#ussd-menu-ingress-payload
    See: decisions/step3.2_security_and_ingestion_firewalls.md
    """

    session_id: SessionId
    originating_phone_number: PhoneNumberE164
    ussd_service_code: str = Field(
        ...,
        pattern=r"^\*\d+(\*\d+)*#$",
        description="Network routing USSD shortcode (e.g., *147#, *147*1*2#)",
    )
    # Length calculation formula: max_length = 2N + D*(L_d + 1) - 1 = 64
    # Where N=5 menu levels (1 digit each), D=5 data entry fields (e.g. mobile, land parcel),
    # and L_d=10 max digits per field.
    ussd_user_digit_selection: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Concatenated digit selections and data entries separated by *",
    )
    received_at: UtcTimestamp = Field(
        ..., description="UTC timestamp when SS7/SIGTRAN gateway received USSD frame"
    )
