"""Unit tests for CaseManagementService in Layer 4 Orchestrator."""

from datetime import UTC, datetime

import pytest

from src.data_models.caseworker import (
    CaseworkerCaseReviewPayload,
    CaseworkerReviewOutcomePayload,
)
from src.data_models.common import ApplicationIntent, GovernanceAction
from src.orchestrator import CaseManagementService
from src.services.dpi import SocialRegistryService


@pytest.mark.asyncio
async def test_case_management_stage_case_review() -> None:
    service = CaseManagementService.from_default()
    payload = CaseworkerCaseReviewPayload(
        escalation_case_id="SPP-CASE-2026-100200",
        session_id="sess_12345678",
        payload_id="ext_12345678",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        unprocessed_input_content="Fasal kharab ho gayi hai",
        escalation_reason="AI extraction confidence below threshold",
        staged_at=datetime.now(UTC),
    )
    staged = await service.stage_case_review(payload)
    assert staged is True


@pytest.mark.asyncio
async def test_case_management_stage_case_review_rejection() -> None:
    service = CaseManagementService(social_registry_service=SocialRegistryService())
    payload = CaseworkerCaseReviewPayload(
        escalation_case_id="SPP-CASE-2026-999999",
        session_id="sess_12345678",
        payload_id="ext_12345678",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        unprocessed_input_content="Bad payload",
        escalation_reason="MOCK_FAIL_STAGE_NOTE triggered",
        staged_at=datetime.now(UTC),
    )
    staged = await service.stage_case_review(payload)
    assert staged is False


@pytest.mark.asyncio
async def test_case_management_process_officer_review() -> None:
    service = CaseManagementService.from_default()
    review = CaseworkerReviewOutcomePayload(
        escalation_case_id="SPP-CASE-2026-100200",
        reviewer_id="OFFICER-UUID-12345",
        governance_action=GovernanceAction.MANUAL_APPROVE,
        review_notes="Field inspection verified land ownership",
        approved_amount=5000.0,
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
