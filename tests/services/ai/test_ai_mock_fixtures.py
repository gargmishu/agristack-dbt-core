from src.data_models.common import ApplicationIntent
from src.services.ai.ai_mock_fixtures import (
    ADVERSARIAL_INJECTION_KEYWORDS,
    DEFAULT_NMT_FALLBACK_KEY,
    MISSING_ENTITY_KEYWORDS,
    MOCK_ASR_TRANSCRIPTIONS,
    MOCK_NMT_TRANSLATIONS,
    MOCK_SLM_RULES,
    MOCK_STREAM_EMPTY_KEYWORD,
    MOCK_STREAM_ERROR_KEYWORDS,
    MOCK_TTS_URL_TEMPLATE,
    STATUS_CHECK_KEYWORDS,
    SUBSIDY_CLAIM_KEYWORDS,
)


def test_ai_mock_fixtures_integrity() -> None:
    assert "hi-IN" in MOCK_ASR_TRANSCRIPTIONS
    assert "default" in MOCK_ASR_TRANSCRIPTIONS
    assert "kist" in MOCK_NMT_TRANSLATIONS
    assert DEFAULT_NMT_FALLBACK_KEY == "kist"
    assert MOCK_STREAM_EMPTY_KEYWORD == "empty"
    assert "error" in MOCK_STREAM_ERROR_KEYWORDS
    assert "{locale}" in MOCK_TTS_URL_TEMPLATE
    assert "ignore previous" in ADVERSARIAL_INJECTION_KEYWORDS
    assert "subsidy" in SUBSIDY_CLAIM_KEYWORDS
    assert "status" in STATUS_CHECK_KEYWORDS
    assert "missing" in MISSING_ENTITY_KEYWORDS
    assert MOCK_SLM_RULES["subsidy_claim"].intent == ApplicationIntent.APPLY_SUBSIDY
