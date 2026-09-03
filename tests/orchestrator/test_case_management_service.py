"""Unit tests for CaseManagementService in Layer 4 Orchestrator."""

from datetime import UTC, datetime

import pytest

from src.data_models.caseworker import (
    CaseworkerCaseReviewPayload,
    CaseworkerReviewOutcomePayload,
)
from src.data_models.common import (
    ApplicationIntent,
    ApplicationStatus,
    EscalationReasonCode,
    GovernanceAction,
)
from src.orchestrator import CaseManagementService

MOCK_CITIZEN_TOKEN = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"  # noqa: S105


def build_case() -> CaseworkerCaseReviewPayload:
    return CaseworkerCaseReviewPayload(
        escalation_case_id="SPP-CASE-2026-100200",
        session_id="sess_stage_1",
        payload_id="ext_stage_1",
        tokenized_citizen_id=MOCK_CITIZEN_TOKEN,
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        extracted_entities={},
        unprocessed_input_content="Raw text for manual review",
        escalation_reason=EscalationReasonCode.LOW_AI_CONFIDENCE,
        staged_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_case_management_stage_incident_ticket() -> None:
    service = CaseManagementService()
    case = build_case()

    staged = await service.stage_incident_ticket(case)
    assert staged is True
    retrieved = service.get_staged_case("SPP-CASE-2026-100200")
    assert retrieved is not None
    assert retrieved.session_id == "sess_stage_1"
    assert len(service.list_staged_cases()) == 1


@pytest.mark.asyncio
async def test_case_management_process_officer_review() -> None:
    service = CaseManagementService()
    await service.stage_incident_ticket(build_case())
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
    assert service.get_case_status(review.escalation_case_id) == ApplicationStatus.APPROVED
    assert service.list_review_audit_entries(review.escalation_case_id) == [review]
    assert service.get_staged_case(review.escalation_case_id) is None

    # Reviewing an unstaged / already-processed ticket should return False
    unstaged_res = await service.process_officer_review(review)
    assert unstaged_res is False


@pytest.mark.asyncio
async def test_case_management_process_officer_review_unsupported_action(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CaseManagementService()
    await service.stage_incident_ticket(build_case())

    # Construct review outcome with action outside
    # (MANUAL_APPROVE, MANUAL_REJECT, REQUEST_MORE_INFO)
    # Using object.__setattr__ to bypass Pydantic model validator for unit testing service guard
    review = CaseworkerReviewOutcomePayload(
        escalation_case_id="SPP-CASE-2026-100200",
        reviewer_id="OFFICER-UUID-12345",
        governance_action=GovernanceAction.MANUAL_APPROVE,
        review_notes="Field inspection verified land ownership",
        approved_amount=5000.0,
        rejection_reason=None,
        reviewed_at=datetime.now(UTC),
    )
    object.__setattr__(review, "governance_action", GovernanceAction.AUTO_APPROVE)
    review_result = await service.process_officer_review(review)
    assert review_result is False


@pytest.mark.asyncio
async def test_case_management_resolve_citizen_clarification() -> None:
    service = CaseManagementService()
    await service.stage_incident_ticket(build_case())
    await service.process_officer_review(
        CaseworkerReviewOutcomePayload(
            escalation_case_id="SPP-CASE-2026-100200",
            reviewer_id="OFFICER-UUID-12345",
            governance_action=GovernanceAction.REQUEST_MORE_INFO,
            review_notes="Please provide the updated crop survey number",
            approved_amount=None,
            rejection_reason=None,
            reviewed_at=datetime.now(UTC),
        )
    )
    resolved = await service.resolve_citizen_clarification(
        escalation_case_id="SPP-CASE-2026-100200",
        citizen_clarification_text="  Updated crop survey number is 402/A  ",
    )
    assert resolved is True
    assert service.get_case_status("SPP-CASE-2026-100200") == ApplicationStatus.UNDER_REVIEW
    assert (
        service.get_citizen_clarification("SPP-CASE-2026-100200")
        == "Updated crop survey number is 402/A"
    )
    assert [entry.text for entry in service.get_citizen_clarifications("SPP-CASE-2026-100200")] == [
        "Updated crop survey number is 402/A"
    ]
    returned_clarifications = service.get_citizen_clarifications("SPP-CASE-2026-100200")
    returned_clarifications.clear()
    assert service.get_citizen_clarifications("SPP-CASE-2026-100200")
    updated_case = service.get_staged_case("SPP-CASE-2026-100200")
    assert updated_case is not None
    assert updated_case.unprocessed_input_content == "Raw text for manual review"
    assert len(updated_case.clarification_history) == 1
    assert updated_case.clarification_history[0].text == "Updated crop survey number is 402/A"
    assert updated_case.clarification_history[0].received_at.tzinfo == UTC

    # Empty inputs should fail
    assert await service.resolve_citizen_clarification("", "Note") is False
    assert await service.resolve_citizen_clarification("SPP-CASE-2026-100200", "  ") is False
    assert (
        await service.resolve_citizen_clarification(
            "SPP-CASE-2026-100200", "A second clarification"
        )
        is False
    )
    await service.process_officer_review(
        CaseworkerReviewOutcomePayload(
            escalation_case_id="SPP-CASE-2026-100200",
            reviewer_id="OFFICER-UUID-12345",
            governance_action=GovernanceAction.REQUEST_MORE_INFO,
            review_notes="Please provide the updated village code",
            approved_amount=None,
            rejection_reason=None,
            reviewed_at=datetime.now(UTC),
        )
    )
    assert (
        await service.resolve_citizen_clarification(
            "SPP-CASE-2026-100200", "Updated village code is VLG-22"
        )
        is True
    )
    assert (
        service.get_citizen_clarification("SPP-CASE-2026-100200")
        == "Updated village code is VLG-22"
    )
    assert [entry.text for entry in service.get_citizen_clarifications("SPP-CASE-2026-100200")] == [
        "Updated crop survey number is 402/A",
        "Updated village code is VLG-22",
    ]
