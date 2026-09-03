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
from http import HTTPStatus
from typing import Any, Final, Protocol, Self

from httpx import AsyncClient

from src.config.service_settings import (
    get_openspp_api_key,
    get_openspp_endpoint,
    is_production,
)
from src.data_models.caseworker import CaseworkerCaseReviewPayload
from src.errors.service_errors import (
    ServiceAuthenticationError,
    ServiceConfigurationError,
    ServiceRequestPayloadError,
    ServiceResponsePayloadError,
    ServiceUnavailableError,
)
from src.services.dpi.dpi_mock_fixtures import (
    UNVERIFIED_IDENTITY_PREFIX,
    UNVERIFIED_IDENTITY_TOKEN_ZERO,
)
from src.services.http_client_pool import get_shared_http_client

logger = logging.getLogger(__name__)

_DEFAULT_DPI_TIMEOUT_SECONDS: Final[float] = 3.0


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
        if not endpoint_url or not endpoint_url.strip():
            raise ServiceConfigurationError(
                "Live OpenSPP social registry endpoint URL is required.",
                service_name="openspp",
            )
        if not api_key or not api_key.strip():
            raise ServiceConfigurationError(
                "Live OpenSPP social registry API key is required.",
                service_name="openspp",
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
        timeout_seconds: float = _DEFAULT_DPI_TIMEOUT_SECONDS,
    ) -> Self:
        """Factory constructor building live instance from environment settings or overrides."""
        openspp_endpoint = endpoint_url or get_openspp_endpoint()
        openspp_api_key = api_key or get_openspp_api_key()
        if not openspp_endpoint:
            raise ServiceConfigurationError(
                "Live OpenSPP social registry endpoint URL is required in production mode.",
                service_name="openspp",
            )
        if not openspp_api_key:
            raise ServiceConfigurationError(
                "Live OpenSPP social registry API key is required in production mode.",
                service_name="openspp",
            )
        return cls(
            endpoint_url=openspp_endpoint,
            api_key=openspp_api_key,
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

        target_url = f"{self._endpoint_url}/v1/social/eligibility"
        payload: dict[str, Any] = {
            "tokenized_citizen_id": tokenized_citizen_id,
            "scheme_id": scheme_id,
        }

        data = await self._post_json(target_url, payload, scheme_id=scheme_id)
        if "is_eligible" in data:
            return bool(data["is_eligible"])

        raise ServiceResponsePayloadError(
            f"Live OpenSPP registry returned invalid schema from {target_url}.",
            service_name="openspp",
        )

    # -------------------------------------------------------------------------
    # Private Helpers (Shared HTTP Transport)
    # -------------------------------------------------------------------------

    async def _post_json(
        self, url: str, json_data: dict[str, Any], scheme_id: str
    ) -> dict[str, Any]:
        """Executes resilient async POST request with timeout, authentication, and error typing."""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        try:
            response = await self._http_client.post(
                url, json=json_data, headers=headers, timeout=self._timeout_seconds
            )
            if response.status_code == HTTPStatus.OK:
                try:
                    result = response.json()
                    if isinstance(result, dict):
                        return result
                except Exception as err:
                    raise ServiceResponsePayloadError(
                        f"Live OpenSPP registry response from {url} violated schema: {err}",
                        service_name="openspp",
                    ) from err
                raise ServiceResponsePayloadError(
                    f"Live OpenSPP registry returned non-dictionary JSON from {url}.",
                    service_name="openspp",
                )
            if response.status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
                raise ServiceAuthenticationError(
                    f"OpenSPP authentication failed with status={response.status_code}",
                    service_name="openspp",
                    status_code=response.status_code,
                )
            if response.status_code in (
                HTTPStatus.BAD_REQUEST,
                HTTPStatus.UNPROCESSABLE_ENTITY,
            ):
                raise ServiceRequestPayloadError(
                    f"OpenSPP rejected eligibility query with "
                    f"status={response.status_code}: {response.text}",
                    service_name="openspp",
                    status_code=response.status_code,
                )
            raise ServiceUnavailableError(
                f"Live OpenSPP call to {url} failed with "
                f"status={response.status_code}: {response.text}",
                service_name="openspp",
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
            logger.warning("Live social registry call failed for scheme=%s: %s", scheme_id, error)
            raise ServiceUnavailableError(
                f"Live OpenSPP registry call failed for scheme '{scheme_id}': {error}",
                service_name="openspp",
            ) from error


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
