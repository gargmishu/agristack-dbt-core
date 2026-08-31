import httpx
import pytest

from src.errors.service_errors import (
    ServiceAuthenticationError,
    ServiceConfigurationError,
    ServiceRequestPayloadError,
    ServiceResponsePayloadError,
    ServiceUnavailableError,
)
from src.services.ai import (
    LiveBhashiniService,
    MockBhashiniService,
    create_bhashini_service,
)


@pytest.mark.asyncio
async def test_mock_bhashini_service_transcribe() -> None:
    service = MockBhashiniService()
    transcription = await service.transcribe_audio(
        "https://sip-gateway.telecom.in/audio/sample.wav", "hi-IN"
    )
    assert isinstance(transcription, str)
    assert len(transcription) > 0


@pytest.mark.asyncio
async def test_mock_bhashini_service_transcribe_empty_stream() -> None:
    service = MockBhashiniService()
    transcription = await service.transcribe_audio(
        "https://sip-gateway.telecom.in/audio/empty_recording.wav", "hi-IN"
    )
    assert transcription == ""


@pytest.mark.asyncio
async def test_mock_bhashini_service_transcribe_error_stream() -> None:
    service = MockBhashiniService()
    with pytest.raises(
        ServiceRequestPayloadError, match="ASR audio stream formatting or download error"
    ):
        await service.transcribe_audio(
            "https://sip-gateway.telecom.in/audio/invalid_stream.wav", "hi-IN"
        )


@pytest.mark.asyncio
async def test_mock_bhashini_service_translate() -> None:
    service = MockBhashiniService()
    translation = await service.translate_text("Mera khet kharab ho gaya hai", "hi-IN", "en-IN")
    assert isinstance(translation, str)
    assert len(translation) > 0


@pytest.mark.asyncio
async def test_mock_bhashini_service_translate_fallback_and_other_locales() -> None:
    service = MockBhashiniService()
    fallback = await service.translate_text("Anjaan vakya bina keyword ke", "hi-IN", "en-IN")
    assert "PM KISAN installment" in fallback

    other_locale = await service.translate_text("Vanakkam", "ta-IN", "hi-IN")
    assert other_locale == "[Translated to hi-IN] Vanakkam"


@pytest.mark.asyncio
async def test_mock_bhashini_service_translate_same_locale() -> None:
    service = MockBhashiniService()
    text = "Already English text"
    translation = await service.translate_text(text, "en-IN", "en-IN")
    assert translation == text


@pytest.mark.asyncio
async def test_mock_bhashini_service_translate_empty_text() -> None:
    service = MockBhashiniService()
    translation = await service.translate_text("   ", "hi-IN", "en-IN")
    assert translation == ""


@pytest.mark.asyncio
async def test_mock_bhashini_service_synthesize() -> None:
    service = MockBhashiniService()
    audio_url = await service.synthesize_speech("Aapka aavedan swikar kar liya gaya hai", "hi-IN")
    assert isinstance(audio_url, str)
    assert audio_url.startswith("https://")


@pytest.mark.asyncio
async def test_mock_bhashini_service_synthesize_empty_text_raises() -> None:
    service = MockBhashiniService()
    with pytest.raises(ValueError, match="Cannot synthesize empty response text"):
        await service.synthesize_speech("   ", "hi-IN")


@pytest.mark.asyncio
async def test_live_bhashini_service_endpoints_success() -> None:
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
    service = LiveBhashiniService(
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
async def test_live_bhashini_service_empty_text_short_circuits() -> None:
    client = httpx.AsyncClient()
    service = LiveBhashiniService(
        endpoint_url="https://api.bhashini.gov.in",
        api_key="test_secret_key",
        http_client=client,
    )
    assert await service.translate_text("   ", "hi-IN", "en-IN") == ""
    with pytest.raises(ValueError, match="Cannot synthesize empty response text"):
        await service.synthesize_speech("   ", "hi-IN")


@pytest.mark.asyncio
async def test_live_bhashini_service_constructor_validation() -> None:
    client = httpx.AsyncClient()
    with pytest.raises(ServiceConfigurationError, match="endpoint URL is required"):
        LiveBhashiniService(endpoint_url="", api_key="valid_key", http_client=client)

    with pytest.raises(ServiceConfigurationError, match="API key is required"):
        LiveBhashiniService(
            endpoint_url="https://api.bhashini.gov.in", api_key="", http_client=client
        )


@pytest.mark.asyncio
async def test_live_bhashini_service_fail_closed_on_500() -> None:
    def error_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Bhashini Cluster Outage")

    client = httpx.AsyncClient(transport=httpx.MockTransport(error_handler))
    service = LiveBhashiniService(
        endpoint_url="https://api.bhashini.gov.in",
        api_key="valid_key",
        http_client=client,
    )
    with pytest.raises(ServiceUnavailableError, match="status=500"):
        await service.transcribe_audio("https://carrier.in/audio.wav", "hi-IN")

    with pytest.raises(ServiceUnavailableError, match="status=500"):
        await service.translate_text("Mera khet kharab ho gaya", "hi-IN", "en-IN")

    with pytest.raises(ServiceUnavailableError, match="status=500"):
        await service.synthesize_speech("Aapka aavedan swikar hua", "hi-IN")


@pytest.mark.asyncio
async def test_live_bhashini_service_fail_closed_on_auth_failure() -> None:
    def auth_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="Unauthorized")

    client = httpx.AsyncClient(transport=httpx.MockTransport(auth_handler))
    service = LiveBhashiniService(
        endpoint_url="https://api.bhashini.gov.in",
        api_key="invalid_key",
        http_client=client,
    )
    with pytest.raises(ServiceAuthenticationError, match="Bhashini authentication failed"):
        await service.translate_text("Mera khet kharab ho gaya", "hi-IN", "en-IN")


@pytest.mark.asyncio
async def test_live_bhashini_service_malformed_payload_error() -> None:
    def bad_request_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, text="Unsupported audio encoding: expected 8kHz/16kHz PCM WAV")

    client = httpx.AsyncClient(transport=httpx.MockTransport(bad_request_handler))
    service = LiveBhashiniService(
        endpoint_url="https://api.bhashini.gov.in",
        api_key="valid_key",
        http_client=client,
    )
    with pytest.raises(ServiceRequestPayloadError, match="Unsupported audio encoding"):
        await service.transcribe_audio("https://carrier.in/corrupted.wav", "hi-IN")


@pytest.mark.asyncio
async def test_live_bhashini_service_response_payload_contract_violation() -> None:
    def missing_field_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected_status": "ok"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(missing_field_handler))
    service = LiveBhashiniService(
        endpoint_url="https://api.bhashini.gov.in",
        api_key="valid_key",
        http_client=client,
    )
    with pytest.raises(ServiceResponsePayloadError, match="missing 'transcript' field"):
        await service.transcribe_audio("https://carrier.in/valid.wav", "hi-IN")


@pytest.mark.asyncio
async def test_create_bhashini_service_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    # Non-production without credentials returns MockBhashiniService
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("BHASHINI_API_ENDPOINT", raising=False)
    monkeypatch.delenv("BHASHINI_API_KEY", raising=False)

    service = create_bhashini_service()
    assert isinstance(service, MockBhashiniService)

    # Production without credentials raises ServiceConfigurationError
    monkeypatch.setenv("ENVIRONMENT", "production")
    with pytest.raises(ServiceConfigurationError, match="BHASHINI_API_ENDPOINT"):
        create_bhashini_service()

    # Production with credentials returns LiveBhashiniService
    monkeypatch.setenv("BHASHINI_API_ENDPOINT", "https://api.bhashini.gov.in")
    monkeypatch.setenv("BHASHINI_API_KEY", "prod_token")
    live_service = create_bhashini_service()
    assert isinstance(live_service, LiveBhashiniService)
