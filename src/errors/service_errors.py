"""Service integration exceptions and RFC 7807 problem details error types.

Defines structured domain exceptions for live external Digital Public Infrastructure (DPI)
and Sovereign AI adapter integrations.

See: decisions/step3.6_live_service_integration.md
"""

from http import HTTPStatus
from typing import Any, Final

__all__ = [
    "ServiceAuthenticationError",
    "ServiceConfigurationError",
    "ServiceIntegrationError",
    "ServiceRequestPayloadError",
    "ServiceResponsePayloadError",
    "ServiceUnavailableError",
]

_DEFAULT_ERROR_TYPE_URI_PREFIX: Final[str] = "https://api.agristack.gov.in/errors"


class ServiceIntegrationError(Exception):
    """Base exception for all external DPI and sovereign AI service errors.

    Captures structured metadata for telemetry, error classification, and
    RFC 7807 Problem Details serialization.
    """

    def __init__(
        self,
        message: str,
        *,
        service_name: str | None = None,
        status_code: int = HTTPStatus.BAD_GATEWAY,
        is_retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.service_name = service_name
        self.status_code = status_code
        self.is_retryable = is_retryable

    def to_problem_details(self) -> dict[str, Any]:
        """Serializes error to RFC 7807 Problem Details format.

        Returns:
            Dictionary matching RFC 7807 schema with sanitized error details.
        """
        payload: dict[str, Any] = {
            "type": f"{_DEFAULT_ERROR_TYPE_URI_PREFIX}/{self._error_slug()}",
            "title": self._error_title(),
            "status": self.status_code,
            "detail": self.message,
            "retryable": self.is_retryable,
        }
        if self.service_name:
            payload["service"] = self.service_name
        return payload

    def _error_slug(self) -> str:
        """Derives kebab-case slug from class name."""
        name = self.__class__.__name__
        slug = ""
        for i, char in enumerate(name):
            if char.isupper() and i > 0:
                slug += "-"
            slug += char.lower()
        return slug

    def _error_title(self) -> str:
        """Derives human-readable title for problem details."""
        doc = self.__doc__
        if doc:
            first_line = doc.strip().split("\n")[0].rstrip(".")
            return first_line
        return "Service Integration Error"


class ServiceConfigurationError(ServiceIntegrationError, ValueError):
    """Raised when mandatory live service endpoint URL or API key is missing in production."""

    def __init__(
        self,
        message: str,
        *,
        service_name: str | None = None,
    ) -> None:
        super().__init__(
            message,
            service_name=service_name,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            is_retryable=False,
        )


class ServiceUnavailableError(ServiceIntegrationError):
    """Raised when an authoritative external service is unreachable, times out, or fails."""

    def __init__(
        self,
        message: str,
        *,
        service_name: str | None = None,
        status_code: int = HTTPStatus.SERVICE_UNAVAILABLE,
    ) -> None:
        super().__init__(
            message,
            service_name=service_name,
            status_code=status_code,
            is_retryable=True,
        )


class ServiceAuthenticationError(ServiceIntegrationError):
    """Raised when external service credentials (API key, Bearer token) are rejected."""

    def __init__(
        self,
        message: str,
        *,
        service_name: str | None = None,
        status_code: int = HTTPStatus.BAD_GATEWAY,
    ) -> None:
        super().__init__(
            message,
            service_name=service_name,
            status_code=status_code,
            is_retryable=False,
        )


class ServiceRequestPayloadError(ServiceIntegrationError, ValueError):
    """Raised when external service rejects request payload as malformed (HTTP 400/415/422)."""

    def __init__(
        self,
        message: str,
        *,
        service_name: str | None = None,
        status_code: int = HTTPStatus.BAD_REQUEST,
    ) -> None:
        super().__init__(
            message,
            service_name=service_name,
            status_code=status_code,
            is_retryable=False,
        )


class ServiceResponsePayloadError(ServiceIntegrationError):
    """Raised when external service returns response violating the schema contract (HTTP 502)."""

    def __init__(
        self,
        message: str,
        *,
        service_name: str | None = None,
        status_code: int = HTTPStatus.BAD_GATEWAY,
    ) -> None:
        super().__init__(
            message,
            service_name=service_name,
            status_code=status_code,
            is_retryable=True,
        )
