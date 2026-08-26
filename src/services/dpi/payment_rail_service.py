"""Authoritative DPI Registry: Sovereign Payment Rail Service.

Interfaces with national clearing rails (NPCI APBS / PFMS Treasury Gateway)
for benefit disbursement.

Why monotonic forward-only clearing state machine?
Financial states move strictly forward (`PENDING` -> `INITIATED` ->
`SUCCESS`/`FAILED`/`RETURNED`).
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
    """Service client for Direct Benefit Transfer (DBT) payment rail clearing.

    Dispatches automated payment clearing instructions and receives clearing status
    callbacks.

    Operations:
    - `initiate_disbursement`: Sends payout instructions for approved governance outcomes
      and
      returns initial clearing status (`DisbursementCallbackPayload`).

    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 4.4)
    See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.4)
    """

    async def initiate_disbursement(
        self, outcome: GovernanceOutcomePayload
    ) -> DisbursementCallbackPayload | None:
        """Dispatches automated payout instruction over sovereign payment clearing rails.

        Args:
            outcome: GovernanceOutcomePayload with valid disbursement_txn_id.

        Returns:
            DisbursementCallbackPayload indicating initial wire status, or None.
        """
        if outcome.disbursement_txn_id is None:
            logger.debug(
                "Skipping payment clearing for session=%s: disbursement_txn_id is None",
                outcome.session_id,
            )
            return None

        logger.info(
            "Initiating payment clearing for session=%s, txn=%s",
            outcome.session_id,
            outcome.disbursement_txn_id,
        )

        if MOCK_PAYMENT_FAIL_TRIGGER in str(outcome.disbursement_txn_id).upper():
            status = DisbursementStatus.FAILED
            failure_reason = MOCK_PAYMENT_FAILURE_REASON
            bank_reference_id = f"NPCI-REJ-{str(outcome.disbursement_txn_id)[-6:]}"
            logger.warning(
                "Payment clearing failed for session=%s, txn=%s, reason=%s",
                outcome.session_id,
                outcome.disbursement_txn_id,
                failure_reason,
            )
        else:
            status = DisbursementStatus.SUCCESS
            failure_reason = None
            bank_reference_id = f"NPCI-UTR-{str(outcome.disbursement_txn_id)[-6:]}"

        return DisbursementCallbackPayload(
            disbursement_txn_id=outcome.disbursement_txn_id,
            bank_reference_id=bank_reference_id,
            disbursement_status=status,
            cleared_at=datetime.now(UTC),
            failure_reason_code=failure_reason,
        )
