from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.data_models.caseworker import CaseworkerReviewOutcomePayload
from src.data_models.common import GovernanceDecision


def test_caseworker_review_outcome_valid_approve() -> None:
    payload = CaseworkerReviewOutcomePayload(
        escalation_case_id="SPP-CASE-2026-981245",
        reviewer_id="OFFICER-991",
        governance_decision=GovernanceDecision.MANUAL_APPROVE,
        review_notes="Verified land record document manually",
        approved_amount=5000.0,  # noqa: PLR2004
        decided_at=datetime.now(UTC),
    )
    assert payload.governance_decision == GovernanceDecision.MANUAL_APPROVE
    assert payload.approved_amount == 5000.0  # noqa: PLR2004


def test_caseworker_review_outcome_valid_request_more_info() -> None:
    payload = CaseworkerReviewOutcomePayload(
        escalation_case_id="SPP-CASE-2026-981245",
        reviewer_id="OFFICER-991",
        governance_decision=GovernanceDecision.REQUEST_MORE_INFO,
        review_notes="Please upload a clearer scan of the land deed document",
        decided_at=datetime.now(UTC),
    )
    assert payload.governance_decision == GovernanceDecision.REQUEST_MORE_INFO
    assert payload.approved_amount is None
    assert payload.rejection_reason is None


def test_caseworker_review_outcome_invalid_type() -> None:
    with pytest.raises(ValidationError) as exc:
        CaseworkerReviewOutcomePayload(
            escalation_case_id="SPP-CASE-2026-981245",
            reviewer_id="OFFICER-991",
            governance_decision=GovernanceDecision.AUTO_APPROVE,  # Automated decision not permitted
            review_notes="Notes",
            approved_amount=5000.0,  # noqa: PLR2004
            decided_at=datetime.now(UTC),
        )
    assert "must be MANUAL_APPROVE, MANUAL_REJECT, or REQUEST_MORE_INFO" in str(exc.value)


def test_caseworker_review_outcome_empty_review_notes() -> None:
    with pytest.raises(ValidationError) as exc:
        CaseworkerReviewOutcomePayload(
            escalation_case_id="SPP-CASE-2026-981245",
            reviewer_id="OFFICER-991",
            governance_decision=GovernanceDecision.MANUAL_APPROVE,
            review_notes="      ",  # 6 spaces
            approved_amount=5000.0,  # noqa: PLR2004
            decided_at=datetime.now(UTC),
        )
    assert "String should have at least 5 characters" in str(exc.value)
