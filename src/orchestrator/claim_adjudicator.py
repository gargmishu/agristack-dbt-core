"""Layer 4 Governance Engine: Claim Adjudicator (Gate 3 Decision Matrix).

Evaluates citizen claims against AI confidence thresholds, sovereign identity records,
cadastral landholdings, and anti-double-dipping ledgers to assign authoritative
governance determinations (AUTO_APPROVE, AUTO_REJECT, or ROUTE_FOR_MANUAL_REVIEW).

See: decisions/step3.3_layer4_orchestrator_brain.md (Section 4: Gate 3 Matrix)
See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.1 & 4.1)
See: decisions/step2.0_canonical_domain_schemas.md (Section 4.3)
See: roadmap.md (Phase 3 Step 3.3 Layer 4 Governance Router)
"""

import logging
import secrets
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
    ClaimEvaluationPayload,
    GovernanceOutcomePayload,
)
from src.services.dpi import (
    AgriRegistryService,
    IdentityVerificationService,
)

logger = logging.getLogger(__name__)

_AUTO_APPROVE_CONFIDENCE_THRESHOLD: Final[float] = 0.85


class ClaimAdjudicator:
    """Evaluates governance decision matrix based on confidence and registry eligibility.

    Coordinates eligibility verification across sovereign identity and land registry clients,
    generating authoritative `GovernanceOutcomePayload` determinations.

    Decision Rules:
    - Auto-Approval (`AUTO_APPROVE`): High confidence (>= 0.85), verified identity, eligible
      land parcel, and no prior claim in the active season.
    - Escalation (`ROUTE_FOR_MANUAL_REVIEW`): Low/moderate confidence (< 0.85) or
      adversarial prompt injection attempts.
    - Rejection (`AUTO_REJECT`): Duplicate active-season claim, unverified identity token,
      or cadastral land record mismatch.

    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.1 & 4.1)
    """

    def __init__(
        self,
        identity_service: IdentityVerificationService | None = None,
        agri_service: AgriRegistryService | None = None,
    ) -> None:
        """Initializes ClaimAdjudicator with required sovereign registry services.

        Args:
            identity_service: Identity verification client (defaults to standard mock).
            agri_service: Cadastral land registry client (defaults to standard mock).
        """
        self._identity_service = identity_service or IdentityVerificationService()
        self._agri_service = agri_service or AgriRegistryService()

    async def evaluate_claim(
        self,
        payload: ClaimEvaluationPayload,
    ) -> GovernanceOutcomePayload:
        """Evaluates extracted entities and citizen credentials against Gate 3 rules matrix.

        Args:
            payload: Validated ClaimEvaluationPayload instance.

        Returns:
            Fully validated GovernanceOutcomePayload representing the adjudication outcome.
        """
        ledger = payload.approved_payouts_ledger or set()
        short_id = f"{secrets.randbelow(900000) + 100000:06d}"
        now = datetime.now(UTC)
        extracted = payload.extracted_payload

        # 1. Security Check: Adversarial Prompt Injection Zeroing Invariant
        if extracted.is_adversarial_attempt or extracted.ai_confidence_score == 0.0:
            logger.warning(
                "Adversarial attempt or zero-confidence claim flagged for session=%s; "
                "routing to caseworker review",
                payload.session_id,
            )
            return GovernanceOutcomePayload(
                session_id=payload.session_id,
                payload_id=payload.payload_id,
                ai_confidence_score=0.0,
                eligibility_status=EligibilityStatus.REQUIRES_REVIEW,
                governance_action=GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
                escalation_case_id=f"SPP-CASE-2026-{short_id}",
                evaluated_at=now,
            )

        # 2. Anti-Double-Dipping Ledger Invariant
        if (payload.tokenized_citizen_id, payload.active_season) in ledger:
            logger.warning(
                "Duplicate active claim detected for citizen=%s season=%s; rejecting",
                payload.tokenized_citizen_id[:16],
                payload.active_season,
            )
            return GovernanceOutcomePayload(
                session_id=payload.session_id,
                payload_id=payload.payload_id,
                ai_confidence_score=extracted.ai_confidence_score,
                eligibility_status=EligibilityStatus.INELIGIBLE,
                governance_action=GovernanceAction.AUTO_REJECT,
                rejection_reason=RejectionReasonCode.DUPLICATE_CLAIM_ACTIVE_SEASON,
                evaluated_at=now,
            )

        # 3. Sovereign Identity Registry Verification
        is_identity_verified = await self._identity_service.verify_identity_token(
            payload.tokenized_citizen_id
        )
        if not is_identity_verified:
            logger.warning(
                "Unverified identity token for session=%s; rejecting",
                payload.session_id,
            )
            return GovernanceOutcomePayload(
                session_id=payload.session_id,
                payload_id=payload.payload_id,
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
            payload.tokenized_citizen_id, survey_number
        )
        if not is_land_verified:
            logger.warning(
                "Cadastral land record mismatch for survey=%s citizen=%s; rejecting",
                survey_number,
                payload.tokenized_citizen_id[:16],
            )
            return GovernanceOutcomePayload(
                session_id=payload.session_id,
                payload_id=payload.payload_id,
                ai_confidence_score=extracted.ai_confidence_score,
                eligibility_status=EligibilityStatus.INELIGIBLE,
                governance_action=GovernanceAction.AUTO_REJECT,
                rejection_reason=RejectionReasonCode.LAND_RECORD_NOT_FOUND,
                evaluated_at=now,
            )

        # 5. Threshold Gate: Confidence Score Evaluation (>= _AUTO_APPROVE_CONFIDENCE_THRESHOLD)
        if extracted.ai_confidence_score >= _AUTO_APPROVE_CONFIDENCE_THRESHOLD:
            logger.info(
                "Straight-through automated payout approved for session=%s score=%.2f",
                payload.session_id,
                extracted.ai_confidence_score,
            )
            return GovernanceOutcomePayload(
                session_id=payload.session_id,
                payload_id=payload.payload_id,
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
            payload.session_id,
        )
        return GovernanceOutcomePayload(
            session_id=payload.session_id,
            payload_id=payload.payload_id,
            ai_confidence_score=extracted.ai_confidence_score,
            eligibility_status=EligibilityStatus.REQUIRES_REVIEW,
            governance_action=GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
            escalation_case_id=f"SPP-CASE-2026-{short_id}",
            evaluated_at=now,
        )
