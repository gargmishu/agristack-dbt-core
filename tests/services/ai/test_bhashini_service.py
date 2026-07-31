import pytest

from src.services.ai import BhashiniService


@pytest.mark.asyncio
async def test_bhashini_service_transcribe() -> None:
    service = BhashiniService()
    transcription = await service.transcribe_audio(
        "https://sip-gateway.telecom.in/audio/sample.wav", "hi-IN"
    )
    assert isinstance(transcription, str)


@pytest.mark.asyncio
async def test_bhashini_service_translate() -> None:
    service = BhashiniService()
    translation = await service.translate_text("Mera khet kharab ho gaya hai", "hi-IN", "en-IN")
    assert isinstance(translation, str)


@pytest.mark.asyncio
async def test_bhashini_service_synthesize() -> None:
    service = BhashiniService()
    audio_url = await service.synthesize_speech("Aapka aavedan swikar kar liya gaya hai", "hi-IN")
    assert isinstance(audio_url, str)
