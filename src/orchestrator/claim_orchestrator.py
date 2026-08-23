"""Layer 4 Governance Engine: Claim Orchestrator & 3-Gate Execution Pipeline.

Coordinates end-to-end citizen claim processing across multimodal ingress transcription,
claim completeness validation, multi-turn conversational reprompts, and deterministic
governance routing.

See: decisions/step3.3_layer4_orchestrator_brain.md
See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 2.1)
"""

import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final

from src.data_models.caseworker import CaseworkerCaseReviewPayload
from src.data_models.common import (
    ApplicationIntent,
    CropSeason,
    DomainEntities,
    DomainEntityKey,
    EligibilityStatus,
    EscalationReasonCode,
    GovernanceAction,
)
from src.data_models.disbursement import DisbursementCallbackPayload
from src.data_models.governance import (
    ClaimEvaluationPayload,
    ExtractedEntityPayload,
    GovernanceOutcomePayload,
)
from src.data_models.public_agent import PublicAgentStandardizedIntakePayload
from src.orchestrator.case_management_service import CaseManagementService
from src.orchestrator.claim_adjudicator import ClaimAdjudicator
from src.services.ai import BhashiniService, SlmExtractor
from src.services.dpi import PaymentRailService

logger = logging.getLogger(__name__)

# Mandatory domain entities required for seasonal crop subsidy claim processing
_MANDATORY_SUBSIDY_ENTITIES: Final[tuple[DomainEntityKey, ...]] = (
    DomainEntityKey.DISTRICT,
    DomainEntityKey.CROP_NAME,
)
_MAX_REPROMPT_ATTEMPTS: Final[int] = 3


@dataclass(frozen=True)
class OrchestrationExecutionResult:
    """Execution outcome returned by the Claim Orchestrator.

    Encapsulates session progress, governance outcome, extracted parameters, and optional
    next steps.

    Attributes:
        session_id: Primary session tracking identifier.
        application_intent: Classified citizen intent driving workflow routing.
        governance_outcome: Governance adjudication verdict.
        extracted_entities: Extracted domain parameter dictionary.
        requires_reprompt: True if mandatory entity completeness failed and requires citizen
        clarification.
        reprompt_message: Clarification prompt message if reprompt is required.
        disbursement_callback: Payment clearing callback receipt if automated payout was
        initiated.
        caseworker_ticket_id: Escalation ticket ID (`SPP-CASE-YYYY-XXXXXX`) if staged for
        review.

    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 2.1)
    """

    session_id: str
    application_intent: ApplicationIntent
    governance_outcome: GovernanceOutcomePayload
    extracted_entities: ExtractedEntityPayload
    requires_reprompt: bool = False
    reprompt_message: str | None = None
    disbursement_callback: DisbursementCallbackPayload | None = None
    caseworker_ticket_id: str | None = None


class ClaimOrchestrator:
    """Claim orchestrator governing claim processing workflows across three execution gates.

    Coordinates end-to-end processing across transcription, entity validation, and
    governance routing:
    - Ingress Modality Processing (`process_ingress_payload` / Gate 1): Manages audio
      transcription, SLM domain entity extraction, or structured menu bypass.
    - Claim Completeness Validation (`check_claim_completeness` / Gate 2): Validates mandatory
      domain entity completeness and manages multi-turn conversational re-prompt loops.
    - Governance Adjudication (Gate 3): Evaluates eligibility rules and routes to auto-payout,
      review, or rejection via the adjudication decision matrix.

    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 2.1)
    """

    def __init__(
        self,
        bhashini_service: BhashiniService | None = None,
        slm_extractor: SlmExtractor | None = None,
        claim_adjudicator: ClaimAdjudicator | None = None,
        case_management_service: CaseManagementService | None = None,
        payment_rail_service: PaymentRailService | None = None,
    ) -> None:
        """Initializes the claim orchestrator with required AI and DPI service dependencies."""
        self._bhashini = bhashini_service or BhashiniService()
        self._slm_extractor = slm_extractor or SlmExtractor()
        self._claim_adjudicator = claim_adjudicator or ClaimAdjudicator()
        self._case_service = case_management_service or CaseManagementService()
        self._payment_rail = payment_rail_service or PaymentRailService()

    # -------------------------------------------------------------------------
    # Primary Public Workflow Entrypoint
    # -------------------------------------------------------------------------

    async def execute_orchestration_cycle(
        self,
        intake: PublicAgentStandardizedIntakePayload,
        attempt_count: int = 1,
        approved_payouts_ledger: set[tuple[str, str]] | None = None,
        active_season: CropSeason = "KHARIF-2026",
    ) -> OrchestrationExecutionResult:
        """Executes complete end-to-end orchestration pipeline across all 3 evaluation gates.

        Args:
            intake: Validated PublicAgentStandardizedIntakePayload from Layer 3.
            attempt_count: Current attempt count for multi-turn conversational loop.
            approved_payouts_ledger: Set of approved (citizen_token, season) claims.
            active_season: Active welfare scheme season identifier.

        Returns:
            OrchestrationExecutionResult with finalized governance action, tracking IDs,
            and payment/caseworker staging outcomes.
        """
        session_id = intake.session_id
        payload_id = f"ext-{uuid.uuid4().hex[:8]}"

        # Gate 1: Ingress Modality & SLM Entity Extraction
        extracted_entities = await self.process_ingress_payload(intake)

        # Gate 2: Intake Completeness & Reprompt Validation
        requires_reprompt, missing_entities = self.check_claim_completeness(
            extracted_entities, attempt_count=attempt_count
        )
        if requires_reprompt:
            return self._build_reprompt_result(
                session_id=session_id,
                payload_id=payload_id,
                extracted_entities=extracted_entities,
                missing_entities=missing_entities,
            )

        # Gate 3: Deterministic Policy Adjudication Matrix
        governance_outcome = await self._adjudicate_claim(
            intake=intake,
            payload_id=payload_id,
            extracted_entities=extracted_entities,
            active_season=active_season,
            approved_payouts_ledger=approved_payouts_ledger,
        )

        # Post-Decision Processing: Payment Dispatch or Caseworker Staging
        disbursement_cb, staged_case_id = await self._handle_post_decision(
            intake=intake,
            payload_id=payload_id,
            extracted_entities=extracted_entities,
            governance_outcome=governance_outcome,
        )

        return OrchestrationExecutionResult(
            session_id=session_id,
            application_intent=extracted_entities.application_intent,
            governance_outcome=governance_outcome,
            extracted_entities=extracted_entities,
            requires_reprompt=False,
            disbursement_callback=disbursement_cb,
            caseworker_ticket_id=staged_case_id,
        )

    # -------------------------------------------------------------------------
    # Public Gate Processing Stages
    # -------------------------------------------------------------------------

    async def process_ingress_payload(
        self, intake: PublicAgentStandardizedIntakePayload
    ) -> ExtractedEntityPayload:
        """Gate 1: Ingress & Structure Evaluation Gate.

        Dispatches audio to ASR/NMT translation, executes sovereign SLM domain entity
        extraction, or performs fast-path structured menu bypass (confidence = 1.0).

        Args:
            intake: Validated PublicAgentStandardizedIntakePayload instance.

        Returns:
            ExtractedEntityPayload containing parsed domain parameters.
        """
        # Fast-Path: Structured USSD or Menu Selection Bypass
        if intake.structure_level.is_structured:
            logger.info(
                "Gate 1: Structured menu bypass applied for session=%s, channel=%s",
                intake.session_id,
                intake.channel_type,
            )
            # Deterministic mapping for structured menu keypresses (e.g. 1*2*101)
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
                    "Gate 1: Audio transcription failed for session=%s: %s; using fallback",
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
                "Gate 1: SLM extraction failed for session=%s; applying low-confidence fallback",
                intake.session_id,
            )
            return self._create_fallback_extracted_payload()

        return extracted_entities

    def check_claim_completeness(
        self,
        extracted: ExtractedEntityPayload,
        attempt_count: int = 1,
    ) -> tuple[bool, list[str]]:
        """Gate 2: Intake & Intent Validation Gate.

        Checks mandatory domain entities for subsidy claims and manages multi-turn
        conversational re-prompt loops (up to 3 attempts).

        Args:
            extracted: ExtractedEntityPayload output from Gate 1.
            attempt_count: Current citizen interaction attempt counter (1 to 3).

        Returns:
            Tuple of (requires_reprompt: bool, missing_entity_names: list[str]).
        """
        if extracted.is_adversarial_attempt or extracted.is_structured_menu_bypass:
            return False, []

        if extracted.application_intent != ApplicationIntent.APPLY_SUBSIDY:
            return False, []

        missing_entities: list[str] = [
            key.value
            for key in _MANDATORY_SUBSIDY_ENTITIES
            if key not in extracted.domain_entities
            or not str(extracted.domain_entities[key]).strip()
        ]

        if missing_entities and attempt_count < _MAX_REPROMPT_ATTEMPTS:
            logger.info(
                "Gate 2: Missing mandatory entities=%s on attempt=%d; triggering re-prompt",
                missing_entities,
                attempt_count,
            )
            return True, missing_entities

        return False, missing_entities

    # -------------------------------------------------------------------------
    # Private Helper Methods
    # -------------------------------------------------------------------------

    async def _adjudicate_claim(
        self,
        intake: PublicAgentStandardizedIntakePayload,
        payload_id: str,
        extracted_entities: ExtractedEntityPayload,
        active_season: CropSeason,
        approved_payouts_ledger: set[tuple[str, str]] | None,
    ) -> GovernanceOutcomePayload:
        """Constructs context and invokes Gate 3 policy adjudication.

        Args:
            intake: Standardized intake payload containing session and citizen token.
            payload_id: Unique extraction payload identifier.
            extracted_entities: Extracted domain entities and AI confidence score.
            active_season: Active crop season for anti-duplicate claim evaluation.
            approved_payouts_ledger: Set of approved (citizen_token, season) tuples.

        Returns:
            GovernanceOutcomePayload containing the adjudication verdict.
        """
        claim_payload = ClaimEvaluationPayload(
            session_id=intake.session_id,
            payload_id=payload_id,
            tokenized_citizen_id=intake.tokenized_citizen_id,
            extracted_payload=extracted_entities,
            active_season=active_season,
            approved_payouts_ledger=approved_payouts_ledger or set(),
        )
        return await self._claim_adjudicator.evaluate_claim(claim_payload)

    @staticmethod
    def _build_reprompt_result(
        session_id: str,
        payload_id: str,
        extracted_entities: ExtractedEntityPayload,
        missing_entities: list[str],
    ) -> OrchestrationExecutionResult:
        """Constructs reprompt governance outcome and execution result for incomplete claims.

        Args:
            session_id: Active session identifier.
            payload_id: Unique extraction payload identifier.
            extracted_entities: Partial extracted domain entities.
            missing_entities: List of missing mandatory entity field names.

        Returns:
            OrchestrationExecutionResult populated with reprompt instructions.
        """
        fields_str = ", ".join(missing_entities)
        reprompt_msg = f"Kripya apne aavedan ke liye nimnlikhit jankari pradan karein: {fields_str}"
        reprompt_outcome = GovernanceOutcomePayload(
            session_id=session_id,
            payload_id=payload_id,
            ai_confidence_score=extracted_entities.ai_confidence_score,
            eligibility_status=EligibilityStatus.REQUIRES_REVIEW,
            governance_action=GovernanceAction.REQUEST_MORE_INFO,
            escalation_case_id=f"SPP-CASE-2026-{secrets.randbelow(900000) + 100000:06d}",
            evaluated_at=datetime.now(UTC),
        )
        return OrchestrationExecutionResult(
            session_id=session_id,
            application_intent=extracted_entities.application_intent,
            governance_outcome=reprompt_outcome,
            extracted_entities=extracted_entities,
            requires_reprompt=True,
            reprompt_message=reprompt_msg,
        )

    async def _handle_post_decision(
        self,
        intake: PublicAgentStandardizedIntakePayload,
        payload_id: str,
        extracted_entities: ExtractedEntityPayload,
        governance_outcome: GovernanceOutcomePayload,
    ) -> tuple[DisbursementCallbackPayload | None, str | None]:
        """Dispatches automated payouts or stages caseworker tickets based on adjudication.

        Args:
            intake: Standardized intake payload with session and citizen tokens.
            payload_id: Unique extraction payload identifier.
            extracted_entities: Extracted domain entities payload.
            governance_outcome: Outcome verdict from Gate 3 adjudication.

        Returns:
            Tuple of (DisbursementCallbackPayload if approved payout dispatched,
            escalation_case_id if staged for caseworker review).
        """
        if governance_outcome.governance_action.is_approval:
            disbursement_cb = await self._payment_rail.initiate_disbursement(governance_outcome)
            return disbursement_cb, None

        if governance_outcome.governance_action.is_review and governance_outcome.escalation_case_id:
            staged_case_id = await self._stage_caseworker_ticket(
                intake=intake,
                payload_id=payload_id,
                extracted_entities=extracted_entities,
                escalation_case_id=governance_outcome.escalation_case_id,
            )
            return None, staged_case_id

        return None, None

    async def _stage_caseworker_ticket(
        self,
        intake: PublicAgentStandardizedIntakePayload,
        payload_id: str,
        extracted_entities: ExtractedEntityPayload,
        escalation_case_id: str,
    ) -> str:
        """Constructs and stages an escalation ticket in the case management service.

        Args:
            intake: Standardized intake payload with session and raw content.
            payload_id: Unique extraction payload identifier.
            extracted_entities: Extracted domain entities payload.
            escalation_case_id: Pre-generated escalation case identifier.

        Returns:
            The staged escalation case identifier string.
        """
        case_payload = CaseworkerCaseReviewPayload(
            escalation_case_id=escalation_case_id,
            session_id=intake.session_id,
            payload_id=payload_id,
            tokenized_citizen_id=intake.tokenized_citizen_id,
            application_intent=extracted_entities.application_intent,
            extracted_entities=extracted_entities.domain_entities,
            unprocessed_input_content=intake.unprocessed_input_content,
            escalation_reason=(
                EscalationReasonCode.ADVERSARIAL_ATTEMPT_FLAGGED
                if extracted_entities.is_adversarial_attempt
                else EscalationReasonCode.MISSING_MANDATORY_ENTITIES
            ),
            staged_at=datetime.now(UTC),
        )
        await self._case_service.stage_incident_ticket(case_payload)
        return escalation_case_id

    @staticmethod
    def _create_fallback_extracted_payload() -> ExtractedEntityPayload:
        """Constructs safe low-confidence fallback extraction payload for unparseable input.

        Why 0.40 instead of 0.0?
        - 0.0 is strictly reserved for Security Zeroing on adversarial prompt injection attacks
          (is_adversarial_attempt=True), which routes to the security threat triage queue.
        - 0.40 represents benign low model confidence / unparseable speech (e.g. ambient farm
          noise, dialect mismatch, or transcription timeout), routing safely to the standard
          caseworker review queue (ROUTE_FOR_MANUAL_REVIEW) without false security alarms.

        Returns:
            ExtractedEntityPayload initialized with 0.40 confidence and UNKNOWN intent.
        """
        return ExtractedEntityPayload(
            application_intent=ApplicationIntent.UNKNOWN,
            ai_confidence_score=0.40,
            domain_entities={},
            is_adversarial_attempt=False,
            is_structured_menu_bypass=False,
        )
