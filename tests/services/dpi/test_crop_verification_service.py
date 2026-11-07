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
    LiveCropVerificationService,
    MockCropVerificationService,
    create_crop_verification_service,
)
from src.services.dpi.dpi_mock_fixtures import (
    INELIGIBLE_CROP_PREFIX,
    UNVERIFIED_IDENTITY_PREFIX,
)


@pytest.mark.asyncio
async def test_mock_crop_verification_service() -> None:
    service = MockCropVerificationService()
    citizen_hash = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"
    assert (
        await service.verify_crop_cultivation(citizen_hash, "LAND-REC-1002", "Onion", "KHARIF-2026")
        is True
    )
    assert (
        await service.verify_crop_cultivation(
            citizen_hash, "LAND-REC-1002", f"{INELIGIBLE_CROP_PREFIX}_TOBACCO", "KHARIF-2026"
        )
        is False
    )
    assert (
        await service.verify_crop_cultivation(citizen_hash, "LAND-REC-1002", "   ", "KHARIF-2026")
        is False
    )
    assert (
        await service.verify_crop_cultivation(citizen_hash, "LAND-REC-1002", "Onion", "   ")
        is False
    )
    unverified_hash = UNVERIFIED_IDENTITY_PREFIX + "a" * (64 - len(UNVERIFIED_IDENTITY_PREFIX))
    assert (
        await service.verify_crop_cultivation(
            unverified_hash, "LAND-REC-1002", "Onion", "KHARIF-2026"
        )
        is False
    )


@pytest.mark.asyncio
async def test_live_crop_verification_endpoint_success_and_invalid_schema() -> None:
    def valid_crop_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer satellite_key"
        assert str(request.url) == "https://openagrinet.gov.in/v1/crop-satellite/verify"
        return httpx.Response(
            HTTPStatus.OK,
            json={"is_crop_verified": True, "land_record_id": "LAND-REC-999"},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(valid_crop_handler))
    service = LiveCropVerificationService(
        endpoint_url="https://openagrinet.gov.in",
        api_key="satellite_key",
        http_client=client,
    )
    assert (
        await service.verify_crop_cultivation("a" * 64, "LAND-REC-999", "Onion", "KHARIF-2026")
        is True
    )

    def invalid_crop_schema_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(HTTPStatus.OK, json={"status": "ok"})

    bad_client = httpx.AsyncClient(transport=httpx.MockTransport(invalid_crop_schema_handler))
    bad_service = LiveCropVerificationService(
        endpoint_url="https://openagrinet.gov.in",
        api_key="satellite_key",
        http_client=bad_client,
    )
    with pytest.raises(ServiceResponsePayloadError, match="invalid schema"):
        await bad_service.verify_crop_cultivation("a" * 64, "LAND-REC-999", "Onion", "KHARIF-2026")


@pytest.mark.asyncio
async def test_live_crop_verification_error_handling() -> None:
    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(HTTPStatus.INTERNAL_SERVER_ERROR, text="Satellite Gateway Outage")

    client = httpx.AsyncClient(transport=httpx.MockTransport(error_handler))
    service = LiveCropVerificationService(
        endpoint_url="https://openagrinet.gov.in",
        api_key="valid_key",
        http_client=client,
    )
    with pytest.raises(ServiceUnavailableError, match="status=500"):
        await service.verify_crop_cultivation("a" * 64, "LAND-REC-1002", "Onion", "KHARIF-2026")

    def auth_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(HTTPStatus.UNAUTHORIZED, text="Unauthorized")

    auth_client = httpx.AsyncClient(transport=httpx.MockTransport(auth_handler))
    auth_service = LiveCropVerificationService(
        endpoint_url="https://openagrinet.gov.in",
        api_key="invalid_key",
        http_client=auth_client,
    )
    with pytest.raises(
        ServiceAuthenticationError, match="Crop Satellite Verification authentication failed"
    ):
        await auth_service.verify_crop_cultivation(
            "a" * 64, "LAND-REC-1002", "Onion", "KHARIF-2026"
        )

    def bad_request_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(HTTPStatus.BAD_REQUEST, text="Invalid crop verification payload")

    bad_req_client = httpx.AsyncClient(transport=httpx.MockTransport(bad_request_handler))
    bad_req_service = LiveCropVerificationService(
        endpoint_url="https://openagrinet.gov.in",
        api_key="valid_key",
        http_client=bad_req_client,
    )
    with pytest.raises(ServiceRequestPayloadError, match="Invalid crop verification payload"):
        await bad_req_service.verify_crop_cultivation(
            "a" * 64, "LAND-REC-1002", "Onion", "KHARIF-2026"
        )


@pytest.mark.asyncio
async def test_create_crop_verification_service_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("CROP_SATELLITE_API_ENDPOINT", raising=False)
    monkeypatch.delenv("CROP_SATELLITE_API_KEY", raising=False)

    service = create_crop_verification_service()
    assert isinstance(service, MockCropVerificationService)

    explicit_live = create_crop_verification_service(
        endpoint_url="https://openagrinet.gov.in",
        api_key="explicit_key",
    )
    assert isinstance(explicit_live, LiveCropVerificationService)

    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ServiceConfigurationError, match="CROP_SATELLITE_API_ENDPOINT"):
        create_crop_verification_service()

    monkeypatch.setenv("CROP_SATELLITE_API_ENDPOINT", "https://openagrinet.gov.in")
    monkeypatch.setenv("CROP_SATELLITE_API_KEY", "prod_token")
    live_service = create_crop_verification_service()
    assert isinstance(live_service, LiveCropVerificationService)
