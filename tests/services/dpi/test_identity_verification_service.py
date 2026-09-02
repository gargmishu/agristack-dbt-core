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
    LiveIdentityVerificationService,
    MockIdentityVerificationService,
    create_identity_verification_service,
)
from src.services.dpi.dpi_mock_fixtures import (
    UNVERIFIED_IDENTITY_PREFIX,
    UNVERIFIED_IDENTITY_TOKEN_ZERO,
)


@pytest.mark.asyncio
async def test_mock_identity_verification_verify_token() -> None:
    service = MockIdentityVerificationService()
    citizen_hash = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"
    is_valid = await service.verify_identity_token(citizen_hash)
    assert is_valid is True


@pytest.mark.asyncio
async def test_mock_identity_verification_reject_zero_token() -> None:
    service = MockIdentityVerificationService()
    is_valid = await service.verify_identity_token(UNVERIFIED_IDENTITY_TOKEN_ZERO)
    assert is_valid is False


@pytest.mark.asyncio
async def test_mock_identity_verification_reject_unverified_prefix() -> None:
    service = MockIdentityVerificationService()
    unverified_hash = UNVERIFIED_IDENTITY_PREFIX + "a" * (64 - len(UNVERIFIED_IDENTITY_PREFIX))
    is_valid = await service.verify_identity_token(unverified_hash)
    assert is_valid is False


@pytest.mark.asyncio
async def test_live_identity_verification_endpoint_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer mosip_token"
        return httpx.Response(200, json={"is_verified": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = LiveIdentityVerificationService(
        endpoint_url="https://mosip.gov.in",
        api_key="mosip_token",
        http_client=client,
    )
    is_valid = await service.verify_identity_token("a" * 64)
    assert is_valid is True


@pytest.mark.asyncio
async def test_live_identity_verification_constructor_validation() -> None:
    client = httpx.AsyncClient()
    with pytest.raises(ServiceConfigurationError, match="endpoint URL is required"):
        LiveIdentityVerificationService(endpoint_url="", api_key="valid_key", http_client=client)

    with pytest.raises(ServiceConfigurationError, match="API key is required"):
        LiveIdentityVerificationService(
            endpoint_url="https://mosip.gov.in", api_key="", http_client=client
        )


@pytest.mark.asyncio
async def test_live_identity_verification_fail_closed_on_500() -> None:
    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="MOSIP Outage")

    client = httpx.AsyncClient(transport=httpx.MockTransport(error_handler))
    service = LiveIdentityVerificationService(
        endpoint_url="https://mosip.gov.in",
        api_key="valid_key",
        http_client=client,
    )
    with pytest.raises(ServiceUnavailableError, match="status=500"):
        await service.verify_identity_token("a" * 64)


@pytest.mark.asyncio
async def test_live_identity_verification_fail_closed_on_auth_failure() -> None:
    def auth_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="Forbidden")

    client = httpx.AsyncClient(transport=httpx.MockTransport(auth_handler))
    service = LiveIdentityVerificationService(
        endpoint_url="https://mosip.gov.in",
        api_key="invalid_key",
        http_client=client,
    )
    with pytest.raises(ServiceAuthenticationError, match="MOSIP verification failed"):
        await service.verify_identity_token("a" * 64)


@pytest.mark.asyncio
async def test_live_identity_verification_malformed_payload_error() -> None:
    def bad_request_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="Invalid HMAC token length: expected 64 hex characters")

    client = httpx.AsyncClient(transport=httpx.MockTransport(bad_request_handler))
    service = LiveIdentityVerificationService(
        endpoint_url="https://mosip.gov.in",
        api_key="valid_key",
        http_client=client,
    )
    with pytest.raises(ServiceRequestPayloadError, match="Invalid HMAC token length"):
        await service.verify_identity_token("short_token")


@pytest.mark.asyncio
async def test_live_identity_verification_response_payload_contract_violation() -> None:
    def invalid_schema_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "ok"})  # missing 'is_verified'

    client = httpx.AsyncClient(transport=httpx.MockTransport(invalid_schema_handler))
    service = LiveIdentityVerificationService(
        endpoint_url="https://mosip.gov.in",
        api_key="valid_key",
        http_client=client,
    )
    with pytest.raises(ServiceResponsePayloadError, match="invalid schema"):
        await service.verify_identity_token("a" * 64)


@pytest.mark.asyncio
async def test_live_identity_verification_non_dict_json_response() -> None:
    def list_json_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["unexpected", "array"])

    client = httpx.AsyncClient(transport=httpx.MockTransport(list_json_handler))
    service = LiveIdentityVerificationService(
        endpoint_url="https://mosip.gov.in",
        api_key="valid_key",
        http_client=client,
    )
    with pytest.raises(ServiceResponsePayloadError, match="non-dictionary JSON"):
        await service.verify_identity_token("a" * 64)



@pytest.mark.asyncio
async def test_create_identity_verification_service_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("MOSIP_API_ENDPOINT", raising=False)
    monkeypatch.delenv("MOSIP_API_KEY", raising=False)

    service = create_identity_verification_service()
    assert isinstance(service, MockIdentityVerificationService)

    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ServiceConfigurationError, match="MOSIP_API_ENDPOINT"):
        create_identity_verification_service()

    monkeypatch.setenv("MOSIP_API_ENDPOINT", "https://mosip.gov.in")
    monkeypatch.setenv("MOSIP_API_KEY", "prod_token")
    live_service = create_identity_verification_service()
    assert isinstance(live_service, LiveIdentityVerificationService)
