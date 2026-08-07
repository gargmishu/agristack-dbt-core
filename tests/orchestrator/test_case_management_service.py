"""Unit tests for CaseManagementService in Layer 4 Orchestrator."""

from datetime import UTC, datetime

import pytest

from src.data_models.caseworker import CaseworkerReviewOutcomePayload
from src.data_models.common import GovernanceAction
from src.orchestrator import CaseManagementService


@pytest.mark.asyncio
async def test_case_management_process_officer_review() -> None:
    service = CaseManagementService()
    review = CaseworkerReviewOutcomePayload(
        escalation_case_id="SPP-CASE-2026-100200",
        reviewer_id="OFFICER-UUID-12345",
        governance_action=GovernanceAction.MANUAL_APPROVE,
        review_notes="Field inspection verified land ownership",
        approved_amount=5000.0,
        rejection_reason=None,
        reviewed_at=datetime.now(UTC),
    )
    processed = await service.process_officer_review(review)
    assert processed is True


@pytest.mark.asyncio
async def test_case_management_resolve_citizen_clarification() -> None:
    service = CaseManagementService()
    resolved = await service.resolve_citizen_clarification(
        escalation_case_id="SPP-CASE-2026-100200",
        citizen_clarification_text="Updated crop survey number is 402/A",
    )
    assert resolved is True

    # Empty inputs should fail
    assert await service.resolve_citizen_clarification("", "Note") is False
    assert await service.resolve_citizen_clarification("SPP-CASE-2026-100200", "  ") is False


@pytest.mark.asyncio
async def test_case_management_process_citizen_response_workflow() -> None:
    service = CaseManagementService()
    resolved = await service.process_citizen_response_workflow(
        escalation_case_id="SPP-CASE-2026-100200",
        citizen_clarification_text="Updated crop survey number is 402/A",
    )
    assert resolved is True
