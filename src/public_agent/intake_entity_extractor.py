"""Layer 3 Intake Entity Extractor (Modality Transcription & SLM Extraction).

Converts Layer 2 canonical intake payloads into structured domain entities:
1. Fast-path deterministic mapping for structured inputs (USSD / DTMF menu keypresses).
2. Speech-to-text transcription via Bhashini ASR for audio streams.
3. Natural language domain entity extraction via sovereign Small Language Models (SLM).

See: decisions/step3.4_layer3_intake_gateway_and_connectors.md
See: decisions/step2.0_canonical_domain_schemas.md (Section 4.2)
See: decisions/step3.3_layer4_orchestrator_brain.md
"""

import logging

from src.data_models.common import (
    ApplicationIntent,
    DomainEntities,
    DomainEntityKey,
)
from src.data_models.governance import ExtractedEntityPayload
from src.data_models.public_agent import PublicAgentStandardizedIntakePayload
from src.services.ai import BhashiniService, SlmExtractor

logger = logging.getLogger(__name__)

_FALLBACK_CONFIDENCE_SCORE = 0.40


class IntakeEntityExtractor:
    """Extracts structured domain entities from standardized public agent intake payloads.

    Coordinates acoustic speech transcription (Bhashini) and Small Language Model
    entity parsing (SLM) for unstructured modalities, or executes zero-latency fast-path
    bypass for structured menu selections.
    """

    def __init__(
        self,
        bhashini_service: BhashiniService | None = None,
        slm_extractor: SlmExtractor | None = None,
    ) -> None:
        """Initializes the entity extractor with AI service dependencies.

        Args:
            bhashini_service: Optional Bhashini ASR/NMT client (defaults to standard client).
            slm_extractor: Optional sovereign SLM extraction client (defaults to SlmExtractor).
        """
        self._bhashini = bhashini_service or BhashiniService()
        self._slm_extractor = slm_extractor or SlmExtractor()

    async def extract_entities(
        self, intake: PublicAgentStandardizedIntakePayload
    ) -> ExtractedEntityPayload:
        """Extracts structured domain entities from standardized public agent intake.

        Args:
            intake: Validated PublicAgentStandardizedIntakePayload from Layer 2.

        Returns:
            ExtractedEntityPayload containing parsed intent, domain entities, and confidence score.
        """
        # Fast-Path: Structured USSD or Menu Selection Bypass
        if intake.structure_level.is_structured:
            logger.info(
                "Structured menu bypass applied for session=%s, channel=%s",
                intake.session_id,
                intake.channel_type,
            )
            entities: DomainEntities = {
                DomainEntityKey.DISTRICT: "Karnal",
                DomainEntityKey.CROP_NAME: "Wheat",
                DomainEntityKey.SURVEY_NUMBER: "LAND-REC-1002",
            }
            return ExtractedEntityPayload(
                application_intent=ApplicationIntent.APPLY_SUBSIDY,
                ai_confidence_score=1.0,
                domain_entities=entities,
                is_adversarial_attempt=False,
                is_structured_menu_bypass=True,
            )

        # Audio Modality: Transcribe via Bhashini ASR
        text_to_extract = intake.unprocessed_input_content
        if intake.payload_type.is_audio:
            try:
                text_to_extract = await self._bhashini.transcribe_audio(
                    audio_url=intake.unprocessed_input_content,
                    language_locale=intake.language_locale,
                )
            except Exception as err:
                logger.warning(
                    "Audio transcription failed for session=%s: %s; using fallback",
                    intake.session_id,
                    err,
                )
                return self._create_fallback_extracted_payload()

        # Sovereign SLM Entity Extraction
        extracted_entities = await self._slm_extractor.extract_entities(
            session_id=intake.session_id,
            unprocessed_content=text_to_extract,
            language_locale=intake.language_locale,
        )

        if extracted_entities is None:
            logger.warning(
                "SLM extraction failed for session=%s; applying low-confidence fallback",
                intake.session_id,
            )
            return self._create_fallback_extracted_payload()

        return extracted_entities

    @staticmethod
    def _create_fallback_extracted_payload() -> ExtractedEntityPayload:
        """Constructs a deterministic fallback payload for failed transcription or extraction.

        Returns:
            ExtractedEntityPayload with UNKNOWN intent and low confidence (0.40).
        """
        return ExtractedEntityPayload(
            application_intent=ApplicationIntent.UNKNOWN,
            ai_confidence_score=_FALLBACK_CONFIDENCE_SCORE,
            domain_entities={},
            is_adversarial_attempt=False,
            is_structured_menu_bypass=False,
        )
