"""Foundational AI Block: Small Language Model (SLM) Entity Extractor.

Abstracts sovereign, in-memory structured entity extraction pipeline for Layer 3/4 processing.

See: decisions/step2.0_canonical_domain_schemas.md
See: roadmap.md (Phase 2 Step 2.2 Service Abstractions)
"""

import logging

from src.data_models.governance import ExtractedEntityPayload

logger = logging.getLogger(__name__)


class SlmExtractor:
    """Service abstraction for structured entity extraction from raw citizen input."""

    async def extract_entities(
        self, session_id: str, unprocessed_content: str, language_locale: str
    ) -> ExtractedEntityPayload | None:
        """Extracts domain entities and intent from unprocessed citizen text input.

        Args:
            session_id: Unified session key tracking communication context.
            unprocessed_content: Unprocessed citizen input string.
            language_locale: Language locale of the input text.

        Returns:
            ExtractedEntityPayload containing extracted parameters and confidence score, or None.
        """
        logger.info("Extracting entities for session=%s locale=%s", session_id, language_locale)
        return None
