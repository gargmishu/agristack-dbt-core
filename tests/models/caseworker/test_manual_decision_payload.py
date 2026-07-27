from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.models.caseworker import CaseworkerManualDecisionPayload
from src.models.common import GovernanceDecision


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
