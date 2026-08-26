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
from typing import Any, Final

import httpx

from src.data_models.common import DisbursementStatus
from src.data_models.disbursement import DisbursementCallbackPayload
from src.data_models.governance import GovernanceOutcomePayload
from src.services.dpi.dpi_mock_fixtures import (
    MOCK_PAYMENT_FAIL_TRIGGER,
    MOCK_PAYMENT_FAILURE_REASON,
)

logger = logging.getLogger(__name__)

_DEFAULT_PAYMENT_TIMEOUT_SECONDS: Final[float] = 5.0
_HTTP_STATUS_OK: Final[int] = 200


class PaymentRailService:
    """Service client for Direct Benefit Transfer (DBT) payment rail clearing.

    Dispatches automated payment clearing instructions and receives clearing status callbacks.

    Supports live REST endpoints with automatic, graceful fallback to deterministic local fixtures.

    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 4.4)
    See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.4)
    See: decisions/step3.6_live_service_integration.md
    """

    def __init__(
        self,
        endpoint_url: str | None = None,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        timeout_seconds: float = _DEFAULT_PAYMENT_TIMEOUT_SECONDS,
    ) -> None:
        """Initializes payment rail client with optional live endpoint configuration.

        Args:
            endpoint_url: Optional base HTTP URL for live NPCI/PFMS payment service.
            api_key: Optional authorization Bearer token or API key for live calls.
            http_client: Optional async HTTP client for connection pooling.
            timeout_seconds: Request timeout in seconds (default: 5.0s).
        """
        self._endpoint_url = endpoint_url.rstrip("/") if endpoint_url else None
        self._api_key = api_key
        self._http_client = http_client
        self._timeout_seconds = timeout_seconds

    # -------------------------------------------------------------------------
    # Primary Public Workflow Entrypoints
    # -------------------------------------------------------------------------

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

        if self._endpoint_url:
            live_result = await self._call_live_disburse(outcome)
            if live_result is not None:
                return live_result

        return self._mock_initiate_disbursement(outcome)

    # -------------------------------------------------------------------------
    # Private Helpers (Live HTTP & Local Mock Handlers)
    # -------------------------------------------------------------------------

    async def _call_live_disburse(
        self, outcome: GovernanceOutcomePayload
    ) -> DisbursementCallbackPayload | None:
        """Dispatches live payment clearing HTTP request with graceful fallback."""
        target_url = f"{self._endpoint_url}/v1/payments/disburse"
        payload: dict[str, Any] = {
            "session_id": outcome.session_id,
            "disbursement_txn_id": outcome.disbursement_txn_id,
            "governance_action": outcome.governance_action.value,
        }
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            if self._http_client:
                response = await self._http_client.post(
                    target_url, json=payload, headers=headers, timeout=self._timeout_seconds
                )
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        target_url, json=payload, headers=headers, timeout=self._timeout_seconds
                    )
            if response.status_code == _HTTP_STATUS_OK:
                data = response.json()
                if isinstance(data, dict):
                    return DisbursementCallbackPayload.model_validate(data)
            logger.warning(
                "Live payment clearing returned status=%d for txn=%s",
                response.status_code,
                outcome.disbursement_txn_id,
            )
        except Exception as error:
            logger.warning(
                "Live payment call failed for txn=%s: %s; using mock fallback",
                outcome.disbursement_txn_id,
                error,
            )
        return None

    @staticmethod
    def _mock_initiate_disbursement(
        outcome: GovernanceOutcomePayload,
    ) -> DisbursementCallbackPayload:
        """Deterministic local payment clearing simulation."""
        assert outcome.disbursement_txn_id is not None
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
