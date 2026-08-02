"""Authoritative DPI Registry: Sovereign Payment Rail Service.

Interfaces with national clearing rails (NPCI APBS / PFMS Treasury Gateway)
for benefit disbursement.

Why monotonic forward-only clearing state machine?
Financial states move strictly forward (`PENDING` -> `INITIATED` -> `SUCCESS`/`FAILED`/`RETURNED`).
Reversion is strictly forbidden to prevent double-payouts.

See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 2.2 & 3.3)
See: roadmap.md (Phase 2 Step 2.2 Service Abstractions)
"""

import logging
from datetime import UTC, datetime

from src.data_models.common import DisbursementStatus
from src.data_models.disbursement import DisbursementCallbackPayload
from src.data_models.governance import GovernanceOutcomePayload
from src.services.dpi.dpi_mock_fixtures import (
    MOCK_PAYMENT_FAIL_TRIGGER,
    MOCK_PAYMENT_FAILURE_REASON,
)

logger = logging.getLogger(__name__)


class PaymentRailService:
    """Service abstraction for NPCI APBS / PFMS financial clearing and payout dispatch.

    Manages asynchronous clearing wire transmissions (`disbursement_txn_id`) and status callbacks.

    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 4.4)
    """

    async def initiate_disbursement(
        self, decision: GovernanceOutcomePayload
    ) -> DisbursementCallbackPayload | None:
        """Dispatches automated payout instruction over sovereign payment clearing rails.

        Args:
            decision: GovernanceOutcomePayload with valid disbursement_txn_id.

        Returns:
            DisbursementCallbackPayload indicating initial wire status, or None.
        """
        logger.info(
            "Initiating payment clearing for session=%s, txn=%s",
            decision.session_id,
            decision.disbursement_txn_id,
        )
        if decision.disbursement_txn_id is None:
            return None

        if MOCK_PAYMENT_FAIL_TRIGGER in str(decision.disbursement_txn_id).upper():
            status = DisbursementStatus.FAILED
            reason = MOCK_PAYMENT_FAILURE_REASON
        else:
            status = DisbursementStatus.SUCCESS
            reason = None

        return DisbursementCallbackPayload(
            disbursement_txn_id=decision.disbursement_txn_id,
            disbursement_status=status,
            cleared_at=datetime.now(UTC),
            failure_reason_code=reason,
        )
