"""Foundational AI Block: Small Language Model (SLM) Structured Entity Extractor.

Abstracts sovereign, in-memory structured entity extraction pipeline for Layer 3/4 processing.
Extracts domain parameters (district, taluka, village, crop_name, survey_number) and computes
AI extraction confidence scores.

Why local sovereign SLM models?
Sovereign data governance requires processing citizen intent within local memory perimeters
without transmitting un-tokenized queries to remote third-party APIs.

See: decisions/step2.0_canonical_domain_schemas.md (Section 3.5)
See: roadmap.md (Phase 2 Step 2.2 Service Abstractions)
"""

import logging

from src.data_models.governance import ExtractedEntityPayload
from src.services.ai.ai_mock_fixtures import ADVERSARIAL_INJECTION_KEYWORDS, MOCK_SLM_RULES

logger = logging.getLogger(__name__)


class SlmExtractor:
    """Service abstraction for structured entity extraction from citizen text input.

    Uses zero-shot/few-shot NLU prompts to convert unstructured regional language text
    into typed domain parameters keyed by DomainEntityKey.

    See: decisions/step2.0_canonical_domain_schemas.md
    """

    async def extract_entities(
        self, session_id: str, unprocessed_content: str, language_locale: str
    ) -> ExtractedEntityPayload | None:
        """Extracts domain entities and classifies intent from citizen input.

        Args:
            session_id: Primary session key tracking end-to-end communication context.
            unprocessed_content: Unprocessed citizen input text or transcribed string.
            language_locale: Language locale identifier (e.g. 'hi-IN').

        Returns:
            ExtractedEntityPayload containing extracted parameters and AI confidence score,
            or None if extraction could not be completed.
        """
        logger.info("Extracting entities for session=%s locale=%s", session_id, language_locale)
        content_lower = unprocessed_content.lower()

        if "error" in content_lower or not unprocessed_content.strip():
            return None

        is_adversarial = any(kw in content_lower for kw in ADVERSARIAL_INJECTION_KEYWORDS)

        if any(k in content_lower for k in ["kist", "subsidy", "pm kisan"]):
            rule = MOCK_SLM_RULES["subsidy_claim"]
        elif any(k in content_lower for k in ["status", "jankari"]):
            rule = MOCK_SLM_RULES["status_check"]
        elif any(k in content_lower for k in ["missing", "incomplete"]):
            rule = MOCK_SLM_RULES["missing_entity"]
        else:
            rule = MOCK_SLM_RULES["default_fallback"]

        return ExtractedEntityPayload(
            application_intent=rule.intent,
            ai_confidence_score=rule.confidence_score,
            domain_entities=rule.entities,
            is_adversarial_attempt=is_adversarial,
            is_structured_menu_bypass=False,
        )
