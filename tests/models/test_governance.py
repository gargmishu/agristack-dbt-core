from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.models.enums import (
    ApplicationIntent,
    DisbursementStatus,
    DomainEntityKey,
    EligibilityStatus,
    GovernanceDecision,
)
from src.models.governance import ExtractedEntityPayload, GovernanceRoutingPayload


def test_extracted_entity_adversarial_zeroing() -> None:
    payload = ExtractedEntityPayload(
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        ai_confidence_score=0.95,  # High score initially passed
        domain_entities={DomainEntityKey.DISTRICT: "Ambala"},
        is_adversarial_attempt=True,  # Injection flagged
    )
    # Validation must zero out confidence score and wipe entities
    assert payload.ai_confidence_score == 0.0
    assert payload.domain_entities == {}
    assert payload.is_adversarial_attempt is True


def test_governance_routing_approved_decision() -> None:
    payload = GovernanceRoutingPayload(
        channel_session_id="sess_12345678",
        payload_id="550e8400-e29b-41d4-a716-446655440000",
        ai_confidence_score=0.92,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        governance_decision=GovernanceDecision.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-987654",
        disbursement_status=DisbursementStatus.PENDING,
        decided_at_timestamp=datetime.now(UTC),
    )
    assert payload.governance_decision == GovernanceDecision.AUTO_APPROVE
    assert payload.disbursement_txn_id == "TXN-2026-987654"


def test_governance_routing_review_decision_missing_case_id() -> None:
    with pytest.raises(ValidationError) as exc:
        GovernanceRoutingPayload(
            channel_session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            ai_confidence_score=0.45,
            eligibility_status=EligibilityStatus.REQUIRES_REVIEW,
            governance_decision=GovernanceDecision.ROUTE_FOR_MANUAL_REVIEW,
            decided_at_timestamp=datetime.now(UTC),
        )
    assert "escalation_case_id is required" in str(exc.value)
