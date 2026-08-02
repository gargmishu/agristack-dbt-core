from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.data_models.common import (
    DisbursementStatus,
    EligibilityStatus,
    GovernanceDecision,
)
from src.data_models.governance import GovernanceOutcomePayload


def test_governance_routing_approved_decision() -> None:
    payload = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="550e8400-e29b-41d4-a716-446655440000",
        ai_confidence_score=0.92,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        governance_decision=GovernanceDecision.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-987654",
        disbursement_status=DisbursementStatus.PENDING,
        decided_at=datetime.now(UTC),
    )
    assert payload.governance_decision == GovernanceDecision.AUTO_APPROVE
    assert payload.disbursement_txn_id == "TXN-2026-987654"


def test_governance_routing_review_decision_missing_case_id() -> None:
    with pytest.raises(ValidationError) as exc:
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            ai_confidence_score=0.45,
            eligibility_status=EligibilityStatus.REQUIRES_REVIEW,
            governance_decision=GovernanceDecision.ROUTE_FOR_MANUAL_REVIEW,
            decided_at=datetime.now(UTC),
        )
    assert "escalation_case_id is required" in str(exc.value)


def test_governance_routing_manual_approve_with_review_notes() -> None:
    payload = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="550e8400-e29b-41d4-a716-446655440000",
        escalation_case_id="SPP-CASE-2026-981245",
        ai_confidence_score=0.78,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        governance_decision=GovernanceDecision.MANUAL_APPROVE,
        disbursement_txn_id="TXN-2026-987654",
        disbursement_status=DisbursementStatus.PENDING,
        review_notes="Verified manual land deed document attached in tribunal appeal",
        decided_at=datetime.now(UTC),
    )
    assert payload.governance_decision == GovernanceDecision.MANUAL_APPROVE
    assert payload.escalation_case_id == "SPP-CASE-2026-981245"
    assert payload.review_notes == "Verified manual land deed document attached in tribunal appeal"


def test_governance_routing_manual_approve_missing_case_id() -> None:
    with pytest.raises(ValidationError) as exc:
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            ai_confidence_score=0.78,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            governance_decision=GovernanceDecision.MANUAL_APPROVE,
            disbursement_txn_id="TXN-2026-987654",
            disbursement_status=DisbursementStatus.PENDING,
            decided_at=datetime.now(UTC),
        )
    assert "escalation_case_id is required for MANUAL_APPROVE" in str(exc.value)


def test_governance_routing_auto_approve_rejects_review_notes() -> None:
    with pytest.raises(ValidationError) as exc:
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            ai_confidence_score=0.92,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            governance_decision=GovernanceDecision.AUTO_APPROVE,
            disbursement_txn_id="TXN-2026-987654",
            disbursement_status=DisbursementStatus.PENDING,
            review_notes="Invalid review note on automated decision",
            decided_at=datetime.now(UTC),
        )
    assert "review_notes must be None for decision AUTO_APPROVE" in str(exc.value)


def test_governance_routing_manual_approve_rejects_empty_review_notes() -> None:
    with pytest.raises(ValidationError) as exc:
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            escalation_case_id="SPP-CASE-2026-981245",
            ai_confidence_score=0.78,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            governance_decision=GovernanceDecision.MANUAL_APPROVE,
            disbursement_txn_id="TXN-2026-987654",
            disbursement_status=DisbursementStatus.PENDING,
            review_notes="   ",
            decided_at=datetime.now(UTC),
        )
    assert "review_notes cannot be empty or whitespace" in str(exc.value)


def test_governance_routing_manual_approve_missing_review_notes() -> None:
    with pytest.raises(ValidationError) as exc:
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            escalation_case_id="SPP-CASE-2026-981245",
            ai_confidence_score=0.78,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            governance_decision=GovernanceDecision.MANUAL_APPROVE,
            disbursement_txn_id="TXN-2026-987654",
            disbursement_status=DisbursementStatus.PENDING,
            review_notes=None,
            decided_at=datetime.now(UTC),
        )
    assert "review_notes is required for MANUAL_APPROVE" in str(exc.value)


def test_governance_routing_manual_reject_missing_review_notes() -> None:
    with pytest.raises(ValidationError) as exc:
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            escalation_case_id="SPP-CASE-2026-981245",
            ai_confidence_score=0.40,
            eligibility_status=EligibilityStatus.INELIGIBLE,
            governance_decision=GovernanceDecision.MANUAL_REJECT,
            rejection_reason="Land deed mismatch",
            review_notes=None,
            decided_at=datetime.now(UTC),
        )
    assert "review_notes is required for MANUAL_REJECT" in str(exc.value)
