"""Offline Mock Fixtures for Foundational AI Block Abstractions (Step 3.1).

Provides deterministic, locally testable data structures and response mappings for ASR, NMT,
TTS, and SLM structured entity extraction during offline development and testing.

Why abstract AI blocks behind offline simulation fixtures?
Sovereign orchestration development under an Inside-Out methodology requires decoupling core
state machine execution from real LLM inference latency, network timeouts, and non-deterministic
model hallucinations. These fixtures provide reproducible inputs for stress-testing
multi-attempt loops and adversarial prompt injection boundaries.

See: decisions/step3.1_foundational_mock_boundaries.md (Section 2)
See: roadmap.md (Phase 3 Step 3.1)
"""

from typing import Final, NamedTuple

from src.data_models.common import ApplicationIntent, DomainEntities, DomainEntityKey

__all__ = [
    "ADVERSARIAL_INJECTION_KEYWORDS",
    "DEFAULT_NMT_FALLBACK_KEY",
    "MISSING_ENTITY_KEYWORDS",
    "MOCK_ASR_TRANSCRIPTIONS",
    "MOCK_NMT_TRANSLATIONS",
    "MOCK_SLM_RULES",
    "MOCK_STREAM_EMPTY_KEYWORD",
    "MOCK_STREAM_ERROR_KEYWORDS",
    "MOCK_TTS_URL_TEMPLATE",
    "STATUS_CHECK_KEYWORDS",
    "SUBSIDY_CLAIM_KEYWORDS",
    "MockExtractionRule",
]

MOCK_ASR_TRANSCRIPTIONS: Final[dict[str, str]] = {
    "hi-IN": "Mujhe PM KISAN ki kist nahi mili hai, mera village Hadoli hai.",
    "en-IN": "I have not received my PM KISAN installment, my village is Hadoli.",
    "default": "I have not received my PM KISAN installment, my village is Hadoli.",
}

MOCK_NMT_TRANSLATIONS: Final[dict[str, str]] = {
    "kharab": "My crop in Karnal district has suffered weather damage.",
    "kist": "I have not received my PM KISAN installment of 2000 rupees.",
}
DEFAULT_NMT_FALLBACK_KEY: Final[str] = "kist"

MOCK_STREAM_EMPTY_KEYWORD: Final[str] = "empty"
MOCK_STREAM_ERROR_KEYWORDS: Final[tuple[str, ...]] = ("error", "invalid")

MOCK_TTS_URL_TEMPLATE: Final[str] = (
    "https://bhashini-gateway.ai/synth/2026_{locale}_response_824921.wav"
)

ADVERSARIAL_INJECTION_KEYWORDS: Final[tuple[str, ...]] = (
    "ignore previous",
    "override",
    "system prompt",
    "drop",
)

SUBSIDY_CLAIM_KEYWORDS: Final[tuple[str, ...]] = ("kist", "subsidy", "pm kisan")
STATUS_CHECK_KEYWORDS: Final[tuple[str, ...]] = ("status", "jankari")
MISSING_ENTITY_KEYWORDS: Final[tuple[str, ...]] = ("missing", "incomplete")


class MockExtractionRule(NamedTuple):
    """Configuration rule for deterministic SLM entity extraction simulations.

    Defines the expected parsed intent, entity dictionary, and confidence score for mock
    testing.

    Attributes:
        intent: Classified citizen application intent (`ApplicationIntent`).
        entities: Dictionary of extracted domain parameters keyed by `DomainEntityKey`.
        confidence_score: Simulated AI confidence score bounded to [0.0, 1.0].

    See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.1)
    """

    intent: ApplicationIntent
    entities: DomainEntities
    confidence_score: float


MOCK_SLM_RULES: Final[dict[str, MockExtractionRule]] = {
    "subsidy_claim": MockExtractionRule(
        intent=ApplicationIntent.APPLY_SUBSIDY,
        entities={
            DomainEntityKey.DISTRICT: "Pune",
            DomainEntityKey.TALUKA: "Haveli",
            DomainEntityKey.VILLAGE: "Hadoli",
            DomainEntityKey.CROP_NAME: "Wheat",
            DomainEntityKey.SURVEY_NUMBER: "124/2A",
        },
        confidence_score=0.96,
    ),
    "status_check": MockExtractionRule(
        intent=ApplicationIntent.CHECK_STATUS,
        entities={
            DomainEntityKey.DISTRICT: "Pune",
            DomainEntityKey.VILLAGE: "Hadoli",
        },
        confidence_score=0.92,
    ),
    "missing_entity": MockExtractionRule(
        intent=ApplicationIntent.APPLY_SUBSIDY,
        entities={
            DomainEntityKey.DISTRICT: "Pune",
        },
        confidence_score=0.65,
    ),
    "default_fallback": MockExtractionRule(
        intent=ApplicationIntent.APPLY_SUBSIDY,
        entities={
            DomainEntityKey.DISTRICT: "Karnal",
            DomainEntityKey.TALUKA: "Nilokheri",
            DomainEntityKey.VILLAGE: "Sultanpur",
            DomainEntityKey.CROP_NAME: "Rice",
            DomainEntityKey.SURVEY_NUMBER: "45/1B",
        },
        confidence_score=0.88,
    ),
}
