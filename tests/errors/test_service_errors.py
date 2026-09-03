"""Unit tests for structured service errors and RFC 7807 problem details serialization."""

from http import HTTPStatus

from src.errors.service_errors import (
    ServiceAuthenticationError,
    ServiceConfigurationError,
    ServiceIntegrationError,
    ServiceUnavailableError,
)


def test_service_integration_error_defaults_and_str() -> None:
    error = ServiceIntegrationError("Generic gateway failure")
    assert str(error) == "Generic gateway failure"
    assert error.message == "Generic gateway failure"
    assert error.service_name is None
    assert error.status_code == HTTPStatus.BAD_GATEWAY
    assert error.is_retryable is False

    details = error.to_problem_details()
    assert details["type"] == "https://api.agristack.gov.in/errors/service-integration-error"
    assert details["title"] == "Base exception for all external DPI and sovereign AI service errors"
    assert details["status"] == HTTPStatus.BAD_GATEWAY
    assert details["detail"] == "Generic gateway failure"
    assert details["retryable"] is False
    assert "service" not in details


def test_service_configuration_error_properties() -> None:
    error = ServiceConfigurationError(
        "Missing BHASHINI_API_ENDPOINT",
        service_name="bhashini",
    )
    assert isinstance(error, ValueError)
    assert isinstance(error, ServiceIntegrationError)
    assert error.service_name == "bhashini"
    assert error.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
    assert error.is_retryable is False

    details = error.to_problem_details()
    assert details["type"] == "https://api.agristack.gov.in/errors/service-configuration-error"
    assert details["status"] == HTTPStatus.INTERNAL_SERVER_ERROR
    assert details["service"] == "bhashini"
    assert details["retryable"] is False


def test_service_unavailable_error_properties() -> None:
    error = ServiceUnavailableError(
        "MOSIP registry timed out after 3.0s",
        service_name="mosip",
        status_code=HTTPStatus.GATEWAY_TIMEOUT,
    )
    assert error.service_name == "mosip"
    assert error.status_code == HTTPStatus.GATEWAY_TIMEOUT
    assert error.is_retryable is True

    details = error.to_problem_details()
    assert details["type"] == "https://api.agristack.gov.in/errors/service-unavailable-error"
    assert details["status"] == HTTPStatus.GATEWAY_TIMEOUT
    assert details["service"] == "mosip"
    assert details["retryable"] is True


def test_service_authentication_error_properties() -> None:
    error = ServiceAuthenticationError(
        "OpenSPP API key rejected with 401 Unauthorized",
        service_name="openspp",
        status_code=HTTPStatus.UNAUTHORIZED,
    )
    assert error.service_name == "openspp"
    assert error.status_code == HTTPStatus.UNAUTHORIZED
    assert error.is_retryable is False

    details = error.to_problem_details()
    assert details["type"] == "https://api.agristack.gov.in/errors/service-authentication-error"
    assert details["status"] == HTTPStatus.UNAUTHORIZED
    assert details["service"] == "openspp"
    assert details["retryable"] is False
