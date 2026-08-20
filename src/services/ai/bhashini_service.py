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

from src.services.ai.ai_mock_fixtures import (
    DEFAULT_NMT_FALLBACK_KEY,
    MOCK_ASR_TRANSCRIPTIONS,
    MOCK_NMT_TRANSLATIONS,
    MOCK_STREAM_EMPTY_KEYWORD,
    MOCK_STREAM_ERROR_KEYWORDS,
    MOCK_TTS_URL_TEMPLATE,
)

logger = logging.getLogger(__name__)


class BhashiniService:
    """Service client for multi-lingual speech transcription, translation, and audio synthesis.

    Provides multi-lingual voice and text processing across Indian regional language
    locales:
    - Audio Transcription (`transcribe_audio`): Transcribes audio recordings into vernacular
      Indic text.
    - Text Translation (`translate_text`): Translates regional language text into canonical
      English representations.
    - Speech Synthesis (`synthesize_speech`): Generates audio stream URLs for synthesized
      vernacular text.

    See: decisions/step2.0_canonical_domain_schemas.md (Section 3.2)
    See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.1)
    """

    async def transcribe_audio(self, audio_url: str, language_locale: str) -> str:
        """Transcribes raw voice stream into text in the specified language locale.

        Args:
            audio_url: Valid HTTP/HTTPS audio recording URL pointer from IVR/WhatsApp edge.
            language_locale: BCP 47 language locale identifier (e.g., 'hi-IN', 'ta-IN').

        Returns:
            Transcribed text string in original spoken language.
        """
        # Zero-PII Defense: Hash audio_url before logging to prevent leaking pre-signed tokens
        # or MSISDN phone number identifiers in URL paths.
        url_hash = hashlib.sha256(audio_url.encode("utf-8")).hexdigest()[:16]
        logger.info("Transcribing audio for url_hash=%s locale=%s", url_hash, language_locale)
        url_lower = audio_url.lower()
        if MOCK_STREAM_EMPTY_KEYWORD in url_lower:
            return ""
        if any(err in url_lower for err in MOCK_STREAM_ERROR_KEYWORDS):
            raise ValueError("ASR audio stream formatting or download error.")

        return MOCK_ASR_TRANSCRIPTIONS.get(language_locale, MOCK_ASR_TRANSCRIPTIONS["default"])

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
        if source_locale == target_locale:
            return text
        if source_locale.startswith("hi") and target_locale.startswith("en"):
            for kw, translation in MOCK_NMT_TRANSLATIONS.items():
                if kw in text.lower():
                    return translation
            return MOCK_NMT_TRANSLATIONS[DEFAULT_NMT_FALLBACK_KEY]
        return f"[Translated to {target_locale}] {text}"

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
        clean_locale = language_locale.replace("-", "_").lower()
        return MOCK_TTS_URL_TEMPLATE.format(locale=clean_locale)
