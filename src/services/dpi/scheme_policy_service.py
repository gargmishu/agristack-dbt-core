"""Authoritative DPI Registry: Scheme Policy & Calamity Notification Service.

Connects to harmonized scheme policy metadata and Model Context Protocol (MCP) endpoints
to verify whether a district and crop variety are covered under active calamity relief rules.

In production environments, LiveSchemePolicyService enforces live HTTPS communication with
strict fail-fast configuration and fail-closed error handling (no mock fallback).
In non-production, MockSchemePolicyService provides deterministic simulation for offline testing.

See: decisions/step2.0_canonical_domain_schemas.md (Section 4.3)
See: decisions/step2.3_governance_flows_and_state_transitions.md
See: decisions/step3.7_live_service_integration.md
See: roadmap.md (Phase 3 Step 3.1 Service Abstractions)
"""

import logging
from typing import Any, Final, Protocol, Self

from httpx import AsyncClient

from src.config.service_settings import (
    get_scheme_policy_api_key,
    get_scheme_policy_endpoint,
    is_production,
)
from src.errors.service_errors import ServiceResponsePayloadError
from src.services.dpi.dpi_mock_fixtures import EXCLUDED_POLICY_PREFIX
from src.services.http_transport import (
    ServiceHttpTransport,
    ServiceTransportConfig,
    get_shared_http_client,
)

logger = logging.getLogger(__name__)

__all__ = [
    "LiveSchemePolicyService",
    "MockSchemePolicyService",
    "SchemePolicyService",
    "create_scheme_policy_service",
]

_DEFAULT_DPI_TIMEOUT_SECONDS: Final[float] = 3.0
_SCHEME_POLICY_VERIFY_PATH: Final[str] = "/v1/scheme-policy/verify"


class SchemePolicyService(Protocol):
    """Protocol contract for machine-readable scheme policy and calamity coverage verification."""

    async def verify_scheme_policy_coverage(
        self,
        district: str,
        crop_name: str,
        active_season: str = "KHARIF-2026",
    ) -> bool:
        """Queries harmonized scheme policy metadata to verify district and crop coverage."""
        ...


class LiveSchemePolicyService:
    """Production live client executing HTTPS calls to scheme policy metadata gateways.

    Strictly requires endpoint URL, API key, and pooled HTTP client. Fails closed with
    ServiceUnavailableError on network errors, timeouts, or remote outages, raises
    ServiceRequestPayloadError on malformed policy queries (400/422),
    and raises ServiceResponsePayloadError on schema contract violations (502).
    """

    def __init__(
        self,
        endpoint_url: str,
        api_key: str,
        http_client: AsyncClient,
        timeout_seconds: float = _DEFAULT_DPI_TIMEOUT_SECONDS,
    ) -> None:
        """Initializes live scheme policy client with mandatory credentials and transport."""
        self._transport = ServiceHttpTransport(
            http_client=http_client,
            api_key=api_key,
            config=ServiceTransportConfig(
                service_name="scheme_policy",
                service_title="Scheme Policy Metadata",
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
            endpoint_url=endpoint_url or get_scheme_policy_endpoint() or "",
            api_key=api_key or get_scheme_policy_api_key() or "",
            http_client=http_client or get_shared_http_client(),
            timeout_seconds=timeout_seconds,
        )

    # -------------------------------------------------------------------------
    # Primary Public Workflow Entrypoints
    # -------------------------------------------------------------------------

    async def verify_scheme_policy_coverage(
        self,
        district: str,
        crop_name: str,
        active_season: str = "KHARIF-2026",
    ) -> bool:
        """Verifies whether a district and crop are covered under active scheme policy rules.

        Queries the NMDS 2.0 / Model Context Protocol (MCP) scheme policy table endpoint
        to confirm that the administrative district and crop variety are eligible for
        relief under the active seasonal notification.

        Args:
            district: Administrative district name or Local Government Directory (LGD) code.
            crop_name: Claimed agricultural crop variety.
            active_season: Active agricultural season identifier (e.g., 'KHARIF-2026').

        Returns:
            True if the district and crop are covered by the active scheme policy, False otherwise.

        Raises:
            ServiceRequestPayloadError: If policy query payload is rejected (400/422).
            ServiceResponsePayloadError: If policy endpoint returns invalid response schema.
            ServiceUnavailableError: If policy endpoint fails, times out, or returns 5xx.
            ServiceAuthenticationError: If policy endpoint returns 401/403.
        """
        logger.info(
            "Live querying scheme policy coverage for district=%s crop=%s season=%s",
            district,
            crop_name,
            active_season,
        )

        payload: dict[str, Any] = {
            "district": district,
            "crop_name": crop_name,
            "active_season": active_season,
        }

        response_data = await self._transport.post_json(
            _SCHEME_POLICY_VERIFY_PATH,
            payload=payload,
            context_label=f"{district}:{crop_name}",
        )
        if "is_policy_covered" in response_data:
            return bool(response_data["is_policy_covered"])

        target_url = self._transport.resolve_url(_SCHEME_POLICY_VERIFY_PATH)
        raise ServiceResponsePayloadError(
            f"Live scheme policy check returned invalid schema from {target_url}.",
            service_name="scheme_policy",
        )


class MockSchemePolicyService:
    """Deterministic local simulation of harmonized scheme policy coverage rules."""

    async def verify_scheme_policy_coverage(
        self,
        district: str,
        crop_name: str,
        active_season: str = "KHARIF-2026",
    ) -> bool:
        """Simulates harmonized scheme policy table coverage rules for offline testing."""
        normalized_district = district.strip().upper()
        normalized_crop = crop_name.strip().upper()
        return bool(
            normalized_district
            and normalized_crop
            and active_season.strip()
            and not normalized_district.startswith(EXCLUDED_POLICY_PREFIX)
            and not normalized_crop.startswith(EXCLUDED_POLICY_PREFIX)
        )


def create_scheme_policy_service(
    endpoint_url: str | None = None,
    api_key: str | None = None,
    http_client: AsyncClient | None = None,
    timeout_seconds: float = _DEFAULT_DPI_TIMEOUT_SECONDS,
    require_live: bool | None = None,
) -> SchemePolicyService:
    """Factory creating appropriate scheme policy service implementation based on environment.

    Resolution follows a 3-tier precedence model:
    1. Mandatory Production: If require_live=True (or ENVIRONMENT='production' is set),
       constructs LiveSchemePolicyService via environment settings, failing fast if credentials
       are missing.
    2. Explicit Parameters: If endpoint_url and api_key are provided directly as arguments,
       constructs LiveSchemePolicyService targeting those coordinates.
    3. Offline Simulation: If require_live is False and explicit credentials are not passed,
       returns MockSchemePolicyService to guarantee offline test isolation.
    """
    must_be_live = is_production() if require_live is None else require_live
    if must_be_live:
        return LiveSchemePolicyService.from_env(
            endpoint_url=endpoint_url,
            api_key=api_key,
            http_client=http_client,
            timeout_seconds=timeout_seconds,
        )

    if endpoint_url and api_key:
        return LiveSchemePolicyService(
            endpoint_url=endpoint_url,
            api_key=api_key,
            http_client=http_client or get_shared_http_client(),
            timeout_seconds=timeout_seconds,
        )

    return MockSchemePolicyService()
