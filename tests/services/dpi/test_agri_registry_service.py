import httpx
import pytest

from src.services.dpi import AgriRegistryService
from src.services.dpi.dpi_mock_fixtures import (
    INVALID_SURVEY_NUMBER,
    UNVERIFIED_IDENTITY_PREFIX,
)


@pytest.mark.asyncio
async def test_agri_registry_verify_land_record() -> None:
    service = AgriRegistryService()
    citizen_hash = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"
    is_valid = await service.verify_land_record(citizen_hash, "LAND-REC-1002")
    assert is_valid is True


@pytest.mark.asyncio
async def test_agri_registry_reject_unentitled_parcel() -> None:
    service = AgriRegistryService()
    citizen_hash = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"
    is_valid = await service.verify_land_record(citizen_hash, "LAND-REC-3006")
    assert is_valid is False


@pytest.mark.asyncio
async def test_agri_registry_reject_zero_token() -> None:
    service = AgriRegistryService()
    zero_hash = "0" * 64
    is_valid = await service.verify_land_record(zero_hash, "LAND-REC-1002")
    assert is_valid is False


@pytest.mark.asyncio
async def test_agri_registry_reject_invalid_prefix() -> None:
    service = AgriRegistryService()
    citizen_hash = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"
    is_valid = await service.verify_land_record(citizen_hash, "INVALID-REC-999")
    assert is_valid is False


@pytest.mark.asyncio
async def test_agri_registry_reject_unverified_identity_prefix() -> None:
    service = AgriRegistryService()
    unverified_hash = UNVERIFIED_IDENTITY_PREFIX + "a" * (64 - len(UNVERIFIED_IDENTITY_PREFIX))
    is_valid = await service.verify_land_record(unverified_hash, "LAND-REC-1002")
    assert is_valid is False


@pytest.mark.asyncio
async def test_agri_registry_reject_invalid_survey_number() -> None:
    service = AgriRegistryService()
    citizen_hash = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"
    is_valid = await service.verify_land_record(citizen_hash, f"LAND-{INVALID_SURVEY_NUMBER}")
    assert is_valid is False


@pytest.mark.asyncio
async def test_agri_registry_reject_empty_record_id() -> None:
    service = AgriRegistryService()
    citizen_hash = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"
    assert await service.verify_land_record(citizen_hash, "   ") is False


@pytest.mark.asyncio
async def test_agri_registry_live_endpoint_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer agristack_key"
        return httpx.Response(200, json={"is_entitled": True, "land_record_id": "LAND-REC-999"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = AgriRegistryService(
        endpoint_url="https://agristack.gov.in",
        api_key="agristack_key",
        http_client=client,
    )
    is_valid = await service.verify_land_record("a" * 64, "LAND-REC-999")
    assert is_valid is True


@pytest.mark.asyncio
async def test_agri_registry_live_endpoint_error_fallback() -> None:
    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Registry Timeout")

    client = httpx.AsyncClient(transport=httpx.MockTransport(error_handler))
    service = AgriRegistryService(
        endpoint_url="https://agristack.gov.in",
        api_key="agristack_key",
        http_client=client,
    )
    # Falls back to mock
    is_valid = await service.verify_land_record("a" * 64, "LAND-REC-1002")
    assert is_valid is True


@pytest.mark.asyncio
async def test_agri_registry_ephemeral_client_error_fallback() -> None:
    service = AgriRegistryService(
        endpoint_url="http://invalid.unreachable.endpoint.local:9999",
        api_key="agristack_key",
    )
    is_valid = await service.verify_land_record("a" * 64, "LAND-REC-1002")
    assert is_valid is True


@pytest.mark.asyncio
async def test_agri_registry_no_api_key_and_non_dict_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "Authorization" not in request.headers
        return httpx.Response(200, json="invalid string response")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = AgriRegistryService(
        endpoint_url="https://agristack.gov.in",
        api_key=None,
        http_client=client,
    )
    is_valid = await service.verify_land_record("a" * 64, "LAND-REC-1002")
    assert is_valid is True
