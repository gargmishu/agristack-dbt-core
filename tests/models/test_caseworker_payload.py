from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.models.caseworker import (
    CaseworkerCaseReviewPayload,
    CaseworkerManualDecisionPayload,
)
from src.models.enums import ApplicationIntent, GovernanceDecision


def test_case_review_payload_valid() -> None:
    payload = CaseworkerCaseReviewPayload(
        escalation_case_id="SPP-CASE-2026-981245",
        channel_session_id="sess_12345678",
        payload_id="550e8400-e29b-41d4-a716-446655440000",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        unprocessed_input_content="Voice note transcript",
        escalation_reason="LOW_CONFIDENCE",
        staged_at_timestamp=datetime.now(UTC),
    )
    assert payload.escalation_case_id == "SPP-CASE-2026-981245"


def test_caseworker_manual_decision_valid_approve() -> None:
    payload = CaseworkerManualDecisionPayload(
        escalation_case_id="SPP-CASE-2026-981245",
        reviewer_id="OFFICER-991",
        governance_decision=GovernanceDecision.MANUAL_APPROVE,
        review_notes="Verified land record document manually",
        approved_amount=5000.0,  # noqa: PLR2004
        decision_timestamp=datetime.now(UTC),
    )
    assert payload.governance_decision == GovernanceDecision.MANUAL_APPROVE
    assert payload.approved_amount == 5000.0  # noqa: PLR2004


def test_caseworker_manual_decision_invalid_type() -> None:
    with pytest.raises(ValidationError) as exc:
        CaseworkerManualDecisionPayload(
            escalation_case_id="SPP-CASE-2026-981245",
            reviewer_id="OFFICER-991",
            governance_decision=GovernanceDecision.AUTO_APPROVE,  # Automated decision not permitted
            review_notes="Notes",
            approved_amount=5000.0,  # noqa: PLR2004
            decision_timestamp=datetime.now(UTC),
        )
    assert "must be MANUAL_APPROVE or MANUAL_REJECT" in str(exc.value)
