"""Foundational AI Block: Speech & Translation Service (Bhashini Abstraction).

Abstracts ASR (Automatic Speech Recognition), NMT (Neural Machine Translation), and TTS
(Text-to-Speech) capabilities for sovereign multi-lingual citizen engagement across Indic
languages.

Why abstract AI services behind interfaces?
Model architectures and translation providers evolve rapidly. Decoupling the ingestion edge
from specific translation services allows swapping backends without breaking Layer 3/4
contracts.

See: decisions/step2.0_canonical_domain_schemas.md (Section 3.5)
See: roadmap.md (Phase 2 Step 2.2 Service Abstractions)
"""

import hashlib
import logging
from typing import Any, Final

import httpx

from src.services.ai.ai_mock_fixtures import (
    DEFAULT_NMT_FALLBACK_KEY,
    MOCK_ASR_TRANSCRIPTIONS,
    MOCK_NMT_TRANSLATIONS,
    MOCK_STREAM_EMPTY_KEYWORD,
    MOCK_STREAM_ERROR_KEYWORDS,
    MOCK_TTS_URL_TEMPLATE,
)

logger = logging.getLogger(__name__)

_DEFAULT_AI_TIMEOUT_SECONDS: Final[float] = 2.0
_HTTP_STATUS_OK: Final[int] = 200


class BhashiniService:
    """Service client for multi-lingual speech transcription, translation, and audio synthesis.

    Provides multi-lingual voice and text processing across Indian regional language locales:
    - Audio Transcription (`transcribe_audio`): Transcribes audio into Indic vernacular text.
    - Text Translation (`translate_text`): Translates regional language text into canonical English.
    - Speech Synthesis (`synthesize_speech`): Generates audio stream URLs for vernacular text.

    Supports live REST endpoints with automatic, graceful fallback to deterministic local fixtures.

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
    ) -> None:
        """Initializes Bhashini service client with optional live endpoint configuration.

        Args:
            endpoint_url: Optional base HTTP URL for live Bhashini API service.
            api_key: Optional authorization Bearer token or API key for live calls.
            http_client: Optional async HTTP client for connection pooling.
            timeout_seconds: Request timeout in seconds (default: 2.0s).
        """
        self._endpoint_url = endpoint_url.rstrip("/") if endpoint_url else None
        self._api_key = api_key
        self._http_client = http_client
        self._timeout_seconds = timeout_seconds

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
        """
        url_hash = hashlib.sha256(audio_url.encode("utf-8")).hexdigest()[:16]
        logger.info("Transcribing audio for url_hash=%s locale=%s", url_hash, language_locale)

        if self._endpoint_url:
            live_result = await self._call_live_asr(audio_url, language_locale)
            if live_result is not None:
                return live_result

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
        """
        logger.info("Translating text from %s to %s", source_locale, target_locale)
        if not text.strip():
            return ""

        if self._endpoint_url:
            live_result = await self._call_live_nmt(text, source_locale, target_locale)
            if live_result is not None:
                return live_result

        return self._mock_translate_text(text, source_locale, target_locale)

    async def synthesize_speech(self, text: str, language_locale: str) -> str:
        """Synthesizes response text into spoken audio stream URL for voice/audio channels.

        Args:
            text: Text content to synthesize into speech.
            language_locale: Target speech language locale identifier.

        Returns:
            URL pointer to generated audio recording.
        """
        logger.info("Synthesizing speech for locale=%s text_len=%d", language_locale, len(text))
        if not text.strip():
            raise ValueError("Cannot synthesize empty response text into speech.")

        if self._endpoint_url:
            live_result = await self._call_live_tts(text, language_locale)
            if live_result is not None:
                return live_result

        return self._mock_synthesize_speech(text, language_locale)

    # -------------------------------------------------------------------------
    # Private Helpers (Live HTTP & Local Mock Handlers)
    # -------------------------------------------------------------------------

    async def _call_live_asr(self, audio_url: str, language_locale: str) -> str | None:
        """Dispatches live ASR transcription HTTP request with graceful fallback."""
        target_url = f"{self._endpoint_url}/v1/asr/transcribe"
        payload = {"audio_url": audio_url, "language_locale": language_locale}
        response_data = await self._post_json(target_url, payload)
        if response_data and isinstance(response_data.get("transcript"), str):
            return str(response_data["transcript"])
        return None

    async def _call_live_nmt(self, text: str, source_locale: str, target_locale: str) -> str | None:
        """Dispatches live NMT translation HTTP request with graceful fallback."""
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
        """Dispatches live TTS synthesis HTTP request with graceful fallback."""
        target_url = f"{self._endpoint_url}/v1/tts/synthesize"
        payload = {"text": text, "language_locale": language_locale}
        response_data = await self._post_json(target_url, payload)
        if response_data and isinstance(response_data.get("audio_url"), str):
            return str(response_data["audio_url"])
        return None

    async def _post_json(self, url: str, json_data: dict[str, Any]) -> dict[str, Any] | None:
        """Executes resilient async POST request with timeout and error suppression."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            if self._http_client:
                response = await self._http_client.post(
                    url, json=json_data, headers=headers, timeout=self._timeout_seconds
                )
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url, json=json_data, headers=headers, timeout=self._timeout_seconds
                    )
            if response.status_code == _HTTP_STATUS_OK:
                result = response.json()
                if isinstance(result, dict):
                    return result
            logger.warning("Live service call to %s returned status=%d", url, response.status_code)
        except Exception as error:
            logger.warning("Live service call to %s failed: %s; using mock fallback", url, error)
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
