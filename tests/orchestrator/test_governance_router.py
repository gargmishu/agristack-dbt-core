from datetime import UTC, datetime

import pytest

from src.data_models.common import (
    DisbursementStatus,
    EligibilityStatus,
    GovernanceAction,
)
from src.data_models.governance import GovernanceOutcomePayload
from src.orchestrator.governance_router import GovernanceRouter


@pytest.mark.asyncio
async def test_governance_router_auto_approve() -> None:
    router = GovernanceRouter()
    payload = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="ext_12345678",
        ai_confidence_score=0.96,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-987654",
        disbursement_status=DisbursementStatus.PENDING,
        evaluated_at=datetime.now(UTC),
    )

    result = await router.route_governance_outcome(payload)
    assert result.governance_action == GovernanceAction.AUTO_APPROVE


@pytest.mark.asyncio
async def test_governance_router_auto_reject() -> None:
    router = GovernanceRouter()
    payload = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="ext_12345678",
        ai_confidence_score=0.40,
        eligibility_status=EligibilityStatus.INELIGIBLE,
        governance_action=GovernanceAction.AUTO_REJECT,
        rejection_reason="Cadastral plot not registered for seasonal crop",
        evaluated_at=datetime.now(UTC),
    )
    result = await router.route_governance_outcome(payload)
    assert result.governance_action == GovernanceAction.AUTO_REJECT


@pytest.mark.asyncio
async def test_governance_router_manual_review_routing() -> None:
    router = GovernanceRouter()
    payload = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="ext_12345678",
        ai_confidence_score=0.72,
        eligibility_status=EligibilityStatus.REQUIRES_REVIEW,
        governance_action=GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
        escalation_case_id="SPP-CASE-2026-100200",
        evaluated_at=datetime.now(UTC),
    )
    result = await router.route_governance_outcome(payload)
    assert result.governance_action == GovernanceAction.ROUTE_FOR_MANUAL_REVIEW


@pytest.mark.asyncio
async def test_governance_router_manual_approve() -> None:
    router = GovernanceRouter()
    payload = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="ext_12345678",
        ai_confidence_score=0.75,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        governance_action=GovernanceAction.MANUAL_APPROVE,
        disbursement_txn_id="TXN-2026-MANUAL-001",
        disbursement_status=DisbursementStatus.PENDING,
        escalation_case_id="SPP-CASE-2026-100200",
        review_notes="Officer verified field report",
        evaluated_at=datetime.now(UTC),
    )
    result = await router.route_governance_outcome(payload)
    assert result.governance_action == GovernanceAction.MANUAL_APPROVE


@pytest.mark.asyncio
async def test_governance_router_manual_reject() -> None:
    router = GovernanceRouter()
    payload = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="ext_12345678",
        ai_confidence_score=0.55,
        eligibility_status=EligibilityStatus.INELIGIBLE,
        governance_action=GovernanceAction.MANUAL_REJECT,
        escalation_case_id="SPP-CASE-2026-100200",
        rejection_reason="Ineligible crop acreage under state relief rules",
        review_notes="Officer reviewed satellite and revenue record mismatch",
        evaluated_at=datetime.now(UTC),
    )
    result = await router.route_governance_outcome(payload)
    assert result.governance_action == GovernanceAction.MANUAL_REJECT


@pytest.mark.asyncio
async def test_governance_router_request_more_info() -> None:
    router = GovernanceRouter()
    payload = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="ext_12345678",
        ai_confidence_score=0.68,
        eligibility_status=EligibilityStatus.REQUIRES_REVIEW,
        governance_action=GovernanceAction.REQUEST_MORE_INFO,
        escalation_case_id="SPP-CASE-2026-100200",
        evaluated_at=datetime.now(UTC),
    )
    result = await router.route_governance_outcome(payload)
    assert result.governance_action == GovernanceAction.REQUEST_MORE_INFO
