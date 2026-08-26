import httpx
import pytest

from src.services.dpi import IdentityVerificationService
from src.services.dpi.dpi_mock_fixtures import (
    UNVERIFIED_IDENTITY_PREFIX,
    UNVERIFIED_IDENTITY_TOKEN_ZERO,
)


@pytest.mark.asyncio
async def test_identity_verification_verify_token() -> None:
    service = IdentityVerificationService()
    citizen_hash = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"
    is_valid = await service.verify_identity_token(citizen_hash)
    assert is_valid is True


@pytest.mark.asyncio
async def test_identity_verification_reject_zero_token() -> None:
    service = IdentityVerificationService()
    is_valid = await service.verify_identity_token(UNVERIFIED_IDENTITY_TOKEN_ZERO)
    assert is_valid is False


@pytest.mark.asyncio
async def test_identity_verification_reject_unverified_prefix() -> None:
    service = IdentityVerificationService()
    unverified_hash = UNVERIFIED_IDENTITY_PREFIX + "a" * (64 - len(UNVERIFIED_IDENTITY_PREFIX))
    is_valid = await service.verify_identity_token(unverified_hash)
    assert is_valid is False


@pytest.mark.asyncio
async def test_identity_verification_live_endpoint_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer mosip_token"
        return httpx.Response(200, json={"is_verified": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = IdentityVerificationService(
        endpoint_url="https://mosip.gov.in",
        api_key="mosip_token",
        http_client=client,
    )
    is_valid = await service.verify_identity_token("a" * 64)
    assert is_valid is True


@pytest.mark.asyncio
async def test_identity_verification_live_endpoint_error_fallback() -> None:
    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Registry Unavailable")

    client = httpx.AsyncClient(transport=httpx.MockTransport(error_handler))
    service = IdentityVerificationService(
        endpoint_url="https://mosip.gov.in",
        api_key="mosip_token",
        http_client=client,
    )
    # Falls back to mock
    is_valid = await service.verify_identity_token("a" * 64)
    assert is_valid is True


@pytest.mark.asyncio
async def test_identity_verification_ephemeral_client_error_fallback() -> None:
    service = IdentityVerificationService(
        endpoint_url="http://invalid.unreachable.endpoint.local:9999",
        api_key="mosip_token",
    )
    is_valid = await service.verify_identity_token("a" * 64)
    assert is_valid is True


@pytest.mark.asyncio
async def test_identity_verification_no_api_key_and_non_dict_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "Authorization" not in request.headers
        return httpx.Response(200, json="invalid string response")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = IdentityVerificationService(
        endpoint_url="https://mosip.gov.in",
        api_key=None,
        http_client=client,
    )
    is_valid = await service.verify_identity_token("a" * 64)
    assert is_valid is True
