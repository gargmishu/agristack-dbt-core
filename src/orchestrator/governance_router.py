"""Layer 4 Governance Engine: Decision Matrix Router.

Evaluates AI extraction confidence scores, landholding cross-match eligibility,
and anti-double-dipping ledgers to assign automated decisions:
1. AUTOMATED_PAYOUT / AUTO_APPROVE (High confidence >=0.85 + Eligible + No active payout)
2. HUMAN_REVIEW / ROUTE_FOR_MANUAL_REVIEW (Low confidence <0.85 or entity discrepancies)
3. AUTO_REJECT (Ineligible land records or double-dipping detection)

See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.1)
See: decisions/step2.0_canonical_domain_schemas.md (Section 4.3)
See: roadmap.md (Phase 3 Step 3.3 Layer 4 Governance Router)
"""

import logging
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Final

from src.data_models.common import (
    DisbursementStatus,
    DomainEntityKey,
    EligibilityStatus,
    GovernanceAction,
    RejectionReasonCode,
)
from src.data_models.governance import (
    ExtractedEntityPayload,
    GovernanceOutcomePayload,
)
from src.services.dpi import (
    AgriRegistryService,
    IdentityVerificationService,
)

logger = logging.getLogger(__name__)

AUTO_APPROVE_CONFIDENCE_THRESHOLD: Final[float] = 0.85
DEFAULT_ACTIVE_SEASON: Final[str] = "KHARIF-2026"


@dataclass(frozen=True)
class ClaimEvaluationContext:
    """Context container for Gate 3 governance claim evaluation."""

    session_id: str
    payload_id: str
    tokenized_citizen_id: str
    extracted_payload: ExtractedEntityPayload
    active_season: str = DEFAULT_ACTIVE_SEASON
    approved_payouts_ledger: set[tuple[str, str]] = field(default_factory=set)


class GovernanceRouter:
    """Evaluates governance decision matrix based on confidence and registry eligibility.

    Decouples governance adjudication from financial execution by assigning an idempotent
    disbursement transaction key (`disbursement_txn_id`) and status `PENDING` upon approval,
    enabling asynchronous clearing over sovereign payment rails.

    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.1 & 4.1)
    See: decisions/step3.3_layer4_orchestrator_brain.md
    """

    def __init__(
        self,
        identity_service: IdentityVerificationService | None = None,
        agri_service: AgriRegistryService | None = None,
    ) -> None:
        """Initializes GovernanceRouter with required sovereign registry services.

        Args:
            identity_service: Identity verification client (defaults to standard mock).
            agri_service: Cadastral land registry client (defaults to standard mock).
        """
        self._identity_service = identity_service or IdentityVerificationService()
        self._agri_service = agri_service or AgriRegistryService()

    @classmethod
    def from_default(cls) -> "GovernanceRouter":
        """Factory method to construct GovernanceRouter with default registry services."""
        return cls(
            identity_service=IdentityVerificationService(),
            agri_service=AgriRegistryService(),
        )

    async def evaluate_claim(
        self,
        context: ClaimEvaluationContext,
    ) -> GovernanceOutcomePayload:
        """Evaluates extracted entities and citizen credentials against Gate 3 rules matrix.

        Args:
            context: Validated ClaimEvaluationContext instance.

        Returns:
            Fully validated GovernanceOutcomePayload representing the adjudication outcome.
        """
        ledger = context.approved_payouts_ledger or set()
        short_id = f"{secrets.randbelow(900000) + 100000:06d}"
        now = datetime.now(UTC)
        extracted = context.extracted_payload

        # 1. Security Check: Adversarial Prompt Injection Zeroing Invariant
        if extracted.is_adversarial_attempt or extracted.ai_confidence_score == 0.0:
            logger.warning(
                "Adversarial attempt or zero-confidence claim flagged for session=%s; "
                "routing to caseworker review",
                context.session_id,
            )
            return GovernanceOutcomePayload(
                session_id=context.session_id,
                payload_id=context.payload_id,
                ai_confidence_score=0.0,
                eligibility_status=EligibilityStatus.REQUIRES_REVIEW,
                governance_action=GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
                escalation_case_id=f"SPP-CASE-2026-{short_id}",
                evaluated_at=now,
            )

        # 2. Anti-Double-Dipping Ledger Invariant
        if (context.tokenized_citizen_id, context.active_season) in ledger:
            logger.warning(
                "Duplicate active claim detected for citizen=%s season=%s; rejecting",
                context.tokenized_citizen_id[:16],
                context.active_season,
            )
            return GovernanceOutcomePayload(
                session_id=context.session_id,
                payload_id=context.payload_id,
                ai_confidence_score=extracted.ai_confidence_score,
                eligibility_status=EligibilityStatus.INELIGIBLE,
                governance_action=GovernanceAction.AUTO_REJECT,
                rejection_reason=RejectionReasonCode.DUPLICATE_CLAIM_ACTIVE_SEASON,
                evaluated_at=now,
            )

        # 3. Sovereign Identity Registry Verification
        is_identity_verified = await self._identity_service.verify_identity_token(
            context.tokenized_citizen_id
        )
        if not is_identity_verified:
            logger.warning(
                "Unverified identity token for session=%s; rejecting",
                context.session_id,
            )
            return GovernanceOutcomePayload(
                session_id=context.session_id,
                payload_id=context.payload_id,
                ai_confidence_score=extracted.ai_confidence_score,
                eligibility_status=EligibilityStatus.INELIGIBLE,
                governance_action=GovernanceAction.AUTO_REJECT,
                rejection_reason=RejectionReasonCode.IDENTITY_NOT_VERIFIED,
                evaluated_at=now,
            )

        # 4. Cadastral Land & Crop Record Cross-Matching
        survey_number = str(
            extracted.domain_entities.get(DomainEntityKey.SURVEY_NUMBER, "LAND-REC-1002")
        )
        is_land_verified = await self._agri_service.verify_land_record(
            context.tokenized_citizen_id, survey_number
        )
        if not is_land_verified:
            logger.warning(
                "Cadastral land record mismatch for survey=%s citizen=%s; rejecting",
                survey_number,
                context.tokenized_citizen_id[:16],
            )
            return GovernanceOutcomePayload(
                session_id=context.session_id,
                payload_id=context.payload_id,
                ai_confidence_score=extracted.ai_confidence_score,
                eligibility_status=EligibilityStatus.INELIGIBLE,
                governance_action=GovernanceAction.AUTO_REJECT,
                rejection_reason=RejectionReasonCode.LAND_RECORD_NOT_FOUND,
                evaluated_at=now,
            )

        # 5. Threshold Gate: Confidence Score Evaluation (>= AUTO_APPROVE_CONFIDENCE_THRESHOLD)
        if extracted.ai_confidence_score >= AUTO_APPROVE_CONFIDENCE_THRESHOLD:
            logger.info(
                "Straight-through automated payout approved for session=%s score=%.2f",
                context.session_id,
                extracted.ai_confidence_score,
            )
            return GovernanceOutcomePayload(
                session_id=context.session_id,
                payload_id=context.payload_id,
                ai_confidence_score=extracted.ai_confidence_score,
                eligibility_status=EligibilityStatus.ELIGIBLE,
                governance_action=GovernanceAction.AUTO_APPROVE,
                disbursement_txn_id=f"TXN-2026-{short_id}",
                disbursement_status=DisbursementStatus.PENDING,
                evaluated_at=now,
            )

        logger.info(
            "Low confidence claim score=%.2f for session=%s; routing to caseworker",
            extracted.ai_confidence_score,
            context.session_id,
        )
        return GovernanceOutcomePayload(
            session_id=context.session_id,
            payload_id=context.payload_id,
            ai_confidence_score=extracted.ai_confidence_score,
            eligibility_status=EligibilityStatus.REQUIRES_REVIEW,
            governance_action=GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
            escalation_case_id=f"SPP-CASE-2026-{short_id}",
            evaluated_at=now,
        )

    async def route_governance_outcome(
        self, payload: GovernanceOutcomePayload
    ) -> GovernanceOutcomePayload:
        """Routes finalized governance outcome through policy logging.

        Args:
            payload: Validated GovernanceOutcomePayload instance.

        Returns:
            GovernanceOutcomePayload with finalized governance action and tracking keys.
        """
        logger.info(
            "Routing governance outcome for session=%s, action=%s, confidence=%.2f",
            payload.session_id,
            payload.governance_action,
            payload.ai_confidence_score,
        )
        return payload
