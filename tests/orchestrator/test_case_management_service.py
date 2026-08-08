"""Unit tests for CaseManagementService in Layer 4 Orchestrator."""

from datetime import UTC, datetime

import pytest

from src.data_models.caseworker import (
    CaseworkerCaseReviewPayload,
    CaseworkerReviewOutcomePayload,
)
from src.data_models.common import ApplicationIntent, GovernanceAction
from src.orchestrator import CaseManagementService

MOCK_CITIZEN_TOKEN = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"  # noqa: S105


@pytest.mark.asyncio
async def test_case_management_stage_incident_ticket() -> None:
    service = CaseManagementService.from_default()
    case = CaseworkerCaseReviewPayload(
        escalation_case_id="SPP-CASE-2026-100200",
        session_id="sess_stage_1",
        payload_id="ext_stage_1",
        tokenized_citizen_id=MOCK_CITIZEN_TOKEN,
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        extracted_entities={},
        unprocessed_input_content="Raw text for manual review",
        escalation_reason="Low AI confidence",
        staged_at=datetime.now(UTC),
    )

    staged = await service.stage_incident_ticket(case)
    assert staged is True
    retrieved = service.get_staged_case("SPP-CASE-2026-100200")
    assert retrieved is not None
    assert retrieved.session_id == "sess_stage_1"
    assert len(service.list_staged_cases()) == 1


@pytest.mark.asyncio
async def test_case_management_process_officer_review() -> None:
    service = CaseManagementService.from_default()
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
    service = CaseManagementService.from_default()
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
    service = CaseManagementService.from_default()
    resolved = await service.process_citizen_response_workflow(
        escalation_case_id="SPP-CASE-2026-100200",
        citizen_clarification_text="Updated crop survey number is 402/A",
    )
    assert resolved is True
