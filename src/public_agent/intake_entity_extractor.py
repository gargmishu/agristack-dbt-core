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
from typing import Final

from src.data_models.common import (
    ApplicationIntent,
    DomainEntities,
    DomainEntityKey,
)
from src.data_models.governance import ExtractedEntityPayload
from src.data_models.public_agent import PublicAgentStandardizedIntakePayload
from src.services.ai import (
    BhashiniService,
    SlmExtractor,
    create_bhashini_service,
    create_slm_extractor,
)

logger = logging.getLogger(__name__)

__all__ = ["IntakeEntityExtractor"]

_FALLBACK_CONFIDENCE_SCORE: Final[float] = 0.40

_STRUCTURED_INTENT_MAP: Final[dict[str, ApplicationIntent]] = {
    "1": ApplicationIntent.APPLY_SUBSIDY,
    "2": ApplicationIntent.CHECK_STATUS,
    "3": ApplicationIntent.SUBMIT_APPEAL,
    "4": ApplicationIntent.SCHEME_INQUIRY,
}

_STRUCTURED_CROP_MAP: Final[dict[str, str]] = {
    "1": "Rice",
    "2": "Wheat",
    "3": "Sugarcane",
}

_STRUCTURED_PARCEL_MAP: Final[dict[str, tuple[str, str]]] = {
    "101": ("Karnal", "LAND-REC-1002"),
    "204": ("Karnal", "LAND-REC-2004"),
    "306": ("Nashik", "LAND-REC-3006"),
    "000": ("Karnal", "000/0"),
}


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
        self._bhashini = bhashini_service or create_bhashini_service()
        self._slm_extractor = slm_extractor or create_slm_extractor()

    # -------------------------------------------------------------------------
    # Primary Public Workflow Entrypoint
    # -------------------------------------------------------------------------

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
            return self._parse_structured_menu_input(intake.unprocessed_input_content)

        # Audio Modality: Transcribe via Bhashini ASR
        text_to_extract = intake.unprocessed_input_content
        if intake.payload_type.is_audio:
            try:
                text_to_extract = await self._bhashini.transcribe_audio(
                    audio_url=intake.unprocessed_input_content,
                    language_locale=intake.language_locale,
                )
            except Exception as error:
                logger.warning(
                    "Audio transcription failed for session=%s: %s; using fallback",
                    intake.session_id,
                    error,
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

    # -------------------------------------------------------------------------
    # Private Helpers (Strictly at Bottom)
    # -------------------------------------------------------------------------

    @staticmethod
    def _parse_structured_menu_input(raw_menu_input: str) -> ExtractedEntityPayload:
        """Parses USSD or DTMF keypad sequences (e.g. '1*2*101' or '1#') into domain entities.

        Menu sequence format: '<intent_code>*<crop_code>*<parcel_code>'
        - intent_code: '1' -> APPLY_SUBSIDY, '2' -> CHECK_STATUS, '3' -> SUBMIT_APPEAL,
          '4' -> SCHEME_INQUIRY
        - crop_code: '1' -> Rice, '2' -> Wheat, '3' -> Sugarcane
        - parcel_code: '101' -> (Karnal, LAND-REC-1002), '204' -> (Karnal, LAND-REC-2004),
          '306' -> (Nashik, LAND-REC-3006), '000' -> (Karnal, 000/0)
        """
        normalized_menu_text = raw_menu_input.strip().rstrip("#")
        menu_segments = [
            segment.strip() for segment in normalized_menu_text.split("*") if segment.strip()
        ]

        intent_code = menu_segments[0] if menu_segments else "1"
        crop_code = menu_segments[1] if len(menu_segments) > 1 else "2"
        parcel_segment_index = 2
        parcel_code = (
            menu_segments[parcel_segment_index]
            if len(menu_segments) > parcel_segment_index
            else "101"
        )

        resolved_intent = _STRUCTURED_INTENT_MAP.get(intent_code, ApplicationIntent.APPLY_SUBSIDY)
        resolved_crop = _STRUCTURED_CROP_MAP.get(crop_code, "Wheat")
        resolved_district, resolved_survey_number = _STRUCTURED_PARCEL_MAP.get(
            parcel_code, ("Karnal", "LAND-REC-1002")
        )

        entities: DomainEntities = {
            DomainEntityKey.DISTRICT: resolved_district,
            DomainEntityKey.CROP_NAME: resolved_crop,
            DomainEntityKey.SURVEY_NUMBER: resolved_survey_number,
        }
        return ExtractedEntityPayload(
            application_intent=resolved_intent,
            ai_confidence_score=1.0,
            domain_entities=entities,
            is_adversarial_attempt=False,
            is_structured_menu_bypass=True,
        )

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
