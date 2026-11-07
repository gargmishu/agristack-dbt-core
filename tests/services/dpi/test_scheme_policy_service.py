from http import HTTPStatus

import httpx
import pytest

from src.errors.service_errors import (
    ServiceAuthenticationError,
    ServiceConfigurationError,
    ServiceRequestPayloadError,
    ServiceResponsePayloadError,
    ServiceUnavailableError,
)
from src.services.dpi import (
    LiveSchemePolicyService,
    MockSchemePolicyService,
    create_scheme_policy_service,
)
from src.services.dpi.dpi_mock_fixtures import EXCLUDED_POLICY_PREFIX


@pytest.mark.asyncio
async def test_mock_scheme_policy_service() -> None:
    service = MockSchemePolicyService()
    assert await service.verify_scheme_policy_coverage("Nashik", "Onion", "KHARIF-2026") is True
    assert (
        await service.verify_scheme_policy_coverage(
            f"{EXCLUDED_POLICY_PREFIX}_DISTRICT", "Onion", "KHARIF-2026"
        )
        is False
    )
    assert (
        await service.verify_scheme_policy_coverage(
            "Nashik", f"{EXCLUDED_POLICY_PREFIX}_CROP", "KHARIF-2026"
        )
        is False
    )
    assert await service.verify_scheme_policy_coverage("   ", "Onion", "KHARIF-2026") is False


@pytest.mark.asyncio
async def test_live_scheme_policy_endpoint_success_and_invalid_schema() -> None:
    def valid_policy_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer dhara_key"
        assert str(request.url) == "https://datadhara.ekstep.org/v1/scheme-policy/verify"
        return httpx.Response(
            HTTPStatus.OK,
            json={"is_policy_covered": True, "district": "Nashik", "crop_name": "Onion"},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(valid_policy_handler))
    service = LiveSchemePolicyService(
        endpoint_url="https://datadhara.ekstep.org",
        api_key="dhara_key",
        http_client=client,
    )
    assert await service.verify_scheme_policy_coverage("Nashik", "Onion", "KHARIF-2026") is True

    def invalid_policy_schema_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(HTTPStatus.OK, json={"status": "ok"})

    bad_client = httpx.AsyncClient(transport=httpx.MockTransport(invalid_policy_schema_handler))
    bad_service = LiveSchemePolicyService(
        endpoint_url="https://datadhara.ekstep.org",
        api_key="dhara_key",
        http_client=bad_client,
    )
    with pytest.raises(ServiceResponsePayloadError, match="invalid schema"):
        await bad_service.verify_scheme_policy_coverage("Nashik", "Onion", "KHARIF-2026")


@pytest.mark.asyncio
async def test_live_scheme_policy_error_handling() -> None:
    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(HTTPStatus.INTERNAL_SERVER_ERROR, text="Policy Gateway Outage")

    client = httpx.AsyncClient(transport=httpx.MockTransport(error_handler))
    service = LiveSchemePolicyService(
        endpoint_url="https://datadhara.ekstep.org",
        api_key="valid_key",
        http_client=client,
    )
    with pytest.raises(ServiceUnavailableError, match="status=500"):
        await service.verify_scheme_policy_coverage("Nashik", "Onion", "KHARIF-2026")

    def auth_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(HTTPStatus.FORBIDDEN, text="Forbidden")

    auth_client = httpx.AsyncClient(transport=httpx.MockTransport(auth_handler))
    auth_service = LiveSchemePolicyService(
        endpoint_url="https://datadhara.ekstep.org",
        api_key="invalid_key",
        http_client=auth_client,
    )
    with pytest.raises(
        ServiceAuthenticationError, match="Scheme Policy Metadata authentication failed"
    ):
        await auth_service.verify_scheme_policy_coverage("Nashik", "Onion", "KHARIF-2026")

    def bad_request_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(HTTPStatus.UNPROCESSABLE_ENTITY, text="Invalid LGD district code")

    bad_req_client = httpx.AsyncClient(transport=httpx.MockTransport(bad_request_handler))
    bad_req_service = LiveSchemePolicyService(
        endpoint_url="https://datadhara.ekstep.org",
        api_key="valid_key",
        http_client=bad_req_client,
    )
    with pytest.raises(ServiceRequestPayloadError, match="Invalid LGD district code"):
        await bad_req_service.verify_scheme_policy_coverage("INVALID", "Onion", "KHARIF-2026")


@pytest.mark.asyncio
async def test_create_scheme_policy_service_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("SCHEME_POLICY_API_ENDPOINT", raising=False)
    monkeypatch.delenv("SCHEME_POLICY_API_KEY", raising=False)

    service = create_scheme_policy_service()
    assert isinstance(service, MockSchemePolicyService)

    explicit_live = create_scheme_policy_service(
        endpoint_url="https://datadhara.ekstep.org",
        api_key="explicit_key",
    )
    assert isinstance(explicit_live, LiveSchemePolicyService)

    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ServiceConfigurationError, match="SCHEME_POLICY_API_ENDPOINT"):
        create_scheme_policy_service()

    monkeypatch.setenv("SCHEME_POLICY_API_ENDPOINT", "https://datadhara.ekstep.org")
    monkeypatch.setenv("SCHEME_POLICY_API_KEY", "prod_token")
    live_service = create_scheme_policy_service()
    assert isinstance(live_service, LiveSchemePolicyService)
