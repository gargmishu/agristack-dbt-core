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
    LiveAgriRegistryService,
    MockAgriRegistryService,
    create_agri_registry_service,
)
from src.services.dpi.dpi_mock_fixtures import (
    INVALID_SURVEY_NUMBER,
    UNVERIFIED_IDENTITY_PREFIX,
)


@pytest.mark.asyncio
async def test_mock_agri_registry_verify_land_record() -> None:
    service = MockAgriRegistryService()
    citizen_hash = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"
    is_valid = await service.verify_land_record(citizen_hash, "LAND-REC-1002")
    assert is_valid is True


@pytest.mark.asyncio
async def test_mock_agri_registry_reject_unentitled_parcel() -> None:
    service = MockAgriRegistryService()
    citizen_hash = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"
    is_valid = await service.verify_land_record(citizen_hash, "LAND-REC-3006")
    assert is_valid is False


@pytest.mark.asyncio
async def test_mock_agri_registry_reject_zero_token() -> None:
    service = MockAgriRegistryService()
    zero_hash = "0" * 64
    is_valid = await service.verify_land_record(zero_hash, "LAND-REC-1002")
    assert is_valid is False


@pytest.mark.asyncio
async def test_mock_agri_registry_reject_invalid_prefix() -> None:
    service = MockAgriRegistryService()
    citizen_hash = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"
    is_valid = await service.verify_land_record(citizen_hash, "INVALID-REC-999")
    assert is_valid is False


@pytest.mark.asyncio
async def test_mock_agri_registry_reject_unverified_identity_prefix() -> None:
    service = MockAgriRegistryService()
    unverified_hash = UNVERIFIED_IDENTITY_PREFIX + "a" * (64 - len(UNVERIFIED_IDENTITY_PREFIX))
    is_valid = await service.verify_land_record(unverified_hash, "LAND-REC-1002")
    assert is_valid is False


@pytest.mark.asyncio
async def test_mock_agri_registry_reject_invalid_survey_number() -> None:
    service = MockAgriRegistryService()
    citizen_hash = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"
    is_valid = await service.verify_land_record(citizen_hash, f"LAND-{INVALID_SURVEY_NUMBER}")
    assert is_valid is False


@pytest.mark.asyncio
async def test_mock_agri_registry_reject_empty_record_id() -> None:
    service = MockAgriRegistryService()
    citizen_hash = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"
    assert await service.verify_land_record(citizen_hash, "   ") is False


@pytest.mark.asyncio
async def test_live_agri_registry_endpoint_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer agristack_key"
        assert str(request.url) == "https://agristack.gov.in/v1/land/cadastral/verify"
        return httpx.Response(
            HTTPStatus.OK,
            json={"is_entitled": True, "land_record_id": "LAND-REC-999"},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = LiveAgriRegistryService(
        endpoint_url="https://agristack.gov.in",
        api_key="agristack_key",
        http_client=client,
    )
    is_valid = await service.verify_land_record("a" * 64, "LAND-REC-999")
    assert is_valid is True


@pytest.mark.asyncio
async def test_live_agri_registry_constructor_validation() -> None:
    client = httpx.AsyncClient()
    with pytest.raises(ServiceConfigurationError, match="endpoint URL is required"):
        LiveAgriRegistryService(endpoint_url="", api_key="valid_key", http_client=client)

    with pytest.raises(ServiceConfigurationError, match="must start with 'http://' or 'https://'"):
        LiveAgriRegistryService(
            endpoint_url="agristack.gov.in", api_key="valid_key", http_client=client
        )

    with pytest.raises(ServiceConfigurationError, match="API key is required"):
        LiveAgriRegistryService(
            endpoint_url="https://agristack.gov.in", api_key="", http_client=client
        )


@pytest.mark.asyncio
async def test_live_agri_registry_fail_closed_on_500() -> None:
    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(HTTPStatus.INTERNAL_SERVER_ERROR, text="Internal Registry Outage")

    client = httpx.AsyncClient(transport=httpx.MockTransport(error_handler))
    service = LiveAgriRegistryService(
        endpoint_url="https://agristack.gov.in",
        api_key="valid_key",
        http_client=client,
    )
    with pytest.raises(ServiceUnavailableError, match="status=500"):
        await service.verify_land_record("a" * 64, "LAND-REC-1002")


@pytest.mark.asyncio
async def test_live_agri_registry_fail_closed_on_auth_failure() -> None:
    def auth_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(HTTPStatus.UNAUTHORIZED, text="Unauthorized")

    client = httpx.AsyncClient(transport=httpx.MockTransport(auth_handler))
    service = LiveAgriRegistryService(
        endpoint_url="https://agristack.gov.in",
        api_key="invalid_key",
        http_client=client,
    )
    with pytest.raises(ServiceAuthenticationError, match="AgriStack authentication failed"):
        await service.verify_land_record("a" * 64, "LAND-REC-1002")


@pytest.mark.asyncio
async def test_live_agri_registry_malformed_payload_error() -> None:
    def bad_request_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(HTTPStatus.BAD_REQUEST, text="Invalid land record identifier format")

    client = httpx.AsyncClient(transport=httpx.MockTransport(bad_request_handler))
    service = LiveAgriRegistryService(
        endpoint_url="https://agristack.gov.in",
        api_key="valid_key",
        http_client=client,
    )
    with pytest.raises(ServiceRequestPayloadError, match="Invalid land record identifier"):
        await service.verify_land_record("a" * 64, "INVALID_FORMAT")


@pytest.mark.asyncio
async def test_live_agri_registry_response_payload_contract_violation() -> None:
    def invalid_schema_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(HTTPStatus.OK, json={"status": "ok"})  # missing 'is_entitled'

    client = httpx.AsyncClient(transport=httpx.MockTransport(invalid_schema_handler))
    service = LiveAgriRegistryService(
        endpoint_url="https://agristack.gov.in",
        api_key="valid_key",
        http_client=client,
    )
    with pytest.raises(ServiceResponsePayloadError, match="invalid schema"):
        await service.verify_land_record("a" * 64, "LAND-REC-1002")


@pytest.mark.asyncio
async def test_live_agri_registry_non_dict_json_response() -> None:
    def list_json_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(HTTPStatus.OK, json=["unexpected", "array"])

    client = httpx.AsyncClient(transport=httpx.MockTransport(list_json_handler))
    service = LiveAgriRegistryService(
        endpoint_url="https://agristack.gov.in",
        api_key="valid_key",
        http_client=client,
    )
    with pytest.raises(ServiceResponsePayloadError, match="non-dictionary JSON"):
        await service.verify_land_record("a" * 64, "LAND-REC-1002")


@pytest.mark.asyncio
async def test_live_agri_registry_service_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGRISTACK_REGISTRY_API_ENDPOINT", raising=False)
    monkeypatch.delenv("AGRISTACK_REGISTRY_API_KEY", raising=False)

    with pytest.raises(ServiceConfigurationError, match="endpoint URL is required"):
        LiveAgriRegistryService.from_env()

    with pytest.raises(ServiceConfigurationError, match="API key is required"):
        LiveAgriRegistryService.from_env(endpoint_url="https://agristack.gov.in")

    # From explicit parameters
    service = LiveAgriRegistryService.from_env(
        endpoint_url="https://agristack.gov.in", api_key="valid_key"
    )
    assert isinstance(service, LiveAgriRegistryService)

    # From environment variables
    monkeypatch.setenv("AGRISTACK_REGISTRY_API_ENDPOINT", "https://agristack.gov.in")
    monkeypatch.setenv("AGRISTACK_REGISTRY_API_KEY", "valid_key")
    service_env = LiveAgriRegistryService.from_env()
    assert isinstance(service_env, LiveAgriRegistryService)


@pytest.mark.asyncio
async def test_create_agri_registry_service_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("AGRISTACK_REGISTRY_API_ENDPOINT", raising=False)
    monkeypatch.delenv("AGRISTACK_REGISTRY_API_KEY", raising=False)

    service = create_agri_registry_service()
    assert isinstance(service, MockAgriRegistryService)

    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ServiceConfigurationError, match="AGRISTACK_REGISTRY_API_ENDPOINT"):
        create_agri_registry_service()

    monkeypatch.setenv("AGRISTACK_REGISTRY_API_ENDPOINT", "https://agristack.gov.in")
    monkeypatch.setenv("AGRISTACK_REGISTRY_API_KEY", "prod_token")
    live_service = create_agri_registry_service()
    assert isinstance(live_service, LiveAgriRegistryService)
