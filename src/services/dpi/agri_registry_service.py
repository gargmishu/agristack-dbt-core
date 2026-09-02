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
from src.errors.service_errors import (
    ServiceAuthenticationError,
    ServiceConfigurationError,
    ServiceRequestPayloadError,
    ServiceResponsePayloadError,
    ServiceUnavailableError,
)
from src.services.dpi.dpi_mock_fixtures import (
    INVALID_LAND_RECORD_PREFIX,
    INVALID_SURVEY_NUMBER,
    MOCK_CADASTRAL_REGISTRY,
    UNVERIFIED_IDENTITY_PREFIX,
    UNVERIFIED_IDENTITY_TOKEN_ZERO,
)
from src.services.http_client_pool import get_shared_http_client

logger = logging.getLogger(__name__)

_DEFAULT_DPI_TIMEOUT_SECONDS: Final[float] = 3.0
_HTTP_STATUS_OK: Final[int] = 200
_HTTP_STATUS_BAD_REQUEST: Final[int] = 400
_HTTP_STATUS_UNAUTHORIZED: Final[int] = 401
_HTTP_STATUS_FORBIDDEN: Final[int] = 403
_HTTP_STATUS_UNPROCESSABLE_ENTITY: Final[int] = 422


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
        if not endpoint_url or not endpoint_url.strip():
            raise ServiceConfigurationError(
                "Live AgriStack registry endpoint URL is required.",
                service_name="agristack",
            )
        if not api_key or not api_key.strip():
            raise ServiceConfigurationError(
                "Live AgriStack registry API key is required.",
                service_name="agristack",
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
        agristack_endpoint = endpoint_url or get_agristack_endpoint()
        agristack_api_key = api_key or get_agristack_api_key()
        if not agristack_endpoint:
            raise ServiceConfigurationError(
                "Live AgriStack registry endpoint URL is required in production mode.",
                service_name="agristack",
            )
        if not agristack_api_key:
            raise ServiceConfigurationError(
                "Live AgriStack registry API key is required in production mode.",
                service_name="agristack",
            )
        return cls(
            endpoint_url=agristack_endpoint,
            api_key=agristack_api_key,
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

        target_url = f"{self._endpoint_url}/v1/land/cadastral/verify"
        payload: dict[str, Any] = {
            "tokenized_citizen_id": tokenized_citizen_id,
            "land_record_id": land_record_id,
        }

        data = await self._post_json(target_url, payload, record_id=land_record_id)
        if "is_entitled" in data:
            return bool(data["is_entitled"])

        raise ServiceResponsePayloadError(
            f"Live AgriStack verification returned invalid schema from {target_url}.",
            service_name="agristack",
        )

    # -------------------------------------------------------------------------
    # Private Helpers (Shared HTTP Transport)
    # -------------------------------------------------------------------------

    async def _post_json(
        self, url: str, json_data: dict[str, Any], record_id: str
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
            if response.status_code == _HTTP_STATUS_OK:
                try:
                    result = response.json()
                    if isinstance(result, dict):
                        return result
                except Exception as err:
                    raise ServiceResponsePayloadError(
                        f"Live AgriStack verification response from {url} violated schema: {err}",
                        service_name="agristack",
                    ) from err
                raise ServiceResponsePayloadError(
                    f"Live AgriStack verification returned non-dictionary JSON from {url}.",
                    service_name="agristack",
                )
            if response.status_code in (_HTTP_STATUS_UNAUTHORIZED, _HTTP_STATUS_FORBIDDEN):
                raise ServiceAuthenticationError(
                    f"AgriStack verification failed with status={response.status_code}",
                    service_name="agristack",
                    status_code=response.status_code,
                )
            if response.status_code in (
                _HTTP_STATUS_BAD_REQUEST,
                _HTTP_STATUS_UNPROCESSABLE_ENTITY,
            ):
                raise ServiceRequestPayloadError(
                    f"AgriStack rejected land record query with "
                    f"status={response.status_code}: {response.text}",
                    service_name="agristack",
                    status_code=response.status_code,
                )
            raise ServiceUnavailableError(
                f"Live AgriStack call to {url} failed with "
                f"status={response.status_code}: {response.text}",
                service_name="agristack",
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
            logger.warning("Live cadastral call failed for record=%s: %s", record_id, error)
            raise ServiceUnavailableError(
                f"Live AgriStack call failed for record '{record_id}': {error}",
                service_name="agristack",
            ) from error


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
