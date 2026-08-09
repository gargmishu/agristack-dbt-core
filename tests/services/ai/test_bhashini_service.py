import pytest

from src.services.ai import BhashiniService


@pytest.mark.asyncio
async def test_bhashini_service_transcribe() -> None:
    service = BhashiniService()
    transcription = await service.transcribe_audio(
        "https://sip-gateway.telecom.in/audio/sample.wav", "hi-IN"
    )
    assert isinstance(transcription, str)
    assert len(transcription) > 0


@pytest.mark.asyncio
async def test_bhashini_service_transcribe_empty_stream() -> None:
    service = BhashiniService()
    transcription = await service.transcribe_audio(
        "https://sip-gateway.telecom.in/audio/empty_recording.wav", "hi-IN"
    )
    assert transcription == ""


@pytest.mark.asyncio
async def test_bhashini_service_transcribe_error_stream() -> None:
    service = BhashiniService()
    with pytest.raises(ValueError, match="ASR audio stream"):
        await service.transcribe_audio(
            "https://sip-gateway.telecom.in/audio/invalid_stream.wav", "hi-IN"
        )


@pytest.mark.asyncio
async def test_bhashini_service_translate() -> None:
    service = BhashiniService()
    translation = await service.translate_text("Mera khet kharab ho gaya hai", "hi-IN", "en-IN")
    assert isinstance(translation, str)
    assert len(translation) > 0


@pytest.mark.asyncio
async def test_bhashini_service_translate_fallback_and_other_locales() -> None:
    service = BhashiniService()
    fallback = await service.translate_text("Anjaan vakya bina keyword ke", "hi-IN", "en-IN")
    assert "PM KISAN installment" in fallback

    other_locale = await service.translate_text("Vanakkam", "ta-IN", "hi-IN")
    assert other_locale == "[Translated to hi-IN] Vanakkam"


@pytest.mark.asyncio
async def test_bhashini_service_translate_same_locale() -> None:
    service = BhashiniService()
    text = "Already English text"
    translation = await service.translate_text(text, "en-IN", "en-IN")
    assert translation == text


@pytest.mark.asyncio
async def test_bhashini_service_translate_empty_text() -> None:
    service = BhashiniService()
    translation = await service.translate_text("   ", "hi-IN", "en-IN")
    assert translation == ""


@pytest.mark.asyncio
async def test_bhashini_service_synthesize() -> None:
    service = BhashiniService()
    audio_url = await service.synthesize_speech("Aapka aavedan swikar kar liya gaya hai", "hi-IN")
    assert isinstance(audio_url, str)
    assert audio_url.startswith("https://")


@pytest.mark.asyncio
async def test_bhashini_service_synthesize_empty_text_raises() -> None:
    service = BhashiniService()
    with pytest.raises(ValueError, match="Cannot synthesize empty response text"):
        await service.synthesize_speech("   ", "hi-IN")
