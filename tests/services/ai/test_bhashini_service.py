import httpx
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


@pytest.mark.asyncio
async def test_bhashini_service_live_endpoints_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        url_str = str(request.url)
        assert request.headers.get("Authorization") == "Bearer test_secret_key"
        if "/v1/asr/transcribe" in url_str:
            return httpx.Response(200, json={"transcript": "Live transcribed Hindi speech"})
        if "/v1/nmt/translate" in url_str:
            return httpx.Response(200, json={"translated_text": "Live translated English text"})
        if "/v1/tts/synthesize" in url_str:
            return httpx.Response(
                200, json={"audio_url": "https://cdn.bhashini.gov.in/live_audio.wav"}
            )
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = BhashiniService(
        endpoint_url="https://api.bhashini.gov.in",
        api_key="test_secret_key",
        http_client=client,
    )

    transcript = await service.transcribe_audio("https://carrier.in/audio.wav", "hi-IN")
    assert transcript == "Live transcribed Hindi speech"

    translation = await service.translate_text("Namaste", "hi-IN", "en-IN")
    assert translation == "Live translated English text"

    tts_url = await service.synthesize_speech("Disbursement approved", "hi-IN")
    assert tts_url == "https://cdn.bhashini.gov.in/live_audio.wav"


@pytest.mark.asyncio
async def test_bhashini_service_live_endpoints_error_fallback() -> None:
    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal Server Error")

    client = httpx.AsyncClient(transport=httpx.MockTransport(error_handler))
    service = BhashiniService(
        endpoint_url="https://api.bhashini.gov.in",
        api_key="test_secret_key",
        http_client=client,
    )

    # Falls back to mock
    transcript = await service.transcribe_audio("https://carrier.in/audio.wav", "hi-IN")
    assert len(transcript) > 0

    translation = await service.translate_text("Mera khet kharab ho gaya", "hi-IN", "en-IN")
    assert len(translation) > 0

    tts_url = await service.synthesize_speech("Aapka aavedan swikar hua", "hi-IN")
    assert tts_url.startswith("https://")


@pytest.mark.asyncio
async def test_bhashini_service_ephemeral_client_success() -> None:
    # Test path when http_client is None but endpoint_url is configured with an invalid/mock server
    service = BhashiniService(
        endpoint_url="http://invalid.unreachable.endpoint.local:9999",
        api_key="test_secret_key",
    )
    # Falls back smoothly when network fails
    transcript = await service.transcribe_audio("https://carrier.in/audio.wav", "hi-IN")
    assert len(transcript) > 0


@pytest.mark.asyncio
async def test_bhashini_service_no_api_key_and_non_dict_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert "Authorization" not in request.headers
        return httpx.Response(200, json=["unexpected_list_not_dict"])

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    service = BhashiniService(
        endpoint_url="https://api.bhashini.gov.in",
        api_key=None,
        http_client=client,
    )
    transcript = await service.transcribe_audio("https://carrier.in/audio.wav", "hi-IN")
    assert len(transcript) > 0
