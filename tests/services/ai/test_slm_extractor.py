import pytest

from src.services.ai import SlmExtractor


@pytest.mark.asyncio
async def test_slm_extractor_extract_entities() -> None:
    extractor = SlmExtractor()
    result = await extractor.extract_entities("sess_12345678", "Mera khet Karnal me hai", "hi-IN")
    assert result is None
