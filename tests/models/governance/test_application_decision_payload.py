from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from src.models.common import (
    DisbursementStatus,
    EligibilityStatus,
    GovernanceDecision,
)
from src.models.governance import ApplicationDecisionPayload


def test_governance_routing_approved_decision() -> None:
    payload = ApplicationDecisionPayload(
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
        ApplicationDecisionPayload(
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            ai_confidence_score=0.45,
            eligibility_status=EligibilityStatus.REQUIRES_REVIEW,
            governance_decision=GovernanceDecision.ROUTE_FOR_MANUAL_REVIEW,
            decided_at=datetime.now(UTC),
        )
    assert "escalation_case_id is required" in str(exc.value)


def test_governance_routing_manual_approve_with_review_notes() -> None:
    payload = ApplicationDecisionPayload(
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
        ApplicationDecisionPayload(
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


@pytest.mark.parametrize(
    ("decision", "case_id_allowed"),
    [
        (GovernanceDecision.AUTO_APPROVE, False),
        (GovernanceDecision.AUTOMATED_PAYOUT, False),
        (GovernanceDecision.AUTO_REJECT, False),
        (GovernanceDecision.MANUAL_APPROVE, True),
        (GovernanceDecision.MANUAL_REJECT, True),
        (GovernanceDecision.ROUTE_FOR_MANUAL_REVIEW, True),
        (GovernanceDecision.HUMAN_REVIEW, True),
        (GovernanceDecision.REQUEST_MORE_INFO, True),
    ],
)
def test_governance_decision_escalation_case_id_matrix(
    decision: GovernanceDecision, case_id_allowed: bool
) -> None:
    """Verifies escalation_case_id rules for every single GovernanceDecision enum member."""
    kwargs: dict[str, Any] = {
        "session_id": "sess_12345678",
        "payload_id": "550e8400-e29b-41d4-a716-446655440000",
        "ai_confidence_score": 0.85,
        "eligibility_status": EligibilityStatus.ELIGIBLE,
        "governance_decision": decision,
        "decided_at": datetime.now(UTC),
    }

    if decision in (
        GovernanceDecision.AUTO_APPROVE,
        GovernanceDecision.MANUAL_APPROVE,
        GovernanceDecision.AUTOMATED_PAYOUT,
    ):
        kwargs["disbursement_txn_id"] = "TXN-2026-123456"
        kwargs["disbursement_status"] = DisbursementStatus.PENDING

    if decision in (GovernanceDecision.AUTO_REJECT, GovernanceDecision.MANUAL_REJECT):
        kwargs["rejection_reason"] = "Scheme eligibility requirements not met"

    if case_id_allowed:
        kwargs["escalation_case_id"] = "SPP-CASE-2026-981245"
        payload = ApplicationDecisionPayload(**kwargs)
        assert payload.escalation_case_id == "SPP-CASE-2026-981245"
    else:
        payload = ApplicationDecisionPayload(**kwargs)
        assert payload.escalation_case_id is None

        # Verify passing escalation_case_id raises ValidationError
        kwargs["escalation_case_id"] = "SPP-CASE-2026-981245"
        with pytest.raises(ValidationError) as exc:
            ApplicationDecisionPayload(**kwargs)
        assert "escalation_case_id must be None" in str(exc.value)
