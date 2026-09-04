from typing import Final

import pytest

from src.data_models.common import (
    ApplicationIntent,
    DisbursementStatus,
    DomainEntityKey,
    GovernanceAction,
    RejectionReasonCode,
)
from src.data_models.governance import (
    ClaimEvaluationPayload,
    ExtractedEntityPayload,
)
from src.orchestrator.claim_adjudicator import ClaimAdjudicator
from src.services.dpi.dpi_mock_fixtures import UNVERIFIED_IDENTITY_PREFIX

MOCK_CITIZEN_TOKEN: Final[str] = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"  # noqa: S105


@pytest.mark.asyncio
async def test_claim_adjudicator_evaluate_claim_duplicate_claim() -> None:
    adjudicator = ClaimAdjudicator()
    extracted = ExtractedEntityPayload(
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        ai_confidence_score=0.95,
        domain_entities={
            DomainEntityKey.DISTRICT: "Karnal",
            DomainEntityKey.CROP_NAME: "Wheat",
            DomainEntityKey.SURVEY_NUMBER: "LAND-REC-1002",
        },
    )
    context = ClaimEvaluationPayload(
        session_id="sess_eval_dup",
        payload_id="ext_eval_dup",
        tokenized_citizen_id=MOCK_CITIZEN_TOKEN,
        extracted_payload=extracted,
        active_season="KHARIF-2026",
        approved_payouts_ledger={(MOCK_CITIZEN_TOKEN, "KHARIF-2026")},
    )

    outcome = await adjudicator.evaluate_claim(context)
    assert outcome.governance_action == GovernanceAction.AUTO_REJECT
    assert outcome.rejection_reason == RejectionReasonCode.DUPLICATE_CLAIM_ACTIVE_SEASON


@pytest.mark.asyncio
async def test_claim_adjudicator_evaluate_claim_high_confidence_auto_approve() -> None:
    adjudicator = ClaimAdjudicator()
    extracted = ExtractedEntityPayload(
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        ai_confidence_score=0.92,
        domain_entities={
            DomainEntityKey.DISTRICT: "Karnal",
            DomainEntityKey.CROP_NAME: "Wheat",
            DomainEntityKey.SURVEY_NUMBER: "LAND-REC-1002",
        },
    )
    context = ClaimEvaluationPayload(
        session_id="sess_eval_1",
        payload_id="ext_eval_1",
        tokenized_citizen_id=MOCK_CITIZEN_TOKEN,
        extracted_payload=extracted,
    )

    outcome = await adjudicator.evaluate_claim(context)
    assert outcome.governance_action == GovernanceAction.AUTO_APPROVE
    assert outcome.disbursement_txn_id is not None
    assert outcome.disbursement_status == DisbursementStatus.PENDING


@pytest.mark.asyncio
async def test_claim_adjudicator_evaluate_claim_low_confidence_escalation() -> None:
    adjudicator = ClaimAdjudicator()
    extracted = ExtractedEntityPayload(
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        ai_confidence_score=0.70,
        domain_entities={
            DomainEntityKey.DISTRICT: "Karnal",
            DomainEntityKey.CROP_NAME: "Wheat",
        },
    )
    context = ClaimEvaluationPayload(
        session_id="sess_eval_2",
        payload_id="ext_eval_2",
        tokenized_citizen_id=MOCK_CITIZEN_TOKEN,
        extracted_payload=extracted,
    )

    outcome = await adjudicator.evaluate_claim(context)
    assert outcome.governance_action == GovernanceAction.ROUTE_FOR_MANUAL_REVIEW
    assert outcome.escalation_case_id is not None


@pytest.mark.asyncio
async def test_claim_adjudicator_evaluate_claim_adversarial_zeroing() -> None:
    adjudicator = ClaimAdjudicator()
    extracted = ExtractedEntityPayload(
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        ai_confidence_score=0.95,
        domain_entities={DomainEntityKey.DISTRICT: "Karnal"},
        is_adversarial_attempt=True,
    )
    context = ClaimEvaluationPayload(
        session_id="sess_eval_3",
        payload_id="ext_eval_3",
        tokenized_citizen_id=MOCK_CITIZEN_TOKEN,
        extracted_payload=extracted,
    )

    outcome = await adjudicator.evaluate_claim(context)
    assert outcome.governance_action == GovernanceAction.ROUTE_FOR_MANUAL_REVIEW
    assert outcome.ai_confidence_score == 0.0


@pytest.mark.asyncio
async def test_claim_adjudicator_evaluate_claim_unverified_identity() -> None:
    adjudicator = ClaimAdjudicator()
    unverified_token = UNVERIFIED_IDENTITY_PREFIX + "a" * (64 - len(UNVERIFIED_IDENTITY_PREFIX))
    extracted = ExtractedEntityPayload(
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        ai_confidence_score=0.92,
        domain_entities={DomainEntityKey.DISTRICT: "Karnal"},
    )
    context = ClaimEvaluationPayload(
        session_id="sess_eval_4",
        payload_id="ext_eval_4",
        tokenized_citizen_id=unverified_token,
        extracted_payload=extracted,
    )

    outcome = await adjudicator.evaluate_claim(context)
    assert outcome.governance_action == GovernanceAction.AUTO_REJECT
    assert outcome.rejection_reason == RejectionReasonCode.IDENTITY_NOT_VERIFIED


@pytest.mark.asyncio
async def test_claim_adjudicator_evaluate_claim_cadastral_mismatch() -> None:
    adjudicator = ClaimAdjudicator()
    extracted = ExtractedEntityPayload(
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        ai_confidence_score=0.92,
        domain_entities={
            DomainEntityKey.DISTRICT: "Karnal",
            DomainEntityKey.CROP_NAME: "Wheat",
            DomainEntityKey.SURVEY_NUMBER: "INVALID_LAND_REC_9999",
        },
    )
    context = ClaimEvaluationPayload(
        session_id="sess_eval_5",
        payload_id="ext_eval_5",
        tokenized_citizen_id=MOCK_CITIZEN_TOKEN,
        extracted_payload=extracted,
    )

    outcome = await adjudicator.evaluate_claim(context)
    assert outcome.governance_action == GovernanceAction.AUTO_REJECT
    assert outcome.rejection_reason == RejectionReasonCode.LAND_RECORD_NOT_FOUND
