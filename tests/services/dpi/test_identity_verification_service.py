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
