"""Channel and carrier transport gateway configuration settings.

Defines carrier-neutral defaults and environment variable bindings for Layer 1
connectors and Layer 4 outbound delivery services.
"""

import os
from typing import Final

DEFAULT_WHATSAPP_INTERFACE: Final[str] = "WHATSAPP_GATEWAY_DEFAULT"
DEFAULT_SIP_TRUNK_INTERFACE: Final[str] = "SIP_TRUNK_GATEWAY_DEFAULT"
DEFAULT_SIGTRAN_INTERFACE: Final[str] = "USSD_SIGTRAN_GATEWAY_DEFAULT"
DEFAULT_SMS_GATEWAY: Final[str] = "SMS_GATEWAY_DEFAULT"
DEFAULT_HELPLINE_TOLL_FREE: Final[str] = "1800-180-1551"


def get_whatsapp_interface_id() -> str:
    """Returns configured WhatsApp webhook interface ID from environment or default."""
    return os.getenv("WHATSAPP_INTERFACE_ID", DEFAULT_WHATSAPP_INTERFACE)


def get_sip_trunk_interface_id() -> str:
    """Returns configured IVR SIP trunk interface ID from environment or default."""
    return os.getenv("IVR_SIP_TRUNK_INTERFACE_ID", DEFAULT_SIP_TRUNK_INTERFACE)


def get_sigtran_interface_id() -> str:
    """Returns configured USSD SIGTRAN interface ID from environment or default."""
    return os.getenv("USSD_SIGTRAN_INTERFACE_ID", DEFAULT_SIGTRAN_INTERFACE)


def get_sms_gateway_id() -> str:
    """Returns configured SMS gateway identifier from environment or default."""
    return os.getenv("SMS_GATEWAY_INTERFACE_ID", DEFAULT_SMS_GATEWAY)


def get_helpline_number() -> str:
    """Returns configured toll-free grievance helpline number from environment or default."""
    return os.getenv("HELPLINE_TOLL_FREE_NUMBER", DEFAULT_HELPLINE_TOLL_FREE)
