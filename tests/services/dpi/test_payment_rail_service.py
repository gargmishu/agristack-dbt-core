from datetime import UTC, datetime

import pytest

from src.data_models.common import (
    DisbursementStatus,
    EligibilityStatus,
    GovernanceDecision,
)
from src.data_models.governance import ApplicationDecisionPayload
from src.services.dpi import PaymentRailService


@pytest.mark.asyncio
async def test_payment_rail_initiate_disbursement() -> None:
    service = PaymentRailService()
    decision = ApplicationDecisionPayload(
        session_id="sess_12345678",
        payload_id="ext_12345678",
        ai_confidence_score=0.96,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        governance_decision=GovernanceDecision.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-987654",
        disbursement_status=DisbursementStatus.PENDING,
        decided_at=datetime.now(UTC),
    )
    result = await service.initiate_disbursement(decision)
    assert result is None
