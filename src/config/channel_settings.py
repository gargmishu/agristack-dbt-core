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
