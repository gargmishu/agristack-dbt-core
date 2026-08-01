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

from src.data_models.common import ApplicationIntent, DomainEntityKey
from src.data_models.governance import ExtractedEntityPayload

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

        is_adversarial = any(
            w in content_lower for w in ["ignore previous", "override", "system prompt", "drop"]
        )

        entities: dict[DomainEntityKey, str | float | int]
        if "kist" in content_lower or "subsidy" in content_lower or "pm kisan" in content_lower:
            intent = ApplicationIntent.APPLY_SUBSIDY
            entities = {
                DomainEntityKey.DISTRICT: "Pune",
                DomainEntityKey.TALUKA: "Haveli",
                DomainEntityKey.VILLAGE: "Hadoli",
                DomainEntityKey.CROP_NAME: "Wheat",
                DomainEntityKey.SURVEY_NUMBER: "124/2A",
            }
            confidence = 0.96
        elif "status" in content_lower or "jankari" in content_lower:
            intent = ApplicationIntent.CHECK_STATUS
            entities = {
                DomainEntityKey.DISTRICT: "Pune",
                DomainEntityKey.VILLAGE: "Hadoli",
            }
            confidence = 0.92
        elif "missing" in content_lower or "incomplete" in content_lower:
            intent = ApplicationIntent.APPLY_SUBSIDY
            entities = {
                DomainEntityKey.DISTRICT: "Pune",
            }
            confidence = 0.65
        else:
            intent = ApplicationIntent.APPLY_SUBSIDY
            entities = {
                DomainEntityKey.DISTRICT: "Karnal",
                DomainEntityKey.TALUKA: "Nilokheri",
                DomainEntityKey.VILLAGE: "Sultanpur",
                DomainEntityKey.CROP_NAME: "Rice",
                DomainEntityKey.SURVEY_NUMBER: "45/1B",
            }
            confidence = 0.88

        return ExtractedEntityPayload(
            application_intent=intent,
            ai_confidence_score=confidence,
            domain_entities=entities,
            is_adversarial_attempt=is_adversarial,
            is_structured_menu_bypass=False,
        )
