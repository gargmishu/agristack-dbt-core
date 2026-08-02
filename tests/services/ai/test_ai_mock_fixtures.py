from src.data_models.common import ApplicationIntent
from src.services.ai.ai_mock_fixtures import (
    ADVERSARIAL_INJECTION_KEYWORDS,
    MOCK_ASR_TRANSCRIPTIONS,
    MOCK_NMT_TRANSLATIONS,
    MOCK_SLM_RULES,
    MOCK_TTS_URL_TEMPLATE,
)


def test_ai_mock_fixtures_integrity() -> None:
    assert "hi-IN" in MOCK_ASR_TRANSCRIPTIONS
    assert "default" in MOCK_ASR_TRANSCRIPTIONS
    assert "kist" in MOCK_NMT_TRANSLATIONS
    assert "{locale}" in MOCK_TTS_URL_TEMPLATE
    assert "ignore previous" in ADVERSARIAL_INJECTION_KEYWORDS
    assert MOCK_SLM_RULES["subsidy_claim"].intent == ApplicationIntent.APPLY_SUBSIDY
