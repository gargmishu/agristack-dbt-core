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

from src.data_models.disbursement import DisbursementCallbackPayload
from src.data_models.governance import ApplicationDecisionPayload

logger = logging.getLogger(__name__)


class PaymentRailService:
    """Service abstraction for NPCI APBS / PFMS financial clearing and payout dispatch.

    Manages asynchronous clearing wire transmissions (`disbursement_txn_id`) and status callbacks.

    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 4.4)
    """

    async def initiate_disbursement(
        self, decision: ApplicationDecisionPayload
    ) -> DisbursementCallbackPayload | None:
        """Dispatches automated payout instruction over sovereign payment clearing rails.

        Args:
            decision: ApplicationDecisionPayload with valid disbursement_txn_id.

        Returns:
            DisbursementCallbackPayload indicating initial wire status, or None.
        """
        logger.info(
            "Initiating payment clearing for session=%s, txn=%s",
            decision.session_id,
            decision.disbursement_txn_id,
        )
        return None
