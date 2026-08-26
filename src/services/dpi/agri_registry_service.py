"""Authoritative DPI Registry: AgriStack Cadastral & Land Registry Service.

Performs cadastral plot verification, landholding ownership cross-matching, and crop
validation.

Why cross-match against AgriStack cadastral registries?
Benefit eligibility requires verifying landholding entitlement, survey/khata numbers, and
seasonal
crop records before executing automated payouts or staging caseworker reviews.

See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.2)
See: decisions/step2.0_canonical_domain_schemas.md (Section 4.3)
See: decisions/step2.2_governance_flows_and_state_transitions.md
See: roadmap.md (Phase 3 Step 3.1 Service Abstractions)
"""

import logging
from typing import Any, Final

import httpx

from src.services.dpi.dpi_mock_fixtures import (
    INVALID_LAND_RECORD_PREFIX,
    INVALID_SURVEY_NUMBER,
    MOCK_CADASTRAL_REGISTRY,
    UNVERIFIED_IDENTITY_PREFIX,
    UNVERIFIED_IDENTITY_TOKEN_ZERO,
)

logger = logging.getLogger(__name__)

_DEFAULT_DPI_TIMEOUT_SECONDS: Final[float] = 3.0
_HTTP_STATUS_OK: Final[int] = 200


class AgriRegistryService:
    """Service client for agricultural landholding and crop registry verification.

    Cross-matches citizen identity tokens and land record identifiers against cadastral databases.

    Supports live REST endpoints with automatic, graceful fallback to deterministic local fixtures.

    See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.2)
    See: decisions/step3.6_live_service_integration.md
    """

    def __init__(
        self,
        endpoint_url: str | None = None,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        timeout_seconds: float = _DEFAULT_DPI_TIMEOUT_SECONDS,
    ) -> None:
        """Initializes AgriStack registry client with optional live endpoint configuration.

        Args:
            endpoint_url: Optional base HTTP URL for live AgriStack cadastral service.
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

    async def verify_land_record(self, tokenized_citizen_id: str, land_record_id: str) -> bool:
        """Cross-matches citizen identity token against cadastral land record ID.

        Args:
            tokenized_citizen_id: 64-character SHA-256 HMAC citizen identity token.
            land_record_id: Land record survey/plot identifier.

        Returns:
            True if land ownership and crop entitlement match, False otherwise.
        """
        logger.info(
            "Verifying land record=%s for token=%s...",
            land_record_id,
            tokenized_citizen_id[:16],
        )

        if self._endpoint_url:
            live_result = await self._call_live_verify(tokenized_citizen_id, land_record_id)
            if live_result is not None:
                return live_result

        return self._mock_verify_land_record(tokenized_citizen_id, land_record_id)

    # -------------------------------------------------------------------------
    # Private Helpers (Live HTTP & Local Mock Handlers)
    # -------------------------------------------------------------------------

    async def _call_live_verify(
        self, tokenized_citizen_id: str, land_record_id: str
    ) -> bool | None:
        """Dispatches live cadastral land record verification HTTP request with fallback."""
        target_url = f"{self._endpoint_url}/v1/land/cadastral/verify"
        payload: dict[str, Any] = {
            "tokenized_citizen_id": tokenized_citizen_id,
            "land_record_id": land_record_id,
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
                if isinstance(data, dict) and "is_entitled" in data:
                    return bool(data["is_entitled"])
            logger.warning(
                "Live cadastral verification returned status=%d for record=%s",
                response.status_code,
                land_record_id,
            )
        except Exception as error:
            logger.warning(
                "Live cadastral call failed for record=%s: %s; using mock fallback",
                land_record_id,
                error,
            )
        return None

    @staticmethod
    def _mock_verify_land_record(tokenized_citizen_id: str, land_record_id: str) -> bool:
        """Deterministic local cadastral verification simulation."""
        if (
            not land_record_id.strip()
            or land_record_id.startswith(INVALID_LAND_RECORD_PREFIX)
            or INVALID_SURVEY_NUMBER in land_record_id
        ):
            logger.warning(
                "Cadastral verification failed: invalid land_record_id='%s' for token=%s...",
                land_record_id,
                tokenized_citizen_id[:16],
            )
            return False
        if (
            tokenized_citizen_id == UNVERIFIED_IDENTITY_TOKEN_ZERO
            or tokenized_citizen_id.startswith(UNVERIFIED_IDENTITY_PREFIX)
        ):
            logger.warning(
                "Cadastral verification failed: unverified citizen token=%s...",
                tokenized_citizen_id[:16],
            )
            return False
        if land_record_id in MOCK_CADASTRAL_REGISTRY:
            is_entitled = MOCK_CADASTRAL_REGISTRY[land_record_id].is_entitled
            if not is_entitled:
                logger.warning(
                    "Cadastral verification failed: citizen not entitled for land_record=%s",
                    land_record_id,
                )
            return is_entitled
        return True
