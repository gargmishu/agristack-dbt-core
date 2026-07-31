"""Authoritative DPI Registry: Sovereign Payment Rail Service.

Interfaces with national clearing rails (NPCI APBS / PFMS Treasury Gateway)
for benefit disbursement.

See: decisions/step2.2_governance_flows_and_state_transitions.md
See: roadmap.md (Phase 2 Step 2.2 Service Abstractions)
"""

import logging

from src.data_models.disbursement import DisbursementCallbackPayload
from src.data_models.governance import ApplicationDecisionPayload

logger = logging.getLogger(__name__)


class PaymentRailService:
    """Service abstraction for NPCI APBS / PFMS financial clearing and payout dispatch."""

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
