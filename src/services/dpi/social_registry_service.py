"""Authoritative DPI Registry: OpenSPP Social Registry Service.

Provides the external Digital Public Infrastructure (DPI) boundary connector for
OpenSPP (Open Social Protection Platform) and sovereign social welfare registries.

This service is dedicated to checking citizen social protection eligibility against
the external registry boundary. It does not own case review lifecycle state.

See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.2)
See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.3)
See: roadmap.md (Phase 3 Step 3.1 Service Abstractions)
"""

import logging
from typing import Any, Final

import httpx

from src.data_models.caseworker import CaseworkerCaseReviewPayload
from src.services.dpi.dpi_mock_fixtures import (
    UNVERIFIED_IDENTITY_PREFIX,
    UNVERIFIED_IDENTITY_TOKEN_ZERO,
)

logger = logging.getLogger(__name__)

_DEFAULT_DPI_TIMEOUT_SECONDS: Final[float] = 3.0
_HTTP_STATUS_OK: Final[int] = 200


class SocialRegistryService:
    """Service client for social protection platform entitlement verification.

    Queries external social registries for citizen welfare scheme eligibility.

    Supports live REST endpoints with automatic, graceful fallback to deterministic local fixtures.

    See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.3)
    See: decisions/step3.6_live_service_integration.md
    """

    def __init__(
        self,
        endpoint_url: str | None = None,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        timeout_seconds: float = _DEFAULT_DPI_TIMEOUT_SECONDS,
    ) -> None:
        """Initializes OpenSPP social registry client with optional live endpoint configuration.

        Args:
            endpoint_url: Optional base HTTP URL for live OpenSPP social registry service.
            api_key: Optional authorization Bearer token or API key for live calls.
            http_client: Optional async HTTP client for connection pooling.
            timeout_seconds: Request timeout in seconds (default: 3.0s).
        """
        self._endpoint_url = endpoint_url.rstrip("/") if endpoint_url else None
        self._api_key = api_key
        self._http_client = http_client
        self._timeout_seconds = timeout_seconds

    # -------------------------------------------------------------------------
    # Primary Public Workflow Entrypoints
    # -------------------------------------------------------------------------

    async def verify_incident_ticket_eligibility(
        self, case_review: CaseworkerCaseReviewPayload
    ) -> bool:
        """Queries the external registry for beneficiary eligibility.

        Args:
            case_review: Validated CaseworkerCaseReviewPayload instance.

        Returns:
            True if the citizen is eligible according to the external registry, False otherwise.
        """
        logger.info(
            "Evaluating eligibility for incident ticket=%s via OpenSPP registry for session=%s",
            case_review.escalation_case_id,
            case_review.session_id,
        )
        return await self.query_beneficiary_eligibility(
            case_review.tokenized_citizen_id,
            str(case_review.application_intent),
        )

    async def query_beneficiary_eligibility(
        self, tokenized_citizen_id: str, scheme_id: str
    ) -> bool:
        """Queries external social registry for beneficiary entitlement under a specific scheme.

        Args:
            tokenized_citizen_id: 64-character SHA-256 HMAC citizen token.
            scheme_id: Identifier of the target social protection scheme.

        Returns:
            True if citizen is registered and entitled, False otherwise.
        """
        logger.info(
            "Querying OpenSPP scheme=%s eligibility for token=%s",
            scheme_id,
            tokenized_citizen_id[:16],
        )

        if self._endpoint_url:
            live_result = await self._call_live_query(tokenized_citizen_id, scheme_id)
            if live_result is not None:
                return live_result

        return self._mock_query_beneficiary_eligibility(tokenized_citizen_id, scheme_id)

    # -------------------------------------------------------------------------
    # Private Helpers (Live HTTP & Local Mock Handlers)
    # -------------------------------------------------------------------------

    async def _call_live_query(self, tokenized_citizen_id: str, scheme_id: str) -> bool | None:
        """Dispatches live social registry eligibility HTTP request with graceful fallback."""
        target_url = f"{self._endpoint_url}/v1/social/eligibility"
        payload: dict[str, Any] = {
            "tokenized_citizen_id": tokenized_citizen_id,
            "scheme_id": scheme_id,
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
                if isinstance(data, dict) and "is_eligible" in data:
                    return bool(data["is_eligible"])
            logger.warning(
                "Live social registry call returned status=%d for scheme=%s",
                response.status_code,
                scheme_id,
            )
        except Exception as error:
            logger.warning(
                "Live social registry call failed for scheme=%s: %s; using mock fallback",
                scheme_id,
                error,
            )
        return None

    @staticmethod
    def _mock_query_beneficiary_eligibility(tokenized_citizen_id: str, scheme_id: str) -> bool:
        """Deterministic local social registry simulation."""
        return bool(
            tokenized_citizen_id != UNVERIFIED_IDENTITY_TOKEN_ZERO
            and not tokenized_citizen_id.startswith(UNVERIFIED_IDENTITY_PREFIX)
            and scheme_id.strip()
        )
