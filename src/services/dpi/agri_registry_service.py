"""Authoritative DPI Registry: AgriStack Cadastral Land Records Service.

Connects to the sovereign AgriStack Digital Public Infrastructure to cross-match
farmer identity tokens against cadastral land parcels, survey numbers, and seasonal
crop sowing declarations.

In production environments, LiveAgriRegistryService enforces live HTTPS communication with
strict fail-fast configuration and fail-closed error handling (no mock fallback).
In non-production, MockAgriRegistryService provides deterministic simulation for offline testing.

See: decisions/step2.0_canonical_domain_schemas.md (Section 4.3)
See: decisions/step2.2_governance_flows_and_state_transitions.md
See: decisions/step3.6_live_service_integration.md
See: roadmap.md (Phase 3 Step 3.1 Service Abstractions)
"""

import logging
from typing import Any, Final, Protocol, Self

from httpx import AsyncClient

from src.config.service_settings import (
    get_agristack_api_key,
    get_agristack_endpoint,
    is_production,
)
from src.errors.service_errors import ServiceResponsePayloadError
from src.services.dpi.dpi_mock_fixtures import (
    INVALID_LAND_RECORD_PREFIX,
    INVALID_SURVEY_NUMBER,
    MOCK_CADASTRAL_REGISTRY,
    UNVERIFIED_IDENTITY_PREFIX,
    UNVERIFIED_IDENTITY_TOKEN_ZERO,
)
from src.services.http_transport import (
    ServiceHttpTransport,
    ServiceTransportConfig,
    get_shared_http_client,
)

logger = logging.getLogger(__name__)

__all__ = [
    "AgriRegistryService",
    "LiveAgriRegistryService",
    "MockAgriRegistryService",
    "create_agri_registry_service",
]

_DEFAULT_DPI_TIMEOUT_SECONDS: Final[float] = 3.0
_LAND_VERIFY_PATH: Final[str] = "/v1/land/cadastral/verify"


class AgriRegistryService(Protocol):
    """Protocol contract for AgriStack cadastral land records registry operations."""

    async def verify_land_record(self, tokenized_citizen_id: str, land_record_id: str) -> bool:
        """Cross-matches citizen identity token against cadastral land record ID."""
        ...


class LiveAgriRegistryService:
    """Production live client executing HTTPS calls to sovereign AgriStack land gateways.

    Strictly requires endpoint URL, API key, and pooled HTTP client. Fails closed with
    ServiceUnavailableError on network errors, timeouts, or remote outages, raises
    ServiceRequestPayloadError on malformed survey records or unprocessable payloads (400/422),
    and raises ServiceResponsePayloadError on schema contract violations (502).
    """

    def __init__(
        self,
        endpoint_url: str,
        api_key: str,
        http_client: AsyncClient,
        timeout_seconds: float = _DEFAULT_DPI_TIMEOUT_SECONDS,
    ) -> None:
        """Initializes live AgriStack registry client with mandatory credentials and transport."""
        self._transport = ServiceHttpTransport(
            http_client=http_client,
            api_key=api_key,
            config=ServiceTransportConfig(
                service_name="agristack",
                service_title="AgriStack",
                timeout_seconds=timeout_seconds,
            ),
            base_url=endpoint_url,
        )

    @classmethod
    def from_env(
        cls,
        endpoint_url: str | None = None,
        api_key: str | None = None,
        http_client: AsyncClient | None = None,
        timeout_seconds: float = _DEFAULT_DPI_TIMEOUT_SECONDS,
    ) -> Self:
        """Factory constructor building live instance from environment settings or overrides."""
        return cls(
            endpoint_url=endpoint_url or get_agristack_endpoint() or "",
            api_key=api_key or get_agristack_api_key() or "",
            http_client=http_client or get_shared_http_client(),
            timeout_seconds=timeout_seconds,
        )

    # -------------------------------------------------------------------------
    # Primary Public Workflow Entrypoints
    # -------------------------------------------------------------------------

    async def verify_land_record(self, tokenized_citizen_id: str, land_record_id: str) -> bool:
        """Cross-matches citizen identity token against cadastral land record ID via live API.

        Args:
            tokenized_citizen_id: 64-character SHA-256 HMAC citizen identity token.
            land_record_id: Land record survey/plot identifier.

        Returns:
            True if land ownership and crop entitlement match, False otherwise.

        Raises:
            ServiceRequestPayloadError: If land record query payload is rejected (400/422).
            ServiceResponsePayloadError: If AgriStack returns invalid response schema.
            ServiceUnavailableError: If live AgriStack service fails, times out, or returns 5xx.
            ServiceAuthenticationError: If live AgriStack service returns 401/403.
        """
        logger.info(
            "Live verifying land record=%s for token=%s...",
            land_record_id,
            tokenized_citizen_id[:16],
        )

        payload: dict[str, Any] = {
            "tokenized_citizen_id": tokenized_citizen_id,
            "land_record_id": land_record_id,
        }

        data = await self._transport.post_json(
            _LAND_VERIFY_PATH,
            payload=payload,
            context_label=land_record_id,
        )
        if "is_entitled" in data:
            return bool(data["is_entitled"])

        target_url = self._transport.resolve_url(_LAND_VERIFY_PATH)
        raise ServiceResponsePayloadError(
            f"Live AgriStack verification returned invalid schema from {target_url}.",
            service_name="agristack",
        )


class MockAgriRegistryService:
    """Deterministic local simulation of AgriStack land records for offline testing."""

    async def verify_land_record(self, tokenized_citizen_id: str, land_record_id: str) -> bool:
        """Simulates cadastral verification with deterministic token rules."""
        if (
            not land_record_id.strip()
            or land_record_id.startswith(INVALID_LAND_RECORD_PREFIX)
            or INVALID_SURVEY_NUMBER in land_record_id
        ):
            return False

        if (
            tokenized_citizen_id == UNVERIFIED_IDENTITY_TOKEN_ZERO
            or tokenized_citizen_id.startswith(UNVERIFIED_IDENTITY_PREFIX)
        ):
            return False

        if land_record_id in MOCK_CADASTRAL_REGISTRY:
            return MOCK_CADASTRAL_REGISTRY[land_record_id].is_entitled

        return True


def create_agri_registry_service(
    endpoint_url: str | None = None,
    api_key: str | None = None,
    http_client: AsyncClient | None = None,
    timeout_seconds: float = _DEFAULT_DPI_TIMEOUT_SECONDS,
    require_live: bool | None = None,
) -> AgriRegistryService:
    """Factory creating appropriate AgriStack service implementation based on environment.

    Resolution follows a 3-tier precedence model:
    1. Explicit Parameters: If endpoint_url and api_key are provided directly as arguments,
       constructs LiveAgriRegistryService targeting those coordinates (useful for local
       WireMock, stub proxies, or sandbox integration without enforcing production invariants).
    2. Mandatory Production: If require_live=True (or ENVIRONMENT='production' when omitted),
       constructs LiveAgriRegistryService via environment settings, failing fast if credentials
       are missing.
    3. Offline Simulation: If require_live is False and explicit credentials are not passed
       (even if present in environment variables), returns MockAgriRegistryService to
       guarantee offline test isolation for local development and CI pipelines.
    """
    must_be_live = is_production() if require_live is None else require_live
    if must_be_live:
        return LiveAgriRegistryService.from_env(
            endpoint_url=endpoint_url,
            api_key=api_key,
            http_client=http_client,
            timeout_seconds=timeout_seconds,
        )

    if endpoint_url and api_key:
        return LiveAgriRegistryService(
            endpoint_url=endpoint_url,
            api_key=api_key,
            http_client=http_client or get_shared_http_client(),
            timeout_seconds=timeout_seconds,
        )

    return MockAgriRegistryService()
