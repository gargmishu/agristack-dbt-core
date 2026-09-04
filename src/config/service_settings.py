"""External DPI and Sovereign AI service configuration settings.

Defines environment variable bindings, fail-fast production validators, and service
endpoint settings for live digital public infrastructure and AI integrations.

See: decisions/step3.6_live_service_integration.md
See: .agents/skills/zero-trust-security/SKILL.md (Section 2: Fail-Fast Configuration)
"""

import os
from typing import Final

from src.errors.service_errors import ServiceConfigurationError

_DEFAULT_ENVIRONMENT: Final[str] = "development"
_PRODUCTION_ENVIRONMENT: Final[str] = "production"

__all__ = [
    "get_agristack_api_key",
    "get_agristack_endpoint",
    "get_bhashini_api_key",
    "get_bhashini_endpoint",
    "get_environment",
    "get_identity_api_key",
    "get_identity_endpoint",
    "get_openspp_api_key",
    "get_openspp_endpoint",
    "get_payment_api_key",
    "get_payment_endpoint",
    "get_slm_api_key",
    "get_slm_endpoint",
    "is_production",
]


def get_environment() -> str:
    """Returns the configured runtime application environment.

    Returns:
        Lowercase environment identifier string (e.g., 'development', 'production', 'test').
    """
    return os.getenv("ENVIRONMENT", _DEFAULT_ENVIRONMENT).strip().lower()


def is_production() -> bool:
    """Determines whether the system is running in production mode.

    Returns:
        True if running in production, False otherwise.
    """
    return get_environment() == _PRODUCTION_ENVIRONMENT


def get_bhashini_endpoint() -> str | None:
    """Returns Bhashini Speech & Translation API endpoint URL.

    Raises:
        ServiceConfigurationError: In production if 'BHASHINI_API_ENDPOINT' is missing or empty.
    """
    return _get_service_setting("BHASHINI_API_ENDPOINT", "Bhashini API Endpoint")


def get_bhashini_api_key() -> str | None:
    """Returns Bhashini Speech & Translation API key.

    Raises:
        ServiceConfigurationError: In production if 'BHASHINI_API_KEY' is missing or empty.
    """
    return _get_service_setting("BHASHINI_API_KEY", "Bhashini API Key")


def get_slm_endpoint() -> str | None:
    """Returns Sovereign SLM inference endpoint URL.

    Raises:
        ServiceConfigurationError: In production if 'SLM_API_ENDPOINT' is missing or empty.
    """
    return _get_service_setting("SLM_API_ENDPOINT", "Sovereign SLM Endpoint")


def get_slm_api_key() -> str | None:
    """Returns Sovereign SLM API key.

    Raises:
        ServiceConfigurationError: In production if 'SLM_API_KEY' is missing or empty.
    """
    return _get_service_setting("SLM_API_KEY", "Sovereign SLM API Key")


def get_agristack_endpoint() -> str | None:
    """Returns AgriStack Land & Farmer Registry Gateway endpoint URL.

    Raises:
        ServiceConfigurationError: In production if 'AGRISTACK_REGISTRY_API_ENDPOINT' is missing.
    """
    return _get_service_setting(
        "AGRISTACK_REGISTRY_API_ENDPOINT", "AgriStack Registry API Endpoint"
    )


def get_agristack_api_key() -> str | None:
    """Returns AgriStack Land & Farmer Registry Gateway API key.

    Raises:
        ServiceConfigurationError: In production if 'AGRISTACK_REGISTRY_API_KEY' is missing.
    """
    return _get_service_setting("AGRISTACK_REGISTRY_API_KEY", "AgriStack Registry API Key")


def get_identity_endpoint() -> str | None:
    """Returns MOSIP / Sovereign Identity Verification API endpoint URL.

    Raises:
        ServiceConfigurationError: In production if 'MOSIP_API_ENDPOINT' is missing or empty.
    """
    return _get_service_setting("MOSIP_API_ENDPOINT", "MOSIP Identity API Endpoint")


def get_identity_api_key() -> str | None:
    """Returns MOSIP / Sovereign Identity Verification API key.

    Raises:
        ServiceConfigurationError: In production if 'MOSIP_API_KEY' is missing or empty.
    """
    return _get_service_setting("MOSIP_API_KEY", "MOSIP Identity API Key")


def get_openspp_endpoint() -> str | None:
    """Returns OpenSPP Social Protection Platform endpoint URL.

    Raises:
        ServiceConfigurationError: In production if 'OPENSPP_API_ENDPOINT' is missing or empty.
    """
    return _get_service_setting("OPENSPP_API_ENDPOINT", "OpenSPP API Endpoint")


def get_openspp_api_key() -> str | None:
    """Returns OpenSPP Social Protection Platform API key.

    Raises:
        ServiceConfigurationError: In production if 'OPENSPP_API_KEY' is missing or empty.
    """
    return _get_service_setting("OPENSPP_API_KEY", "OpenSPP API Key")


def get_payment_endpoint() -> str | None:
    """Returns NPCI APBS / PFMS Payment Rail endpoint URL.

    Raises:
        ServiceConfigurationError: In production if 'NPCI_APBS_API_ENDPOINT' is missing or empty.
    """
    return _get_service_setting("NPCI_APBS_API_ENDPOINT", "NPCI APBS Payment Rail Endpoint")


def get_payment_api_key() -> str | None:
    """Returns NPCI APBS / PFMS Payment Rail API key.

    Raises:
        ServiceConfigurationError: In production if 'NPCI_APBS_API_KEY' is missing or empty.
    """
    return _get_service_setting("NPCI_APBS_API_KEY", "NPCI APBS Payment Rail API Key")


# -----------------------------------------------------------------------------
# Private Helpers
# -----------------------------------------------------------------------------


def _get_service_setting(
    variable_name: str,
    display_name: str,
    is_required_in_production: bool = True,
) -> str | None:
    """Reads and validates an external service setting.

    In production mode, missing or empty values raise ServiceConfigurationError immediately
    to prevent unconfigured live service execution or silent degradation to mock fixtures.

    Args:
        variable_name: Environment variable key name.
        display_name: Human-readable service setting name for error messages.
        is_required_in_production: Whether the variable is mandatory in production mode.

    Returns:
        Configured string value if present, or None in non-production environments.

    Raises:
        ServiceConfigurationError: If variable is required in production but missing or empty.
    """
    raw_value = os.getenv(variable_name)
    stripped_value = raw_value.strip() if raw_value else None

    if is_production() and is_required_in_production and not stripped_value:
        # Extract service prefix (e.g., 'BHASHINI' from 'BHASHINI_API_KEY') to populate
        # the machine-readable service identifier for RFC 7807 problem details payloads.
        service_identifier = variable_name.split("_", maxsplit=1)[0].lower()
        raise ServiceConfigurationError(
            f"Required production environment variable '{variable_name}' "
            f"({display_name}) is missing or empty.",
            service_name=service_identifier,
        )

    return stripped_value
