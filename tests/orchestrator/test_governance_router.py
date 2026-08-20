from datetime import UTC, datetime

import pytest

from src.data_models.common import (
    ApplicationIntent,
    DisbursementStatus,
    DomainEntityKey,
    EligibilityStatus,
    GovernanceAction,
    RejectionReasonCode,
)
from src.data_models.governance import (
    ExtractedEntityPayload,
    GovernanceOutcomePayload,
)
from src.orchestrator.governance_router import (
    ClaimEvaluationContext,
    GovernanceRouter,
)
from src.services.dpi.dpi_mock_fixtures import UNVERIFIED_IDENTITY_PREFIX

MOCK_CITIZEN_TOKEN = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"  # noqa: S105


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
        rejection_reason=RejectionReasonCode.LAND_RECORD_NOT_FOUND,
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
        rejection_reason=RejectionReasonCode.INELIGIBLE_LAND_SIZE,
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


@pytest.mark.asyncio
async def test_governance_router_evaluate_claim_high_confidence_auto_approve() -> None:
    router = GovernanceRouter()
    extracted = ExtractedEntityPayload(
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        ai_confidence_score=0.92,
        domain_entities={
            DomainEntityKey.DISTRICT: "Karnal",
            DomainEntityKey.CROP_NAME: "Wheat",
            DomainEntityKey.SURVEY_NUMBER: "LAND-REC-1002",
        },
    )
    context = ClaimEvaluationContext(
        session_id="sess_eval_1",
        payload_id="ext_eval_1",
        tokenized_citizen_id=MOCK_CITIZEN_TOKEN,
        extracted_payload=extracted,
    )

    outcome = await router.evaluate_claim(context)
    assert outcome.governance_action == GovernanceAction.AUTO_APPROVE
    assert outcome.disbursement_txn_id is not None
    assert outcome.disbursement_status == DisbursementStatus.PENDING


@pytest.mark.asyncio
async def test_governance_router_evaluate_claim_low_confidence_escalation() -> None:
    router = GovernanceRouter()
    extracted = ExtractedEntityPayload(
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        ai_confidence_score=0.70,
        domain_entities={
            DomainEntityKey.DISTRICT: "Karnal",
            DomainEntityKey.CROP_NAME: "Wheat",
        },
    )
    context = ClaimEvaluationContext(
        session_id="sess_eval_2",
        payload_id="ext_eval_2",
        tokenized_citizen_id=MOCK_CITIZEN_TOKEN,
        extracted_payload=extracted,
    )

    outcome = await router.evaluate_claim(context)
    assert outcome.governance_action == GovernanceAction.ROUTE_FOR_MANUAL_REVIEW
    assert outcome.escalation_case_id is not None


@pytest.mark.asyncio
async def test_governance_router_evaluate_claim_adversarial_zeroing() -> None:
    router = GovernanceRouter()
    extracted = ExtractedEntityPayload(
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        ai_confidence_score=0.95,
        domain_entities={DomainEntityKey.DISTRICT: "Karnal"},
        is_adversarial_attempt=True,
    )
    context = ClaimEvaluationContext(
        session_id="sess_eval_3",
        payload_id="ext_eval_3",
        tokenized_citizen_id=MOCK_CITIZEN_TOKEN,
        extracted_payload=extracted,
    )

    outcome = await router.evaluate_claim(context)
    assert outcome.governance_action == GovernanceAction.ROUTE_FOR_MANUAL_REVIEW
    assert outcome.ai_confidence_score == 0.0


@pytest.mark.asyncio
async def test_governance_router_evaluate_claim_unverified_identity() -> None:
    router = GovernanceRouter()
    unverified_token = UNVERIFIED_IDENTITY_PREFIX + "a" * (64 - len(UNVERIFIED_IDENTITY_PREFIX))
    extracted = ExtractedEntityPayload(
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        ai_confidence_score=0.92,
        domain_entities={DomainEntityKey.DISTRICT: "Karnal"},
    )
    context = ClaimEvaluationContext(
        session_id="sess_eval_4",
        payload_id="ext_eval_4",
        tokenized_citizen_id=unverified_token,
        extracted_payload=extracted,
    )

    outcome = await router.evaluate_claim(context)
    assert outcome.governance_action == GovernanceAction.AUTO_REJECT
    assert outcome.rejection_reason == RejectionReasonCode.IDENTITY_NOT_VERIFIED


@pytest.mark.asyncio
async def test_governance_router_evaluate_claim_cadastral_mismatch() -> None:
    router = GovernanceRouter()
    extracted = ExtractedEntityPayload(
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        ai_confidence_score=0.92,
        domain_entities={
            DomainEntityKey.DISTRICT: "Karnal",
            DomainEntityKey.CROP_NAME: "Wheat",
            DomainEntityKey.SURVEY_NUMBER: "INVALID_LAND_REC_9999",
        },
    )
    context = ClaimEvaluationContext(
        session_id="sess_eval_5",
        payload_id="ext_eval_5",
        tokenized_citizen_id=MOCK_CITIZEN_TOKEN,
        extracted_payload=extracted,
    )

    outcome = await router.evaluate_claim(context)
    assert outcome.governance_action == GovernanceAction.AUTO_REJECT
    assert outcome.rejection_reason == RejectionReasonCode.LAND_RECORD_NOT_FOUND
