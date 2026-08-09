from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.data_models.common import (
    DisbursementStatus,
    EligibilityStatus,
    GovernanceAction,
)
from src.data_models.governance import GovernanceOutcomePayload


def test_governance_routing_approved_decision() -> None:
    payload = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="550e8400-e29b-41d4-a716-446655440000",
        ai_confidence_score=0.92,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-987654",
        disbursement_status=DisbursementStatus.PENDING,
        evaluated_at=datetime.now(UTC),
    )
    assert payload.governance_action == GovernanceAction.AUTO_APPROVE
    assert payload.disbursement_txn_id == "TXN-2026-987654"


def test_governance_routing_auto_approve_missing_txn_id() -> None:
    with pytest.raises(ValidationError, match="disbursement_txn_id is required"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            ai_confidence_score=0.92,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            governance_action=GovernanceAction.AUTO_APPROVE,
            disbursement_status=DisbursementStatus.PENDING,
            evaluated_at=datetime.now(UTC),
        )


def test_governance_routing_auto_approve_missing_status() -> None:
    with pytest.raises(ValidationError, match="disbursement_status is required"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            ai_confidence_score=0.92,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            governance_action=GovernanceAction.AUTO_APPROVE,
            disbursement_txn_id="TXN-2026-987654",
            evaluated_at=datetime.now(UTC),
        )


def test_governance_routing_auto_approve_with_rejection_reason() -> None:
    with pytest.raises(ValidationError, match="rejection_reason must be None"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            ai_confidence_score=0.92,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            governance_action=GovernanceAction.AUTO_APPROVE,
            disbursement_txn_id="TXN-2026-987654",
            disbursement_status=DisbursementStatus.PENDING,
            rejection_reason="Invalid reason on approve",
            evaluated_at=datetime.now(UTC),
        )


def test_governance_routing_auto_approve_with_escalation_case_id() -> None:
    with pytest.raises(ValidationError, match="escalation_case_id must be None"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            ai_confidence_score=0.92,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            governance_action=GovernanceAction.AUTO_APPROVE,
            disbursement_txn_id="TXN-2026-987654",
            disbursement_status=DisbursementStatus.PENDING,
            escalation_case_id="SPP-CASE-2026-981245",
            evaluated_at=datetime.now(UTC),
        )


def test_governance_routing_auto_approve_rejects_review_notes() -> None:
    with pytest.raises(ValidationError, match="review_notes must be None"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            ai_confidence_score=0.92,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            governance_action=GovernanceAction.AUTO_APPROVE,
            disbursement_txn_id="TXN-2026-987654",
            disbursement_status=DisbursementStatus.PENDING,
            review_notes="Invalid review note on automated decision",
            evaluated_at=datetime.now(UTC),
        )


def test_governance_routing_review_decision_missing_case_id() -> None:
    with pytest.raises(ValidationError, match="escalation_case_id is required"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            ai_confidence_score=0.45,
            eligibility_status=EligibilityStatus.REQUIRES_REVIEW,
            governance_action=GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
            evaluated_at=datetime.now(UTC),
        )


def test_governance_routing_review_decision_with_disbursement_keys() -> None:
    with pytest.raises(ValidationError, match="disbursement_txn_id must be None"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            escalation_case_id="SPP-CASE-2026-981245",
            ai_confidence_score=0.45,
            eligibility_status=EligibilityStatus.REQUIRES_REVIEW,
            governance_action=GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
            disbursement_txn_id="TXN-2026-987654",
            evaluated_at=datetime.now(UTC),
        )

    with pytest.raises(ValidationError, match="disbursement_status must be None"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            escalation_case_id="SPP-CASE-2026-981245",
            ai_confidence_score=0.45,
            eligibility_status=EligibilityStatus.REQUIRES_REVIEW,
            governance_action=GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
            disbursement_status=DisbursementStatus.PENDING,
            evaluated_at=datetime.now(UTC),
        )

    with pytest.raises(ValidationError, match="rejection_reason must be None"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            escalation_case_id="SPP-CASE-2026-981245",
            ai_confidence_score=0.45,
            eligibility_status=EligibilityStatus.REQUIRES_REVIEW,
            governance_action=GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
            rejection_reason="Some reason",
            evaluated_at=datetime.now(UTC),
        )

    with pytest.raises(ValidationError, match="review_notes must be None"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            escalation_case_id="SPP-CASE-2026-981245",
            ai_confidence_score=0.45,
            eligibility_status=EligibilityStatus.REQUIRES_REVIEW,
            governance_action=GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
            review_notes="Some notes",
            evaluated_at=datetime.now(UTC),
        )


def test_governance_routing_manual_approve_with_review_notes() -> None:
    payload = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="550e8400-e29b-41d4-a716-446655440000",
        escalation_case_id="SPP-CASE-2026-981245",
        ai_confidence_score=0.78,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        governance_action=GovernanceAction.MANUAL_APPROVE,
        disbursement_txn_id="TXN-2026-987654",
        disbursement_status=DisbursementStatus.PENDING,
        review_notes="Verified manual land deed document attached in tribunal appeal",
        evaluated_at=datetime.now(UTC),
    )
    assert payload.governance_action == GovernanceAction.MANUAL_APPROVE
    assert payload.escalation_case_id == "SPP-CASE-2026-981245"


def test_governance_routing_manual_approve_missing_fields() -> None:
    with pytest.raises(ValidationError, match="disbursement_txn_id is required"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            escalation_case_id="SPP-CASE-2026-981245",
            ai_confidence_score=0.78,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            governance_action=GovernanceAction.MANUAL_APPROVE,
            disbursement_status=DisbursementStatus.PENDING,
            review_notes="Note",
            evaluated_at=datetime.now(UTC),
        )

    with pytest.raises(ValidationError, match="disbursement_status is required"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            escalation_case_id="SPP-CASE-2026-981245",
            ai_confidence_score=0.78,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            governance_action=GovernanceAction.MANUAL_APPROVE,
            disbursement_txn_id="TXN-2026-987654",
            review_notes="Note",
            evaluated_at=datetime.now(UTC),
        )

    with pytest.raises(ValidationError, match="rejection_reason must be None"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            escalation_case_id="SPP-CASE-2026-981245",
            ai_confidence_score=0.78,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            governance_action=GovernanceAction.MANUAL_APPROVE,
            disbursement_txn_id="TXN-2026-987654",
            disbursement_status=DisbursementStatus.PENDING,
            rejection_reason="Invalid rejection reason",
            review_notes="Note",
            evaluated_at=datetime.now(UTC),
        )

    with pytest.raises(ValidationError, match="escalation_case_id is required"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            ai_confidence_score=0.78,
            eligibility_status=EligibilityStatus.ELIGIBLE,
            governance_action=GovernanceAction.MANUAL_APPROVE,
            disbursement_txn_id="TXN-2026-987654",
            disbursement_status=DisbursementStatus.PENDING,
            review_notes="Note",
            evaluated_at=datetime.now(UTC),
        )


def test_governance_routing_auto_reject_valid_and_invalid() -> None:
    valid = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="550e8400-e29b-41d4-a716-446655440000",
        ai_confidence_score=0.40,
        eligibility_status=EligibilityStatus.INELIGIBLE,
        governance_action=GovernanceAction.AUTO_REJECT,
        rejection_reason="Cadastral plot not registered",
        evaluated_at=datetime.now(UTC),
    )
    assert valid.governance_action == GovernanceAction.AUTO_REJECT

    with pytest.raises(ValidationError, match="rejection_reason is required"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            ai_confidence_score=0.40,
            eligibility_status=EligibilityStatus.INELIGIBLE,
            governance_action=GovernanceAction.AUTO_REJECT,
            evaluated_at=datetime.now(UTC),
        )

    with pytest.raises(ValidationError, match="disbursement_txn_id must be None"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            ai_confidence_score=0.40,
            eligibility_status=EligibilityStatus.INELIGIBLE,
            governance_action=GovernanceAction.AUTO_REJECT,
            rejection_reason="Reason",
            disbursement_txn_id="TXN-2026-987654",
            evaluated_at=datetime.now(UTC),
        )

    with pytest.raises(ValidationError, match="disbursement_status must be None"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            ai_confidence_score=0.40,
            eligibility_status=EligibilityStatus.INELIGIBLE,
            governance_action=GovernanceAction.AUTO_REJECT,
            rejection_reason="Reason",
            disbursement_status=DisbursementStatus.PENDING,
            evaluated_at=datetime.now(UTC),
        )

    with pytest.raises(ValidationError, match="escalation_case_id must be None"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            ai_confidence_score=0.40,
            eligibility_status=EligibilityStatus.INELIGIBLE,
            governance_action=GovernanceAction.AUTO_REJECT,
            rejection_reason="Reason",
            escalation_case_id="SPP-CASE-2026-981245",
            evaluated_at=datetime.now(UTC),
        )

    with pytest.raises(ValidationError, match="review_notes must be None"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            ai_confidence_score=0.40,
            eligibility_status=EligibilityStatus.INELIGIBLE,
            governance_action=GovernanceAction.AUTO_REJECT,
            rejection_reason="Reason",
            review_notes="Some review note",
            evaluated_at=datetime.now(UTC),
        )


def test_governance_routing_manual_reject_valid_and_invalid() -> None:
    valid = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="550e8400-e29b-41d4-a716-446655440000",
        escalation_case_id="SPP-CASE-2026-981245",
        ai_confidence_score=0.40,
        eligibility_status=EligibilityStatus.INELIGIBLE,
        governance_action=GovernanceAction.MANUAL_REJECT,
        rejection_reason="Land deed mismatch",
        review_notes="Officer verified records",
        evaluated_at=datetime.now(UTC),
    )
    assert valid.governance_action == GovernanceAction.MANUAL_REJECT

    with pytest.raises(ValidationError, match="rejection_reason is required"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            escalation_case_id="SPP-CASE-2026-981245",
            ai_confidence_score=0.40,
            eligibility_status=EligibilityStatus.INELIGIBLE,
            governance_action=GovernanceAction.MANUAL_REJECT,
            review_notes="Note",
            evaluated_at=datetime.now(UTC),
        )

    with pytest.raises(ValidationError, match="escalation_case_id is required"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            ai_confidence_score=0.40,
            eligibility_status=EligibilityStatus.INELIGIBLE,
            governance_action=GovernanceAction.MANUAL_REJECT,
            rejection_reason="Reason",
            review_notes="Note",
            evaluated_at=datetime.now(UTC),
        )

    with pytest.raises(ValidationError, match="disbursement_txn_id must be None"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            escalation_case_id="SPP-CASE-2026-981245",
            ai_confidence_score=0.40,
            eligibility_status=EligibilityStatus.INELIGIBLE,
            governance_action=GovernanceAction.MANUAL_REJECT,
            rejection_reason="Reason",
            review_notes="Note",
            disbursement_txn_id="TXN-2026-987654",
            evaluated_at=datetime.now(UTC),
        )

    with pytest.raises(ValidationError, match="disbursement_status must be None"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            escalation_case_id="SPP-CASE-2026-981245",
            ai_confidence_score=0.40,
            eligibility_status=EligibilityStatus.INELIGIBLE,
            governance_action=GovernanceAction.MANUAL_REJECT,
            rejection_reason="Reason",
            review_notes="Note",
            disbursement_status=DisbursementStatus.PENDING,
            evaluated_at=datetime.now(UTC),
        )

    with pytest.raises(ValidationError, match="review_notes cannot be empty or whitespace"):
        GovernanceOutcomePayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            escalation_case_id="SPP-CASE-2026-981245",
            ai_confidence_score=0.40,
            eligibility_status=EligibilityStatus.INELIGIBLE,
            governance_action=GovernanceAction.MANUAL_REJECT,
            rejection_reason="Reason",
            review_notes="   ",
            evaluated_at=datetime.now(UTC),
        )
