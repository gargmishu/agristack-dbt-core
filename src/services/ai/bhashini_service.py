"""Sovereign AI Perception: Bhashini Indic Speech & Translation Service.

Performs Automatic Speech Recognition (ASR), Neural Machine Translation (NMT), and
Text-to-Speech (TTS) synthesis across scheduled Indian languages.

Why integrate Bhashini for agricultural citizen intake?
Agrarian communities across India communicate across dozens of languages and hundreds of
local dialects. Layer 3 perception uses Bhashini to normalize spoken/textual vernacular input
into structured domain contracts while maintaining Zero-PII boundaries.

In production environments, enforces live HTTPS communication with strict fail-fast configuration
and fail-closed error handling (no mock fallback). In non-production, supports deterministic
mock simulation for offline testing.

See: decisions/step2.0_canonical_domain_schemas.md (Section 3.2)
See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.1)
See: decisions/step3.6_live_service_integration.md
See: roadmap.md (Phase 3 Step 3.1 Service Abstractions)
"""

import hashlib
import logging
from typing import Any, Final

import httpx

from src.config.service_settings import (
    get_bhashini_api_key,
    get_bhashini_endpoint,
    is_production,
)
from src.errors.service_errors import (
    ServiceAuthenticationError,
    ServiceConfigurationError,
    ServiceUnavailableError,
)
from src.services.ai.ai_mock_fixtures import (
    DEFAULT_NMT_FALLBACK_KEY,
    MOCK_ASR_TRANSCRIPTIONS,
    MOCK_NMT_TRANSLATIONS,
    MOCK_STREAM_EMPTY_KEYWORD,
    MOCK_STREAM_ERROR_KEYWORDS,
    MOCK_TTS_URL_TEMPLATE,
)
from src.services.http_client_pool import get_shared_http_client

logger = logging.getLogger(__name__)

_DEFAULT_AI_TIMEOUT_SECONDS: Final[float] = 2.0
_HTTP_STATUS_OK: Final[int] = 200
_HTTP_STATUS_UNAUTHORIZED: Final[int] = 401
_HTTP_STATUS_FORBIDDEN: Final[int] = 403


class BhashiniService:
    """Service client for multi-lingual Indic speech and translation perception.

    Provides automated ASR transcription, NMT vernacular translation, and TTS audio synthesis.

    In production, mandates live endpoint configuration and pooled persistent HTTP transport.
    In development/testing, supports offline mock simulations.

    See: decisions/step2.0_canonical_domain_schemas.md (Section 3.2)
    See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.1)
    See: decisions/step3.6_live_service_integration.md
    """

    def __init__(
        self,
        endpoint_url: str | None = None,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        timeout_seconds: float = _DEFAULT_AI_TIMEOUT_SECONDS,
        require_live: bool | None = None,
    ) -> None:
        """Initializes Bhashini service client.

        Args:
            endpoint_url: Base HTTP URL for live Bhashini API service.
            api_key: Authorization Bearer token or API key for live calls.
            http_client: Async HTTP client for connection pooling.
            timeout_seconds: Request timeout in seconds (default: 2.0s).
            require_live: Whether live endpoints are required (defaults to is_production()).

        Raises:
            ServiceConfigurationError: In production mode if endpoint_url or api_key is missing.
        """
        self._require_live = is_production() if require_live is None else require_live
        self._http_client: httpx.AsyncClient | None

        if self._require_live:
            if not endpoint_url or not endpoint_url.strip():
                raise ServiceConfigurationError(
                    "Live Bhashini API endpoint URL is required in production mode."
                )
            if not api_key or not api_key.strip():
                raise ServiceConfigurationError(
                    "Live Bhashini API key is required in production mode."
                )
            self._http_client = http_client or get_shared_http_client()
        else:
            self._http_client = http_client

        self._endpoint_url = (
            endpoint_url.rstrip("/") if endpoint_url and endpoint_url.strip() else None
        )
        self._api_key = api_key.strip() if api_key and api_key.strip() else None
        self._timeout_seconds = timeout_seconds

    @classmethod
    def from_env(
        cls,
        http_client: httpx.AsyncClient | None = None,
        require_live: bool | None = None,
    ) -> "BhashiniService":
        """Factory constructor building instance from validated environment settings."""
        return cls(
            endpoint_url=get_bhashini_endpoint(),
            api_key=get_bhashini_api_key(),
            http_client=http_client,
            require_live=require_live,
        )

    # -------------------------------------------------------------------------
    # Primary Public Workflow Entrypoints
    # -------------------------------------------------------------------------

    async def transcribe_audio(self, audio_url: str, language_locale: str) -> str:
        """Transcribes raw voice stream into text in the specified language locale.

        Args:
            audio_url: Valid HTTP/HTTPS audio recording URL pointer from IVR/WhatsApp edge.
            language_locale: BCP 47 language locale identifier (e.g., 'hi-IN', 'ta-IN').

        Returns:
            Transcribed text string in original spoken language.

        Raises:
            ServiceUnavailableError: In live/production mode if external service fails or times out.
            ServiceAuthenticationError: In live/production mode if external service returns 401/403.
            ServiceConfigurationError: In live/production mode if live endpoint is not configured.
        """
        url_hash = hashlib.sha256(audio_url.encode("utf-8")).hexdigest()[:16]
        logger.info("Transcribing audio for url_hash=%s locale=%s", url_hash, language_locale)

        if self._endpoint_url:
            live_result = await self._call_live_asr(audio_url, language_locale)
            if live_result is not None:
                return live_result
            if self._require_live:
                raise ServiceUnavailableError(
                    f"Live Bhashini ASR transcription failed for audio URL hash '{url_hash}'."
                )

        if self._require_live:
            raise ServiceConfigurationError(
                "Bhashini ASR cannot execute: live endpoint is required in production."
            )

        return self._mock_transcribe_audio(audio_url, language_locale)

    async def translate_text(
        self, text: str, source_locale: str, target_locale: str = "en-IN"
    ) -> str:
        """Translates text content from source regional locale to target processing locale.

        Args:
            text: Source text string to translate.
            source_locale: Source language locale identifier.
            target_locale: Target language locale identifier (default: 'en-IN').

        Returns:
            Translated text string.

        Raises:
            ServiceUnavailableError: In live/production mode if external service fails or times out.
            ServiceAuthenticationError: In live/production mode if external service returns 401/403.
            ServiceConfigurationError: In live/production mode if live endpoint is not configured.
        """
        logger.info("Translating text from %s to %s", source_locale, target_locale)
        if not text.strip():
            return ""

        if self._endpoint_url:
            live_result = await self._call_live_nmt(text, source_locale, target_locale)
            if live_result is not None:
                return live_result
            if self._require_live:
                raise ServiceUnavailableError(
                    f"Live Bhashini NMT translation failed from {source_locale} to {target_locale}."
                )

        if self._require_live:
            raise ServiceConfigurationError(
                "Bhashini NMT cannot execute: live endpoint is required in production."
            )

        return self._mock_translate_text(text, source_locale, target_locale)

    async def synthesize_speech(self, text: str, language_locale: str) -> str:
        """Synthesizes response text into spoken audio stream URL for voice/audio channels.

        Args:
            text: Text content to synthesize into speech.
            language_locale: Target speech language locale identifier.

        Returns:
            URL pointer to generated audio recording.

        Raises:
            ServiceUnavailableError: In live/production mode if external service fails or times out.
            ServiceAuthenticationError: In live/production mode if external service returns 401/403.
            ServiceConfigurationError: In live/production mode if live endpoint is not configured.
        """
        logger.info("Synthesizing speech for locale=%s text_len=%d", language_locale, len(text))
        if not text.strip():
            raise ValueError("Cannot synthesize empty response text into speech.")

        if self._endpoint_url:
            live_result = await self._call_live_tts(text, language_locale)
            if live_result is not None:
                return live_result
            if self._require_live:
                raise ServiceUnavailableError(
                    f"Live Bhashini TTS synthesis failed for locale '{language_locale}'."
                )

        if self._require_live:
            raise ServiceConfigurationError(
                "Bhashini TTS cannot execute: live endpoint is required in production."
            )

        return self._mock_synthesize_speech(text, language_locale)

    # -------------------------------------------------------------------------
    # Private Helpers (Live HTTP & Local Mock Handlers)
    # -------------------------------------------------------------------------

    async def _call_live_asr(self, audio_url: str, language_locale: str) -> str | None:
        """Dispatches live ASR transcription HTTP request."""
        target_url = f"{self._endpoint_url}/v1/asr/transcribe"
        payload = {"audio_url": audio_url, "language_locale": language_locale}
        response_data = await self._post_json(target_url, payload)
        if response_data and isinstance(response_data.get("transcript"), str):
            return str(response_data["transcript"])
        return None

    async def _call_live_nmt(self, text: str, source_locale: str, target_locale: str) -> str | None:
        """Dispatches live NMT translation HTTP request."""
        target_url = f"{self._endpoint_url}/v1/nmt/translate"
        payload = {
            "text": text,
            "source_locale": source_locale,
            "target_locale": target_locale,
        }
        response_data = await self._post_json(target_url, payload)
        if response_data and isinstance(response_data.get("translated_text"), str):
            return str(response_data["translated_text"])
        return None

    async def _call_live_tts(self, text: str, language_locale: str) -> str | None:
        """Dispatches live TTS synthesis HTTP request."""
        target_url = f"{self._endpoint_url}/v1/tts/synthesize"
        payload = {"text": text, "language_locale": language_locale}
        response_data = await self._post_json(target_url, payload)
        if response_data and isinstance(response_data.get("audio_url"), str):
            return str(response_data["audio_url"])
        return None

    async def _post_json(self, url: str, json_data: dict[str, Any]) -> dict[str, Any] | None:
        """Executes resilient async POST request with timeout and authentication."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            client = self._http_client or get_shared_http_client()
            response = await client.post(
                url, json=json_data, headers=headers, timeout=self._timeout_seconds
            )
            if response.status_code == _HTTP_STATUS_OK:
                result = response.json()
                if isinstance(result, dict):
                    return result
            elif response.status_code in (_HTTP_STATUS_UNAUTHORIZED, _HTTP_STATUS_FORBIDDEN):
                if self._require_live:
                    raise ServiceAuthenticationError(
                        f"Bhashini authentication failed with status={response.status_code}"
                    )
            logger.warning("Live service call to %s returned status=%d", url, response.status_code)
        except (ServiceAuthenticationError, ServiceUnavailableError):
            raise
        except Exception as error:
            logger.warning(
                "Live service call to %s failed: %s; fallback_allowed=%s",
                url,
                error,
                not self._require_live,
            )
            if self._require_live:
                raise ServiceUnavailableError(
                    f"Live Bhashini API call to {url} failed: {error}"
                ) from error
        return None

    @staticmethod
    def _mock_transcribe_audio(audio_url: str, language_locale: str) -> str:
        """Deterministic local ASR simulation."""
        url_lower = audio_url.lower()
        if MOCK_STREAM_EMPTY_KEYWORD in url_lower:
            return ""
        if any(err in url_lower for err in MOCK_STREAM_ERROR_KEYWORDS):
            raise ValueError("ASR audio stream formatting or download error.")
        return MOCK_ASR_TRANSCRIPTIONS.get(language_locale, MOCK_ASR_TRANSCRIPTIONS["default"])

    @staticmethod
    def _mock_translate_text(text: str, source_locale: str, target_locale: str) -> str:
        """Deterministic local NMT simulation."""
        if source_locale == target_locale:
            return text
        if source_locale.startswith("hi") and target_locale.startswith("en"):
            for kw, translation in MOCK_NMT_TRANSLATIONS.items():
                if kw in text.lower():
                    return translation
            return MOCK_NMT_TRANSLATIONS[DEFAULT_NMT_FALLBACK_KEY]
        return f"[Translated to {target_locale}] {text}"

    @staticmethod
    def _mock_synthesize_speech(text: str, language_locale: str) -> str:
        """Deterministic local TTS simulation."""
        clean_locale = language_locale.replace("-", "_").lower()
        return MOCK_TTS_URL_TEMPLATE.format(locale=clean_locale)
