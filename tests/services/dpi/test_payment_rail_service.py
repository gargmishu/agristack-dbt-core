from datetime import UTC, datetime

import pytest

from src.data_models.common import (
    DisbursementStatus,
    EligibilityStatus,
    GovernanceAction,
)
from src.data_models.governance import GovernanceOutcomePayload
from src.services.dpi import PaymentRailService


@pytest.mark.asyncio
async def test_payment_rail_initiate_disbursement() -> None:
    service = PaymentRailService()
    outcome = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="ext_12345678",
        ai_confidence_score=0.96,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-987654",
        disbursement_status=DisbursementStatus.PENDING,
        evaluated_at=datetime.now(UTC),
    )
    result = await service.initiate_disbursement(outcome)
    assert result is not None
    assert result.disbursement_txn_id == "TXN-2026-987654"
    assert result.disbursement_status == DisbursementStatus.SUCCESS


@pytest.mark.asyncio
async def test_payment_rail_disbursement_failure() -> None:
    service = PaymentRailService()
    outcome = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="ext_12345678",
        ai_confidence_score=0.96,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-FAIL-101",
        disbursement_status=DisbursementStatus.PENDING,
        evaluated_at=datetime.now(UTC),
    )
    result = await service.initiate_disbursement(outcome)
    assert result is not None
    assert result.disbursement_status == DisbursementStatus.FAILED
    assert result.failure_reason_code is not None


@pytest.mark.asyncio
async def test_payment_rail_skips_when_txn_id_is_none() -> None:
    service = PaymentRailService()
    outcome = GovernanceOutcomePayload(
        session_id="sess_12345678",
        payload_id="ext_12345678",
        ai_confidence_score=0.45,
        eligibility_status=EligibilityStatus.INELIGIBLE,
        governance_action=GovernanceAction.AUTO_REJECT,
        rejection_reason="Ineligible land registry status",
        disbursement_txn_id=None,
        disbursement_status=None,
        evaluated_at=datetime.now(UTC),
    )
    result = await service.initiate_disbursement(outcome)
    assert result is None
