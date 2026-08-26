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
    DomainEntityKey,
    EligibilityStatus,
    EscalationReasonCode,
    GovernanceAction,
    SessionId,
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
        governance_outcome: Governance adjudication verdict.
        extracted_entities: Extracted domain parameter dictionary.
        requires_reprompt: True if mandatory entity completeness failed and requires citizen
            clarification.
        reprompt_message: Clarification prompt message if reprompt is required.
        disbursement_callback: Payment clearing callback receipt if automated payout was
            initiated.
        caseworker_ticket_id: Escalation ticket ID (`SPP-CASE-YYYY-XXXXXX`) if staged for review.

    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 2.1)
    """

    governance_outcome: GovernanceOutcomePayload
    extracted_entities: ExtractedEntityPayload
    requires_reprompt: bool = False
    reprompt_message: str | None = None
    disbursement_callback: DisbursementCallbackPayload | None = None
    caseworker_ticket_id: str | None = None

    @property
    def session_id(self) -> SessionId:
        """Primary session tracking identifier."""
        return self.governance_outcome.session_id

    @property
    def application_intent(self) -> ApplicationIntent:
        """Classified citizen intent driving workflow routing."""
        return self.extracted_entities.application_intent


class ClaimOrchestrator:
    """Claim orchestrator governing claim processing workflows across governance gates.

    Coordinates end-to-end processing across completeness validation, policy adjudication,
    and post-decision disbursement/caseworker staging:
    - Claim Completeness Validation (Gate 2): Validates mandatory domain entity completeness
      and manages multi-turn conversational re-prompt loops.
    - Governance Adjudication (Gate 3): Evaluates eligibility rules and routes to auto-payout,
      review, or rejection via the adjudication decision matrix.

    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 2.1)
    """

    def __init__(
        self,
        claim_adjudicator: ClaimAdjudicator | None = None,
        case_management_service: CaseManagementService | None = None,
        payment_rail_service: PaymentRailService | None = None,
    ) -> None:
        """Initializes the claim orchestrator with required governance and DPI dependencies."""
        self._claim_adjudicator = claim_adjudicator or ClaimAdjudicator()
        self._case_service = case_management_service or CaseManagementService()
        self._payment_rail = payment_rail_service or PaymentRailService()

    # -------------------------------------------------------------------------
    # Primary Public Workflow Entrypoint
    # -------------------------------------------------------------------------

    async def execute_orchestration_cycle(
        self,
        intake: PublicAgentStandardizedIntakePayload,
        extracted_entities: ExtractedEntityPayload,
        attempt_count: int = 1,
        approved_payouts_ledger: set[tuple[str, str]] | None = None,
        active_season: CropSeason = "KHARIF-2026",
    ) -> OrchestrationExecutionResult:
        """Executes complete end-to-end orchestration pipeline across governance gates.

        Args:
            intake: Validated PublicAgentStandardizedIntakePayload from Layer 3.
            extracted_entities: Structured ExtractedEntityPayload from Layer 3 Entity Extractor.
            attempt_count: Current attempt count for multi-turn conversational loop.
            approved_payouts_ledger: Set of approved (citizen_token, season) claims.
            active_season: Active welfare scheme season identifier.

        Returns:
            OrchestrationExecutionResult with finalized governance action, tracking IDs,
            and payment/caseworker staging outcomes.
        """
        session_id = intake.session_id
        payload_id = f"ext-{uuid.uuid4().hex[:8]}"

        # Gate 2: Intake Completeness & Reprompt Validation
        missing_entities = self._check_claim_completeness(
            extracted_entities, attempt_count=attempt_count
        )
        if missing_entities:
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
        disbursement_callback: DisbursementCallbackPayload | None = None
        staged_case_id: str | None = None
        if governance_outcome.governance_action.is_approval:
            disbursement_callback = await self._payment_rail.initiate_disbursement(
                governance_outcome
            )
        elif (
            governance_outcome.governance_action.is_review and governance_outcome.escalation_case_id
        ):
            staged_case_id = await self._stage_caseworker_ticket(
                intake=intake,
                payload_id=payload_id,
                extracted_entities=extracted_entities,
                escalation_case_id=governance_outcome.escalation_case_id,
            )

        return OrchestrationExecutionResult(
            governance_outcome=governance_outcome,
            extracted_entities=extracted_entities,
            requires_reprompt=False,
            disbursement_callback=disbursement_callback,
            caseworker_ticket_id=staged_case_id,
        )

    # -------------------------------------------------------------------------
    # Private Helpers (Strictly at Bottom)
    # -------------------------------------------------------------------------

    def _check_claim_completeness(
        self,
        extracted: ExtractedEntityPayload,
        attempt_count: int = 1,
    ) -> list[str]:
        """Gate 2: Intake & Intent Validation Gate.

        Checks mandatory domain entities for subsidy claims and manages multi-turn
        conversational re-prompt loops (up to 3 attempts).

        Args:
            extracted: ExtractedEntityPayload output from Gate 1.
            attempt_count: Current citizen interaction attempt counter (1 to 3).

        Returns:
            List of missing mandatory entity field names requiring reprompt, or empty list if
            complete or maximum attempts reached.
        """
        if extracted.is_adversarial_attempt or extracted.is_structured_menu_bypass:
            return []

        if extracted.application_intent != ApplicationIntent.APPLY_SUBSIDY:
            return []

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
            return missing_entities

        return []

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
        missing_fields_text = ", ".join(missing_entities)
        reprompt_message = (
            f"Kripya apne aavedan ke liye nimnlikhit jankari pradan karein: {missing_fields_text}"
        )
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
            governance_outcome=reprompt_outcome,
            extracted_entities=extracted_entities,
            requires_reprompt=True,
            reprompt_message=reprompt_message,
        )

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
