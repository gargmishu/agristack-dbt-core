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
from typing import Any, Final, Protocol, Self

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

_DEFAULT_AI_TIMEOUT_SECONDS: Final[float] = 10.0
_ULCA_PIPELINE_PATH: Final[str] = "/services/inference/pipeline"
_DEFAULT_ASR_SERVICE_ID: Final[str] = "bhashini/bharatgen/asr"
_DEFAULT_NMT_SERVICE_ID: Final[str] = "bhashini/cdac-noida/nmt"
_DEFAULT_TTS_SERVICE_ID: Final[str] = "bhashini/bodhan/indic-tts"
_DEFAULT_AUDIO_FORMAT: Final[str] = "wav"
_DEFAULT_SAMPLING_RATE_HZ: Final[int] = 8000
_DEFAULT_TTS_GENDER: Final[str] = "female"
_DATA_URI_PREFIX: Final[str] = "data:"
_DATA_URI_WAV_PREFIX: Final[str] = "data:audio/wav;base64,"


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
    """Production live client executing HTTPS calls to sovereign Bhashini ULCA gateways.

    Dispatches standard ULCA inference pipeline tasks (`asr`, `translation`, `tts`) to
    `/services/inference/pipeline`. Strictly requires endpoint URL, inference API key,
    and pooled HTTP client. Fails closed with ServiceUnavailableError on network errors,
    timeouts, or remote 5xx outages, raises ServiceRequestPayloadError on malformed audio
    streams or unprocessable payloads (400/415/422), and raises ServiceResponsePayloadError
    on schema contract violations (502).
    """

    def __init__(
        self,
        endpoint_url: str,
        api_key: str,
        http_client: AsyncClient,
        timeout_seconds: float = _DEFAULT_AI_TIMEOUT_SECONDS,
    ) -> None:
        """Initializes live Bhashini client with mandatory credentials and transport."""
        normalized_base_url = self._normalize_base_endpoint(endpoint_url)
        self._transport = ServiceHttpTransport(
            http_client=http_client,
            api_key=api_key,
            config=ServiceTransportConfig(
                service_name="bhashini",
                service_title="Bhashini",
                timeout_seconds=timeout_seconds,
                auth_scheme="",
            ),
            base_url=normalized_base_url,
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
        """Transcribes raw voice stream into text via live Bhashini ASR pipeline endpoint.

        Args:
            audio_url: Valid HTTP/HTTPS audio recording URL or base64 data URI from edge.
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
        source_language = self._extract_language_code(language_locale)
        logger.info("Live transcribing audio for url_hash=%s locale=%s", url_hash, language_locale)

        payload: dict[str, Any] = {
            "pipelineTasks": [
                {
                    "taskType": "asr",
                    "config": {
                        "language": {"sourceLanguage": source_language},
                        "serviceId": _DEFAULT_ASR_SERVICE_ID,
                        "audioFormat": _DEFAULT_AUDIO_FORMAT,
                        "samplingRate": _DEFAULT_SAMPLING_RATE_HZ,
                    },
                }
            ],
            "inputData": {"audio": [self._build_audio_input(audio_url)]},
        }
        response_data = await self._transport.post_json(
            _ULCA_PIPELINE_PATH,
            payload=payload,
            context_label=f"audio_hash={url_hash}",
        )
        transcript = self._extract_pipeline_text_field(response_data, field_name="source")
        if transcript is not None:
            return transcript
        target_url = self._transport.resolve_url(_ULCA_PIPELINE_PATH)
        raise ServiceResponsePayloadError(
            f"Live Bhashini ASR response from {target_url} missing 'transcript' field.",
            service_name="bhashini",
        )

    async def translate_text(
        self, text: str, source_locale: str, target_locale: str = "en-IN"
    ) -> str:
        """Translates text content via live Bhashini NMT pipeline endpoint.

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

        source_language = self._extract_language_code(source_locale)
        target_language = self._extract_language_code(target_locale)
        if source_language == target_language:
            return text

        payload: dict[str, Any] = {
            "pipelineTasks": [
                {
                    "taskType": "translation",
                    "config": {
                        "language": {
                            "sourceLanguage": source_language,
                            "targetLanguage": target_language,
                        },
                        "serviceId": _DEFAULT_NMT_SERVICE_ID,
                    },
                }
            ],
            "inputData": {"input": [{"source": text}]},
        }
        response_data = await self._transport.post_json(
            _ULCA_PIPELINE_PATH,
            payload=payload,
            context_label=f"{source_locale}->{target_locale}",
        )
        translated_text = self._extract_pipeline_text_field(response_data, field_name="target")
        if translated_text is not None:
            return translated_text
        target_url = self._transport.resolve_url(_ULCA_PIPELINE_PATH)
        raise ServiceResponsePayloadError(
            f"Live Bhashini NMT response from {target_url} missing 'translated_text' field.",
            service_name="bhashini",
        )

    async def synthesize_speech(self, text: str, language_locale: str) -> str:
        """Synthesizes response text into spoken audio URI via live Bhashini TTS pipeline endpoint.

        Args:
            text: Text content to synthesize into speech.
            language_locale: Target speech language locale identifier.

        Returns:
            Audio URI or `data:audio/wav;base64,...` payload of generated speech recording.

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

        source_language = self._extract_language_code(language_locale)
        payload: dict[str, Any] = {
            "pipelineTasks": [
                {
                    "taskType": "tts",
                    "config": {
                        "language": {"sourceLanguage": source_language},
                        "serviceId": _DEFAULT_TTS_SERVICE_ID,
                        "gender": _DEFAULT_TTS_GENDER,
                        "samplingRate": _DEFAULT_SAMPLING_RATE_HZ,
                    },
                }
            ],
            "inputData": {"input": [{"source": text}]},
        }
        response_data = await self._transport.post_json(
            _ULCA_PIPELINE_PATH,
            payload=payload,
            context_label=f"locale={language_locale}",
        )
        audio_uri = self._extract_pipeline_audio_uri(response_data)
        if audio_uri is not None:
            return audio_uri
        target_url = self._transport.resolve_url(_ULCA_PIPELINE_PATH)
        raise ServiceResponsePayloadError(
            f"Live Bhashini TTS response from {target_url} missing 'audio_url' field.",
            service_name="bhashini",
        )

    # -------------------------------------------------------------------------
    # Private Helpers (Strictly at Bottom)
    # -------------------------------------------------------------------------

    @staticmethod
    def _normalize_base_endpoint(endpoint_url: str) -> str:
        """Strips trailing ULCA pipeline path if caller supplied full callback URL."""
        cleaned = endpoint_url.strip().rstrip("/")
        if cleaned.endswith(_ULCA_PIPELINE_PATH):
            return cleaned[: -len(_ULCA_PIPELINE_PATH)]
        return cleaned

    @staticmethod
    def _extract_language_code(language_locale: str) -> str:
        """Normalizes BCP 47 locale (e.g. 'hi-IN') into ULCA ISO-639-1 language code ('hi')."""
        return language_locale.strip().split("-", maxsplit=1)[0].split("_", maxsplit=1)[0].lower()

    @staticmethod
    def _build_audio_input(audio_url: str) -> dict[str, str]:
        """Constructs ULCA audio input object from a data URI or remote HTTP/HTTPS URL."""
        stripped_url = audio_url.strip()
        if stripped_url.startswith(_DATA_URI_PREFIX) and "," in stripped_url:
            base64_content = stripped_url.split(",", maxsplit=1)[1]
            return {"audioContent": base64_content}
        return {"audioUri": stripped_url}

    @staticmethod
    def _extract_first_task_response(response_data: dict[str, Any]) -> dict[str, Any] | None:
        """Extracts the first task dictionary from ULCA pipelineResponse list."""
        pipeline_response = response_data.get("pipelineResponse")
        if not isinstance(pipeline_response, list) or not pipeline_response:
            return None
        first_task = pipeline_response[0]
        return first_task if isinstance(first_task, dict) else None

    @classmethod
    def _extract_pipeline_text_field(
        cls, response_data: dict[str, Any], field_name: str
    ) -> str | None:
        """Extracts string field ('source' for ASR or 'target' for NMT) from pipeline output."""
        first_task = cls._extract_first_task_response(response_data)
        if first_task is None:
            return None
        output_items = first_task.get("output")
        if not isinstance(output_items, list) or not output_items:
            return None
        first_output = output_items[0]
        if not isinstance(first_output, dict):
            return None
        field_value = first_output.get(field_name)
        return field_value if isinstance(field_value, str) else None

    @classmethod
    def _extract_pipeline_audio_uri(cls, response_data: dict[str, Any]) -> str | None:
        """Extracts audio URI or formats base64 audioContent from TTS pipeline output."""
        first_task = cls._extract_first_task_response(response_data)
        if first_task is None:
            return None
        audio_items = first_task.get("audio")
        if not isinstance(audio_items, list) or not audio_items:
            return None
        first_audio = audio_items[0]
        if not isinstance(first_audio, dict):
            return None
        audio_uri = first_audio.get("audioUri")
        if isinstance(audio_uri, str) and audio_uri.strip():
            return audio_uri.strip()
        audio_content = first_audio.get("audioContent")
        if isinstance(audio_content, str) and audio_content.strip():
            return f"{_DATA_URI_WAV_PREFIX}{audio_content.strip()}"
        return None


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
