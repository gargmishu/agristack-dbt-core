"""Authoritative DPI Registry: Sovereign Payment Rail Service.

Interfaces with national clearing rails (NPCI APBS / PFMS Treasury Gateway)
for benefit disbursement.

Why monotonic forward-only clearing state machine?
Financial states move strictly forward (`PENDING` -> `INITIATED` -> `SUCCESS`/`FAILED`/`RETURNED`).
Reversion is strictly forbidden to prevent double-payouts.

In production environments, enforces live HTTPS communication via LivePaymentRailService with
strict fail-fast configuration and fail-closed error handling (no mock fallback).
In non-production, MockPaymentRailService provides deterministic simulation for offline testing.

See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 2.2 & 3.3)
See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.4)
See: decisions/step3.6_live_service_integration.md
See: roadmap.md (Phase 2 Step 2.2 Service Abstractions)
"""

import logging
from datetime import UTC, datetime
from typing import Any, Final, Protocol, Self

from httpx import AsyncClient

from src.config.service_settings import (
    get_payment_api_key,
    get_payment_endpoint,
    is_production,
)
from src.data_models.common import DisbursementStatus
from src.data_models.disbursement import DisbursementCallbackPayload
from src.data_models.governance import GovernanceOutcomePayload
from src.errors.service_errors import (
    ServiceAuthenticationError,
    ServiceConfigurationError,
    ServiceRequestPayloadError,
    ServiceResponsePayloadError,
    ServiceUnavailableError,
)
from src.services.dpi.dpi_mock_fixtures import (
    MOCK_PAYMENT_FAIL_TRIGGER,
    MOCK_PAYMENT_FAILURE_REASON,
)
from src.services.http_client_pool import get_shared_http_client

logger = logging.getLogger(__name__)

_DEFAULT_PAYMENT_TIMEOUT_SECONDS: Final[float] = 5.0
_HTTP_STATUS_OK: Final[int] = 200
_HTTP_STATUS_BAD_REQUEST: Final[int] = 400
_HTTP_STATUS_UNAUTHORIZED: Final[int] = 401
_HTTP_STATUS_FORBIDDEN: Final[int] = 403
_HTTP_STATUS_UNPROCESSABLE_ENTITY: Final[int] = 422


class PaymentRailService(Protocol):
    """Protocol contract for Direct Benefit Transfer (DBT) payment rail clearing.

    Dispatches automated payment clearing instructions and receives clearing status callbacks.
    """

    async def initiate_disbursement(
        self, outcome: GovernanceOutcomePayload
    ) -> DisbursementCallbackPayload | None:
        """Dispatches automated payout instruction over sovereign payment clearing rails."""
        ...


class LivePaymentRailService:
    """Production live client executing HTTPS calls to sovereign NPCI/PFMS clearing gateways.

    Strictly requires endpoint URL, API key, and pooled HTTP client. Fails closed with
    ServiceUnavailableError on network errors, timeouts, or remote outages, raises
    ServiceRequestPayloadError on malformed payment instructions (400/422),
    and raises ServiceResponsePayloadError on schema contract violations (502).
    """

    def __init__(
        self,
        endpoint_url: str,
        api_key: str,
        http_client: AsyncClient,
        timeout_seconds: float = _DEFAULT_PAYMENT_TIMEOUT_SECONDS,
    ) -> None:
        """Initializes live payment rail client with mandatory credentials and transport."""
        if not endpoint_url or not endpoint_url.strip():
            raise ServiceConfigurationError(
                "Live NPCI/PFMS payment rail endpoint URL is required.",
                service_name="payment_rail",
            )
        if not api_key or not api_key.strip():
            raise ServiceConfigurationError(
                "Live NPCI/PFMS payment rail API key is required.",
                service_name="payment_rail",
            )
        self._endpoint_url = endpoint_url.rstrip("/")
        self._api_key = api_key.strip()
        self._http_client = http_client
        self._timeout_seconds = timeout_seconds

    @classmethod
    def from_env(
        cls,
        endpoint_url: str | None = None,
        api_key: str | None = None,
        http_client: AsyncClient | None = None,
        timeout_seconds: float = _DEFAULT_PAYMENT_TIMEOUT_SECONDS,
    ) -> Self:
        """Factory constructor building live instance from environment settings or overrides."""
        payment_endpoint = endpoint_url or get_payment_endpoint()
        payment_api_key = api_key or get_payment_api_key()
        if not payment_endpoint:
            raise ServiceConfigurationError(
                "Live NPCI/PFMS payment rail endpoint URL is required in production mode.",
                service_name="payment_rail",
            )
        if not payment_api_key:
            raise ServiceConfigurationError(
                "Live NPCI/PFMS payment rail API key is required in production mode.",
                service_name="payment_rail",
            )
        return cls(
            endpoint_url=payment_endpoint,
            api_key=payment_api_key,
            http_client=http_client or get_shared_http_client(),
            timeout_seconds=timeout_seconds,
        )

    # -------------------------------------------------------------------------
    # Primary Public Workflow Entrypoints
    # -------------------------------------------------------------------------

    async def initiate_disbursement(
        self, outcome: GovernanceOutcomePayload
    ) -> DisbursementCallbackPayload | None:
        """Dispatches automated payout instruction over live payment clearing rails.

        Args:
            outcome: GovernanceOutcomePayload with valid disbursement_txn_id.

        Returns:
            DisbursementCallbackPayload indicating initial wire status, or None.

        Raises:
            ServiceRequestPayloadError: If disbursement instruction is rejected (400/422).
            ServiceResponsePayloadError: If payment rail returns invalid response schema.
            ServiceUnavailableError: If live payment clearing rail fails, times out, or returns 5xx.
            ServiceAuthenticationError: If live payment clearing rail returns 401/403.
        """
        if outcome.disbursement_txn_id is None:
            logger.debug(
                "Skipping payment clearing for session=%s: disbursement_txn_id is None",
                outcome.session_id,
            )
            return None

        logger.info(
            "Live initiating payment clearing for session=%s, txn=%s",
            outcome.session_id,
            outcome.disbursement_txn_id,
        )

        target_url = f"{self._endpoint_url}/v1/payments/disburse"
        payload: dict[str, Any] = {
            "session_id": outcome.session_id,
            "disbursement_txn_id": outcome.disbursement_txn_id,
            "governance_action": outcome.governance_action.value,
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        try:
            response = await self._http_client.post(
                target_url, json=payload, headers=headers, timeout=self._timeout_seconds
            )
            if response.status_code == _HTTP_STATUS_OK:
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        return DisbursementCallbackPayload.model_validate(data)
                except Exception as err:
                    raise ServiceResponsePayloadError(
                        f"Live payment rail response from {target_url} violated schema: {err}",
                        service_name="payment_rail",
                    ) from err
                raise ServiceResponsePayloadError(
                    f"Live payment rail returned non-dictionary JSON from {target_url}.",
                    service_name="payment_rail",
                )
            if response.status_code in (_HTTP_STATUS_UNAUTHORIZED, _HTTP_STATUS_FORBIDDEN):
                raise ServiceAuthenticationError(
                    f"Payment rail authentication failed with status={response.status_code}",
                    service_name="payment_rail",
                    status_code=response.status_code,
                )
            if response.status_code in (
                _HTTP_STATUS_BAD_REQUEST,
                _HTTP_STATUS_UNPROCESSABLE_ENTITY,
            ):
                raise ServiceRequestPayloadError(
                    f"Payment rail rejected disbursement payload with "
                    f"status={response.status_code}: {response.text}",
                    service_name="payment_rail",
                    status_code=response.status_code,
                )
            raise ServiceUnavailableError(
                f"Live payment rail call to {target_url} failed with "
                f"status={response.status_code}: {response.text}",
                service_name="payment_rail",
                status_code=response.status_code,
            )
        except (
            ServiceAuthenticationError,
            ServiceRequestPayloadError,
            ServiceResponsePayloadError,
            ServiceUnavailableError,
        ):
            raise
        except Exception as error:
            logger.warning(
                "Live payment call failed for txn=%s: %s", outcome.disbursement_txn_id, error
            )
            raise ServiceUnavailableError(
                f"Live payment rail failed for txn '{outcome.disbursement_txn_id}': {error}",
                service_name="payment_rail",
            ) from error


class MockPaymentRailService:
    """Deterministic local payment clearing simulation for offline testing."""

    async def initiate_disbursement(
        self, outcome: GovernanceOutcomePayload
    ) -> DisbursementCallbackPayload | None:
        """Simulates payment clearing with deterministic transaction ID rules."""
        if outcome.disbursement_txn_id is None:
            logger.debug(
                "Skipping payment clearing for session=%s: disbursement_txn_id is None",
                outcome.session_id,
            )
            return None

        logger.info(
            "Mock payment clearing for session=%s, txn=%s",
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


def create_payment_rail_service(
    endpoint_url: str | None = None,
    api_key: str | None = None,
    http_client: AsyncClient | None = None,
    timeout_seconds: float = _DEFAULT_PAYMENT_TIMEOUT_SECONDS,
    require_live: bool | None = None,
) -> PaymentRailService:
    """Factory creating appropriate payment rail service implementation based on environment.

    Resolution follows a 3-tier precedence model:
    1. Explicit Parameters: If endpoint_url and api_key are provided directly as arguments,
       constructs LivePaymentRailService targeting those coordinates (useful for local
       WireMock, stub proxies, or sandbox integration without enforcing production invariants).
    2. Mandatory Production: If require_live=True (or ENVIRONMENT='production' when omitted),
       constructs LivePaymentRailService via environment settings, failing fast if credentials
       are missing.
    3. Offline Simulation: If require_live is False and explicit credentials are not passed
       (even if present in environment variables), returns MockPaymentRailService to
       guarantee offline test isolation for local development and CI pipelines.
    """
    must_be_live = is_production() if require_live is None else require_live
    if must_be_live:
        return LivePaymentRailService.from_env(
            endpoint_url=endpoint_url,
            api_key=api_key,
            http_client=http_client,
            timeout_seconds=timeout_seconds,
        )

    if endpoint_url and api_key:
        return LivePaymentRailService(
            endpoint_url=endpoint_url,
            api_key=api_key,
            http_client=http_client or get_shared_http_client(),
            timeout_seconds=timeout_seconds,
        )

    return MockPaymentRailService()
