"""USSD Menu signaling ingress payload schema (Layer 1 -> Layer 2)."""

from pydantic import Field

from src.data_models.common import (
    PhoneNumberE164,
    SessionId,
    StrictBaseModel,
    UtcTimestamp,
)


class UssdIngressPayload(StrictBaseModel):
    """USSD Menu signaling ingress payload (Layer 1 -> Layer 2).

    See: decisions/step2.0_canonical_domain_schemas.md#ussd-menu-ingress-payload

    USSD uses session_id as the interaction identity because each request belongs to
    one short-lived signaling session. Unlike SMS or WhatsApp webhooks, it does not
    represent an independently retried discrete message, so channel_message_id is
    not required.

    Architectural Design Choice:
    Decoupling network routing shortcodes (e.g. *147#) from application menu selections
    (e.g. 1*2*9876543210) eliminates parsing ambiguity for downstream services and allows
    Layer 2 connectors to forward digit selections directly into
    StandardizedIntakePayload.unprocessed_input_content.
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
