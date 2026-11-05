"""Layer 3 AI Perception: Sovereign Bhashini Speech & Translation Service.

Provides stateless Automatic Speech Recognition (ASR), Neural Machine Translation (NMT),
and Text-to-Speech (TTS) model inference across 22 scheduled Indian languages.

Architectural Boundary (Layer 3 Bhashini Models vs. Layer 1 Telephony Edge):
- Bhashini (`BhashiniService` at Layer 3) provides the stateless foundational speech and
  translation model APIs (`ASR` audio-to-text, `NMT` text-to-text, `TTS` text-to-audio).
  It does not terminate SIP/PSTN telecom calls, manage Voice Activity Detection (VAD), or
  handle mid-call barge-in interruptions.
- Upstream telephony edge runtimes (such as COSS/EkStep's open-source VoicEra platform on
  8kHz PSTN/SIP paired with Layer 1 `IvrConnector`) answer feature-phone calls, manage
  real-time bidirectional audio streaming and VAD/barge-in at <₹1/min, and deliver signed
  8kHz/16kHz audio streams into `agristack-dbt-core`, which tokenizes PII in RAM (Layer 2),
  invokes `BhashiniService` (Layer 3), and enforces 3-Gate eligibility governance (Layer 4).

In production environments, LiveBhashiniService enforces live HTTPS communication with
strict fail-fast configuration and fail-closed error handling (no mock fallback).
In non-production, MockBhashiniService provides deterministic simulation for offline testing.

See: decisions/step2.0_canonical_domain_schemas.md (Section 3.2)
See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.1)
See: decisions/step3.7_live_service_integration.md
See: decisions/step3.6_speech_and_translation_evaluation.md
"""

import hashlib
import logging
from typing import Final, Protocol, Self

from httpx import AsyncClient

from src.config.service_settings import (
    get_bhashini_api_key,
    get_bhashini_endpoint,
    is_production,
)
from src.errors.service_errors import (
    ServiceRequestPayloadError,
    ServiceResponsePayloadError,
)
from src.services.ai.ai_mock_fixtures import (
    DEFAULT_NMT_FALLBACK_KEY,
    MOCK_ASR_TRANSCRIPTIONS,
    MOCK_NMT_TRANSLATIONS,
    MOCK_STREAM_EMPTY_KEYWORD,
    MOCK_STREAM_ERROR_KEYWORDS,
    MOCK_TTS_URL_TEMPLATE,
)
from src.services.http_transport import (
    ServiceHttpTransport,
    ServiceTransportConfig,
    get_shared_http_client,
)

logger = logging.getLogger(__name__)

__all__ = [
    "BhashiniService",
    "LiveBhashiniService",
    "MockBhashiniService",
    "create_bhashini_service",
]

_DEFAULT_AI_TIMEOUT_SECONDS: Final[float] = 2.0
_ASR_TRANSCRIBE_PATH: Final[str] = "/v1/asr/transcribe"
_NMT_TRANSLATE_PATH: Final[str] = "/v1/nmt/translate"
_TTS_SYNTHESIZE_PATH: Final[str] = "/v1/tts/synthesize"


class BhashiniService(Protocol):
    """Protocol interface for multi-lingual Indic speech and translation perception.

    Provides automated ASR transcription, NMT vernacular translation, and TTS audio synthesis.
    """

    async def transcribe_audio(self, audio_url: str, language_locale: str) -> str:
        """Transcribes raw voice stream into text."""
        ...

    async def translate_text(
        self, text: str, source_locale: str, target_locale: str = "en-IN"
    ) -> str:
        """Translates text content into standard English or vernacular locale."""
        ...

    async def synthesize_speech(self, text: str, language_locale: str) -> str:
        """Synthesizes response text into spoken audio stream URL."""
        ...


class LiveBhashiniService:
    """Production live client executing HTTPS calls to sovereign Bhashini gateways.

    Strictly requires endpoint URL, API key, and pooled HTTP client. Fails closed with
    ServiceUnavailableError on network errors, timeouts, or remote 5xx outages, raises
    ServiceRequestPayloadError on malformed audio streams or unprocessable payloads (400/415/422),
    and raises ServiceResponsePayloadError on schema contract violations (502).
    """

    def __init__(
        self,
        endpoint_url: str,
        api_key: str,
        http_client: AsyncClient,
        timeout_seconds: float = _DEFAULT_AI_TIMEOUT_SECONDS,
    ) -> None:
        """Initializes live Bhashini client with mandatory credentials and transport."""
        self._transport = ServiceHttpTransport(
            http_client=http_client,
            api_key=api_key,
            config=ServiceTransportConfig(
                service_name="bhashini",
                service_title="Bhashini",
                timeout_seconds=timeout_seconds,
            ),
            base_url=endpoint_url,
        )

    @classmethod
    def from_env(
        cls,
        endpoint_url: str | None = None,
        api_key: str | None = None,
        http_client: AsyncClient | None = None,
        timeout_seconds: float = _DEFAULT_AI_TIMEOUT_SECONDS,
    ) -> Self:
        """Factory constructor building live instance from environment settings or overrides."""
        return cls(
            endpoint_url=endpoint_url or get_bhashini_endpoint() or "",
            api_key=api_key or get_bhashini_api_key() or "",
            http_client=http_client or get_shared_http_client(),
            timeout_seconds=timeout_seconds,
        )

    # -------------------------------------------------------------------------
    # Primary Public Workflow Entrypoints
    # -------------------------------------------------------------------------

    async def transcribe_audio(self, audio_url: str, language_locale: str) -> str:
        """Transcribes raw voice stream into text via live Bhashini ASR endpoint.

        Args:
            audio_url: Valid HTTP/HTTPS audio recording URL pointer from IVR/WhatsApp edge.
            language_locale: BCP 47 language locale identifier (e.g., 'hi-IN', 'ta-IN').

        Returns:
            Transcribed text string in original spoken language.

        Raises:
            ServiceRequestPayloadError: If audio file is malformed or rejected (400/415/422).
            ServiceResponsePayloadError: If response from Bhashini violates schema contract.
            ServiceUnavailableError: If live Bhashini service fails, times out, or returns 5xx.
            ServiceAuthenticationError: If live Bhashini service returns 401/403.
        """
        url_hash = hashlib.sha256(audio_url.encode("utf-8")).hexdigest()[:16]
        logger.info("Live transcribing audio for url_hash=%s locale=%s", url_hash, language_locale)

        payload = {"audio_url": audio_url, "language_locale": language_locale}
        response_data = await self._transport.post_json(
            _ASR_TRANSCRIBE_PATH,
            payload=payload,
            context_label=f"audio_hash={url_hash}",
        )
        transcript = response_data.get("transcript")
        if isinstance(transcript, str):
            return transcript
        target_url = self._transport.resolve_url(_ASR_TRANSCRIBE_PATH)
        raise ServiceResponsePayloadError(
            f"Live Bhashini ASR response from {target_url} missing 'transcript' field.",
            service_name="bhashini",
        )

    async def translate_text(
        self, text: str, source_locale: str, target_locale: str = "en-IN"
    ) -> str:
        """Translates text content via live Bhashini NMT endpoint.

        Args:
            text: Source text string to translate.
            source_locale: Source language locale identifier.
            target_locale: Target language locale identifier (default: 'en-IN').

        Returns:
            Translated text string.

        Raises:
            ServiceRequestPayloadError: If translation payload is rejected as invalid (400/422).
            ServiceResponsePayloadError: If response from Bhashini violates schema contract.
            ServiceUnavailableError: If live Bhashini service fails, times out, or returns 5xx.
            ServiceAuthenticationError: If live Bhashini service returns 401/403.
        """
        logger.info("Live translating text from %s to %s", source_locale, target_locale)
        if not text.strip():
            return ""

        payload = {
            "text": text,
            "source_locale": source_locale,
            "target_locale": target_locale,
        }
        response_data = await self._transport.post_json(
            _NMT_TRANSLATE_PATH,
            payload=payload,
            context_label=f"{source_locale}->{target_locale}",
        )
        translated_text = response_data.get("translated_text")
        if isinstance(translated_text, str):
            return translated_text
        target_url = self._transport.resolve_url(_NMT_TRANSLATE_PATH)
        raise ServiceResponsePayloadError(
            f"Live Bhashini NMT response from {target_url} missing 'translated_text' field.",
            service_name="bhashini",
        )

    async def synthesize_speech(self, text: str, language_locale: str) -> str:
        """Synthesizes response text into spoken audio stream URL via live Bhashini TTS endpoint.

        Args:
            text: Text content to synthesize into speech.
            language_locale: Target speech language locale identifier.

        Returns:
            URL pointer to generated audio recording.

        Raises:
            ValueError: If response text is empty.
            ServiceRequestPayloadError: If synthesis payload is rejected as invalid (400/422).
            ServiceResponsePayloadError: If response from Bhashini violates schema contract.
            ServiceUnavailableError: If live Bhashini service fails, times out, or returns 5xx.
            ServiceAuthenticationError: If live Bhashini service returns 401/403.
        """
        logger.info(
            "Live synthesizing speech for locale=%s text_len=%d", language_locale, len(text)
        )
        if not text.strip():
            raise ValueError("Cannot synthesize empty response text into speech.")

        payload = {"text": text, "language_locale": language_locale}
        response_data = await self._transport.post_json(
            _TTS_SYNTHESIZE_PATH,
            payload=payload,
            context_label=f"locale={language_locale}",
        )
        audio_url = response_data.get("audio_url")
        if isinstance(audio_url, str):
            return audio_url
        target_url = self._transport.resolve_url(_TTS_SYNTHESIZE_PATH)
        raise ServiceResponsePayloadError(
            f"Live Bhashini TTS response from {target_url} missing 'audio_url' field.",
            service_name="bhashini",
        )


class MockBhashiniService:
    """Deterministic local simulation of Bhashini perception for offline testing."""

    async def transcribe_audio(self, audio_url: str, language_locale: str) -> str:
        """Simulates speech transcription with deterministic keywords."""
        url_lower = audio_url.lower()
        if MOCK_STREAM_EMPTY_KEYWORD in url_lower:
            return ""
        if any(error_keyword in url_lower for error_keyword in MOCK_STREAM_ERROR_KEYWORDS):
            raise ServiceRequestPayloadError(
                "ASR audio stream formatting or download error.",
                service_name="bhashini",
            )
        return MOCK_ASR_TRANSCRIPTIONS.get(language_locale, MOCK_ASR_TRANSCRIPTIONS["default"])

    async def translate_text(
        self, text: str, source_locale: str, target_locale: str = "en-IN"
    ) -> str:
        """Simulates regional translation with deterministic dictionary mapping."""
        if not text.strip():
            return ""
        if source_locale == target_locale:
            return text
        if source_locale.startswith("hi") and target_locale.startswith("en"):
            for keyword, translation in MOCK_NMT_TRANSLATIONS.items():
                if keyword in text.lower():
                    return translation
            return MOCK_NMT_TRANSLATIONS[DEFAULT_NMT_FALLBACK_KEY]
        return f"[Translated to {target_locale}] {text}"

    async def synthesize_speech(self, text: str, language_locale: str) -> str:
        """Simulates speech synthesis with deterministic audio URL template."""
        if not text.strip():
            raise ValueError("Cannot synthesize empty response text into speech.")
        clean_locale = language_locale.replace("-", "_").lower()
        return MOCK_TTS_URL_TEMPLATE.format(locale=clean_locale)


def create_bhashini_service(
    endpoint_url: str | None = None,
    api_key: str | None = None,
    http_client: AsyncClient | None = None,
    timeout_seconds: float = _DEFAULT_AI_TIMEOUT_SECONDS,
    require_live: bool | None = None,
) -> BhashiniService:
    """Factory creating appropriate Bhashini service implementation based on environment.

    Resolution follows a 3-tier precedence model:
    1.  Mandatory Production: If require_live=True (or ENVIRONMENT='production' is set),
       constructs LiveBhashiniService via environment settings, failing fast if credentials
       are missing.
    2. Explicit Parameters: If endpoint_url and api_key are provided directly as arguments,
       constructs LiveBhashiniService targeting those coordinates (useful for local WireMock,
       stub proxies, or partial sandbox integration without enforcing production invariants).
    3. Offline Simulation: If require_live is False and explicit credentials are not passed
       (even if present in environment variables), returns MockBhashiniService to guarantee
       offline test isolation for local development and CI pipelines.
    """
    must_be_live = is_production() if require_live is None else require_live
    if must_be_live:
        return LiveBhashiniService.from_env(
            endpoint_url=endpoint_url,
            api_key=api_key,
            http_client=http_client,
            timeout_seconds=timeout_seconds,
        )

    if endpoint_url and api_key:
        return LiveBhashiniService(
            endpoint_url=endpoint_url,
            api_key=api_key,
            http_client=http_client or get_shared_http_client(),
            timeout_seconds=timeout_seconds,
        )

    return MockBhashiniService()
