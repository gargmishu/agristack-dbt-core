import pytest

from src.services.dpi import IdentityRegistryService


@pytest.mark.asyncio
async def test_identity_registry_verify_token() -> None:
    service = IdentityRegistryService()
    citizen_hash = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"
    is_valid = await service.verify_identity_token(citizen_hash)
    assert is_valid is True
