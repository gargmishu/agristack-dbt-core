"""Unit tests for external service settings and production fail-fast validators."""

import pytest

from src.config.service_settings import (
    get_agristack_api_key,
    get_agristack_endpoint,
    get_bhashini_api_key,
    get_bhashini_endpoint,
    get_environment,
    get_identity_endpoint,
    get_openspp_endpoint,
    get_payment_endpoint,
    get_slm_endpoint,
    is_production,
)
from src.errors.service_errors import ServiceConfigurationError


def test_environment_default_and_is_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert get_environment() == "development"
    assert is_production() is False

    monkeypatch.setenv("ENVIRONMENT", "production")
    assert get_environment() == "production"
    assert is_production() is True


def test_service_settings_non_production_returns_none_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("BHASHINI_API_ENDPOINT", raising=False)
    monkeypatch.delenv("BHASHINI_API_KEY", raising=False)
    monkeypatch.delenv("AGRISTACK_REGISTRY_API_ENDPOINT", raising=False)
    monkeypatch.delenv("AGRISTACK_REGISTRY_API_KEY", raising=False)

    assert get_bhashini_endpoint() is None
    assert get_bhashini_api_key() is None
    assert get_agristack_endpoint() is None
    assert get_agristack_api_key() is None


def test_service_settings_returns_configured_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("BHASHINI_API_ENDPOINT", "https://bhashini.gov.in/api")
    monkeypatch.setenv("BHASHINI_API_KEY", "secret_bhashini_token")

    assert get_bhashini_endpoint() == "https://bhashini.gov.in/api"
    assert get_bhashini_api_key() == "secret_bhashini_token"


def test_service_settings_production_fail_fast_when_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("BHASHINI_API_ENDPOINT", raising=False)

    with pytest.raises(ServiceConfigurationError, match="BHASHINI_API_ENDPOINT"):
        get_bhashini_endpoint()


def test_service_settings_production_fail_fast_all_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("SLM_API_ENDPOINT", raising=False)
    monkeypatch.delenv("AGRISTACK_REGISTRY_API_ENDPOINT", raising=False)
    monkeypatch.delenv("MOSIP_API_ENDPOINT", raising=False)
    monkeypatch.delenv("OPENSPP_API_ENDPOINT", raising=False)
    monkeypatch.delenv("NPCI_APBS_API_ENDPOINT", raising=False)

    with pytest.raises(ServiceConfigurationError, match="SLM_API_ENDPOINT"):
        get_slm_endpoint()

    with pytest.raises(ServiceConfigurationError, match="AGRISTACK_REGISTRY_API_ENDPOINT"):
        get_agristack_endpoint()

    with pytest.raises(ServiceConfigurationError, match="MOSIP_API_ENDPOINT"):
        get_identity_endpoint()

    with pytest.raises(ServiceConfigurationError, match="OPENSPP_API_ENDPOINT"):
        get_openspp_endpoint()

    with pytest.raises(ServiceConfigurationError, match="NPCI_APBS_API_ENDPOINT"):
        get_payment_endpoint()
