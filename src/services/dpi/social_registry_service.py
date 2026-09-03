"""Authoritative DPI Registry: OpenSPP Social Registry Service.

Provides the external Digital Public Infrastructure (DPI) boundary connector for
OpenSPP (Open Social Protection Platform) and sovereign social welfare registries.

This service is dedicated to checking citizen social protection eligibility against
the external registry boundary. It does not own case review lifecycle state.

In production environments, enforces live HTTPS communication via LiveSocialRegistryService with
strict fail-fast configuration and fail-closed error handling (no mock fallback).
In non-production, MockSocialRegistryService provides deterministic simulation for offline testing.

See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.2)
See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.3)
See: decisions/step3.6_live_service_integration.md
See: roadmap.md (Phase 3 Step 3.1 Service Abstractions)
"""

import logging
from typing import Any, Final, Protocol, Self

from httpx import AsyncClient

from src.config.service_settings import (
    get_openspp_api_key,
    get_openspp_endpoint,
    is_production,
)
from src.data_models.caseworker import CaseworkerCaseReviewPayload
from src.errors.service_errors import ServiceResponsePayloadError
from src.services.dpi.dpi_mock_fixtures import (
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
    "LiveSocialRegistryService",
    "MockSocialRegistryService",
    "SocialRegistryService",
    "create_social_registry_service",
]

_DEFAULT_DPI_TIMEOUT_SECONDS: Final[float] = 3.0
_SOCIAL_ELIGIBILITY_PATH: Final[str] = "/v1/social/eligibility"


class SocialRegistryService(Protocol):
    """Protocol contract for social protection platform entitlement verification.

    Queries external social registries for citizen welfare scheme eligibility.
    """

    async def verify_incident_ticket_eligibility(
        self, case_review: CaseworkerCaseReviewPayload
    ) -> bool:
        """Queries external registry for beneficiary eligibility for a staged incident ticket."""
        ...

    async def query_beneficiary_eligibility(
        self, tokenized_citizen_id: str, scheme_id: str
    ) -> bool:
        """Queries external social registry for beneficiary entitlement under a specific scheme."""
        ...


class LiveSocialRegistryService:
    """Production live client executing HTTPS calls to sovereign OpenSPP registry gateways.

    Strictly requires endpoint URL, API key, and pooled HTTP client. Fails closed with
    ServiceUnavailableError on network errors, timeouts, or remote outages, raises
    ServiceRequestPayloadError on malformed scheme queries or unprocessable payloads (400/422),
    and raises ServiceResponsePayloadError on schema contract violations (502).
    """

    def __init__(
        self,
        endpoint_url: str,
        api_key: str,
        http_client: AsyncClient,
        timeout_seconds: float = _DEFAULT_DPI_TIMEOUT_SECONDS,
    ) -> None:
        """Initializes live OpenSPP registry client with mandatory credentials and transport."""
        self._transport = ServiceHttpTransport(
            http_client=http_client,
            api_key=api_key,
            config=ServiceTransportConfig(
                service_name="openspp",
                service_title="OpenSPP",
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
            endpoint_url=endpoint_url or get_openspp_endpoint() or "",
            api_key=api_key or get_openspp_api_key() or "",
            http_client=http_client or get_shared_http_client(),
            timeout_seconds=timeout_seconds,
        )

    # -------------------------------------------------------------------------
    # Primary Public Workflow Entrypoints
    # -------------------------------------------------------------------------

    async def verify_incident_ticket_eligibility(
        self, case_review: CaseworkerCaseReviewPayload
    ) -> bool:
        """Queries live OpenSPP registry for staged incident ticket eligibility."""
        logger.info(
            "Live evaluating eligibility for incident ticket=%s via OpenSPP for session=%s",
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
        """Queries live OpenSPP registry for beneficiary entitlement under a specific scheme.

        Args:
            tokenized_citizen_id: 64-character SHA-256 HMAC citizen token.
            scheme_id: Identifier of the target social protection scheme.

        Returns:
            True if citizen is registered and entitled, False otherwise.

        Raises:
            ServiceRequestPayloadError: If query payload is rejected as unprocessable (400/422).
            ServiceResponsePayloadError: If OpenSPP returns invalid response schema.
            ServiceUnavailableError: If live OpenSPP service fails, times out, or returns 5xx.
            ServiceAuthenticationError: If live OpenSPP service returns 401/403.
        """
        logger.info(
            "Live querying OpenSPP scheme=%s eligibility for token=%s",
            scheme_id,
            tokenized_citizen_id[:16],
        )

        payload: dict[str, Any] = {
            "tokenized_citizen_id": tokenized_citizen_id,
            "scheme_id": scheme_id,
        }

        data = await self._transport.post_json(
            _SOCIAL_ELIGIBILITY_PATH,
            payload=payload,
            context_label=scheme_id,
        )
        if "is_eligible" in data:
            return bool(data["is_eligible"])

        target_url = self._transport.resolve_url(_SOCIAL_ELIGIBILITY_PATH)
        raise ServiceResponsePayloadError(
            f"Live OpenSPP registry returned invalid schema from {target_url}.",
            service_name="openspp",
        )


class MockSocialRegistryService:
    """Deterministic local social registry simulation for offline testing."""

    async def verify_incident_ticket_eligibility(
        self, case_review: CaseworkerCaseReviewPayload
    ) -> bool:
        """Simulates eligibility verification for a staged incident ticket."""
        return await self.query_beneficiary_eligibility(
            case_review.tokenized_citizen_id,
            str(case_review.application_intent),
        )

    async def query_beneficiary_eligibility(
        self, tokenized_citizen_id: str, scheme_id: str
    ) -> bool:
        """Simulates beneficiary entitlement check with deterministic token rules."""
        return bool(
            tokenized_citizen_id != UNVERIFIED_IDENTITY_TOKEN_ZERO
            and not tokenized_citizen_id.startswith(UNVERIFIED_IDENTITY_PREFIX)
            and scheme_id.strip()
        )


def create_social_registry_service(
    endpoint_url: str | None = None,
    api_key: str | None = None,
    http_client: AsyncClient | None = None,
    timeout_seconds: float = _DEFAULT_DPI_TIMEOUT_SECONDS,
    require_live: bool | None = None,
) -> SocialRegistryService:
    """Factory creating appropriate social registry service implementation based on environment.

    Resolution follows a 3-tier precedence model:
    1. Explicit Parameters: If endpoint_url and api_key are provided directly as arguments,
       constructs LiveSocialRegistryService targeting those coordinates (useful for local
       WireMock, stub proxies, or sandbox integration without enforcing production invariants).
    2. Mandatory Production: If require_live=True (or ENVIRONMENT='production' when omitted),
       constructs LiveSocialRegistryService via environment settings, failing fast if credentials
       are missing.
    3. Offline Simulation: If require_live is False and explicit credentials are not passed
       (even if present in environment variables), returns MockSocialRegistryService to
       guarantee offline test isolation for local development and CI pipelines.
    """
    must_be_live = is_production() if require_live is None else require_live
    if must_be_live:
        return LiveSocialRegistryService.from_env(
            endpoint_url=endpoint_url,
            api_key=api_key,
            http_client=http_client,
            timeout_seconds=timeout_seconds,
        )

    if endpoint_url and api_key:
        return LiveSocialRegistryService(
            endpoint_url=endpoint_url,
            api_key=api_key,
            http_client=http_client or get_shared_http_client(),
            timeout_seconds=timeout_seconds,
        )

    return MockSocialRegistryService()
