"""Channel and carrier transport gateway configuration settings.

Defines carrier-neutral defaults and environment variable bindings for Layer 1
connectors and Layer 4 outbound delivery services.
"""

import os
from typing import Final

DEFAULT_WHATSAPP_INTERFACE: Final[str] = "WHATSAPP_GATEWAY_DEFAULT"
DEFAULT_IVR_INTERFACE: Final[str] = "IVR_GATEWAY_DEFAULT"
DEFAULT_USSD_INTERFACE: Final[str] = "USSD_GATEWAY_DEFAULT"
DEFAULT_SMS_INTERFACE: Final[str] = "SMS_GATEWAY_DEFAULT"
DEFAULT_HELPLINE_NUMBER: Final[str] = "1800-180-1551"


def get_whatsapp_interface_id() -> str:
    """Returns configured WhatsApp webhook interface ID from environment or default."""
    return os.getenv("WHATSAPP_INTERFACE_ID", DEFAULT_WHATSAPP_INTERFACE)


def get_ivr_interface_id() -> str:
    """Returns configured IVR telephony interface ID from environment or default."""
    return os.getenv("IVR_INTERFACE_ID", DEFAULT_IVR_INTERFACE)


def get_ussd_interface_id() -> str:
    """Returns configured USSD signaling interface ID from environment or default."""
    return os.getenv("USSD_INTERFACE_ID", DEFAULT_USSD_INTERFACE)


def get_sms_interface_id() -> str:
    """Returns configured SMS gateway interface ID from environment or default."""
    return os.getenv("SMS_INTERFACE_ID", DEFAULT_SMS_INTERFACE)


def get_helpline_number() -> str:
    """Returns configured grievance helpline number from environment or default."""
    return os.getenv("HELPLINE_NUMBER", DEFAULT_HELPLINE_NUMBER)


def get_rate_per_minute() -> int:
    """Returns the configured sustained ingress rate limit per minute."""
    return _get_positive_int("RATE_LIMIT_PER_MINUTE")


def get_rate_limit_capacity() -> int:
    """Returns the configured ingress burst capacity."""
    return _get_positive_int("RATE_LIMIT_CAPACITY")


def get_pepper_secret() -> str:
    """Returns configured cryptographic pepper secret for Zero-PII HMAC tokenization."""
    pepper_secret = os.getenv("AGRISTACK_PEPPER_SECRET")
    if not pepper_secret or not pepper_secret.strip():
        raise ValueError(
            "Required environment variable 'AGRISTACK_PEPPER_SECRET' is missing or empty."
        )
    return pepper_secret.strip()


def _get_positive_int(variable_name: str) -> int:
    value = os.getenv(variable_name)
    if value is None:
        raise ValueError(f"Required environment variable '{variable_name}' is missing.")

    try:
        parsed_value = int(value)
    except ValueError as error:
        raise ValueError(f"Environment variable '{variable_name}' must be an integer.") from error

    if parsed_value <= 0:
        raise ValueError(f"Environment variable '{variable_name}' must be positive.")
    return parsed_value
