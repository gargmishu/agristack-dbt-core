"""Unit tests for SocialRegistryService (OpenSPP external DPI connector)."""

import pytest

from src.services.dpi import SocialRegistryService
from src.services.dpi.dpi_mock_fixtures import UNVERIFIED_IDENTITY_PREFIX


@pytest.mark.asyncio
async def test_social_registry_query_beneficiary_eligibility() -> None:
    service = SocialRegistryService()
    valid_hmac = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"
    zero_hmac = "0000000000000000000000000000000000000000000000000000000000000000"
    unverified_hmac = UNVERIFIED_IDENTITY_PREFIX + "a" * (64 - len(UNVERIFIED_IDENTITY_PREFIX))

    assert await service.query_beneficiary_eligibility(valid_hmac, "PM_KISAN") is True
    assert await service.query_beneficiary_eligibility(zero_hmac, "PM_KISAN") is False
    assert await service.query_beneficiary_eligibility(unverified_hmac, "PM_KISAN") is False
    assert await service.query_beneficiary_eligibility(valid_hmac, "   ") is False
