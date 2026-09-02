"""Authoritative DPI Registry: MOSIP Sovereign Identity Verification Service.

Connects to the national Modular Open Source Identity Platform (MOSIP) to verify
citizen identity tokens without transmitting raw PII across network boundaries.

In production environments, LiveIdentityVerificationService enforces live HTTPS communication with
strict fail-fast configuration and fail-closed error handling (no mock fallback).
In non-production, MockIdentityVerificationService provides deterministic simulation for
offline testing.

See: decisions/step0.3_zero_trust_tokenization.md
See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.1)
See: decisions/step3.6_live_service_integration.md
See: roadmap.md (Phase 3 Step 3.1 Service Abstractions)
"""

import logging
from typing import Any, Final, Protocol, Self

from httpx import AsyncClient

from src.config.service_settings import (
    get_identity_api_key,
    get_identity_endpoint,
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
_HMAC_TOKEN_HEX_LENGTH: Final[int] = 64


class IdentityVerificationService(Protocol):
    """Protocol contract for sovereign identity registry verification operations."""

    async def verify_identity_token(self, tokenized_citizen_id: str) -> bool:
        """Verifies if citizen identity token exists in authoritative registry."""
        ...


class LiveIdentityVerificationService:
    """Production live client executing HTTPS calls to sovereign MOSIP identity gateways.

    Strictly requires endpoint URL, API key, and pooled HTTP client. Fails closed with
    ServiceUnavailableError on network errors, timeouts, or remote outages, raises
    ServiceRequestPayloadError on malformed identity tokens or unprocessable payloads (400/422),
    and raises ServiceResponsePayloadError on schema contract violations (502).
    """

    def __init__(
        self,
        endpoint_url: str,
        api_key: str,
        http_client: AsyncClient,
        timeout_seconds: float = _DEFAULT_DPI_TIMEOUT_SECONDS,
    ) -> None:
        """Initializes live identity client with mandatory credentials and transport."""
        if not endpoint_url or not endpoint_url.strip():
            raise ServiceConfigurationError(
                "Live MOSIP identity verification endpoint URL is required.",
                service_name="mosip",
            )
        if not api_key or not api_key.strip():
            raise ServiceConfigurationError(
                "Live MOSIP identity verification API key is required.",
                service_name="mosip",
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
        mosip_endpoint = endpoint_url or get_identity_endpoint()
        mosip_api_key = api_key or get_identity_api_key()
        if not mosip_endpoint:
            raise ServiceConfigurationError(
                "Live MOSIP identity verification endpoint URL is required in production mode.",
                service_name="mosip",
            )
        if not mosip_api_key:
            raise ServiceConfigurationError(
                "Live MOSIP identity verification API key is required in production mode.",
                service_name="mosip",
            )
        return cls(
            endpoint_url=mosip_endpoint,
            api_key=mosip_api_key,
            http_client=http_client or get_shared_http_client(),
            timeout_seconds=timeout_seconds,
        )

    # -------------------------------------------------------------------------
    # Primary Public Workflow Entrypoints
    # -------------------------------------------------------------------------

    async def verify_identity_token(self, tokenized_citizen_id: str) -> bool:
        """Verifies if citizen identity token exists in authoritative registry via live API.

        Args:
            tokenized_citizen_id: 64-character SHA-256 HMAC citizen identity token.

        Returns:
            True if identity token is verified and active in registry, False otherwise.

        Raises:
            ServiceRequestPayloadError: If citizen token is rejected as malformed (400/422).
            ServiceResponsePayloadError: If MOSIP returns invalid response schema.
            ServiceUnavailableError: If live MOSIP service fails, times out, or returns 5xx.
            ServiceAuthenticationError: If live MOSIP service returns 401/403.
        """
        logger.info("Live verifying identity token=%s...", tokenized_citizen_id[:16])

        target_url = f"{self._endpoint_url}/v1/identity/verify"
        payload: dict[str, Any] = {"tokenized_citizen_id": tokenized_citizen_id}
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
                    if isinstance(data, dict) and "is_verified" in data:
                        return bool(data["is_verified"])
                except Exception as err:
                    raise ServiceResponsePayloadError(
                        f"Live MOSIP verification response from {target_url} "
                        f"violated schema: {err}",
                        service_name="mosip",
                    ) from err
                raise ServiceResponsePayloadError(
                    f"Live MOSIP verification returned invalid schema from {target_url}.",
                    service_name="mosip",
                )
            if response.status_code in (_HTTP_STATUS_UNAUTHORIZED, _HTTP_STATUS_FORBIDDEN):
                raise ServiceAuthenticationError(
                    f"MOSIP verification failed with status={response.status_code}",
                    service_name="mosip",
                    status_code=response.status_code,
                )
            if response.status_code in (
                _HTTP_STATUS_BAD_REQUEST,
                _HTTP_STATUS_UNPROCESSABLE_ENTITY,
            ):
                raise ServiceRequestPayloadError(
                    f"MOSIP rejected identity payload with "
                    f"status={response.status_code}: {response.text}",
                    service_name="mosip",
                    status_code=response.status_code,
                )
            raise ServiceUnavailableError(
                f"Live MOSIP call to {target_url} failed with "
                f"status={response.status_code}: {response.text}",
                service_name="mosip",
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
                "Live identity call failed for token=%s...: %s", tokenized_citizen_id[:16], error
            )
            raise ServiceUnavailableError(
                f"Live MOSIP call failed for token '{tokenized_citizen_id[:16]}': {error}",
                service_name="mosip",
            ) from error


class MockIdentityVerificationService:
    """Deterministic local identity verification simulation for offline testing."""

    async def verify_identity_token(self, tokenized_citizen_id: str) -> bool:
        """Simulates identity verification with deterministic HMAC prefix rules."""
        if not tokenized_citizen_id.strip():
            return False

        if (
            tokenized_citizen_id == UNVERIFIED_IDENTITY_TOKEN_ZERO
            or tokenized_citizen_id.startswith(UNVERIFIED_IDENTITY_PREFIX)
        ):
            return False

        return len(tokenized_citizen_id) == _HMAC_TOKEN_HEX_LENGTH


def create_identity_verification_service(
    endpoint_url: str | None = None,
    api_key: str | None = None,
    http_client: AsyncClient | None = None,
    timeout_seconds: float = _DEFAULT_DPI_TIMEOUT_SECONDS,
    require_live: bool | None = None,
) -> IdentityVerificationService:
    """Factory creating appropriate identity service implementation based on environment.

    Resolution follows a 3-tier precedence model:
    1. Explicit Parameters: If endpoint_url and api_key are provided directly as arguments,
       constructs LiveIdentityVerificationService targeting those coordinates (useful for local
       WireMock, stub proxies, or sandbox integration without enforcing production invariants).
    2. Mandatory Production: If require_live=True (or ENVIRONMENT='production' when omitted),
       constructs LiveIdentityVerificationService via environment settings, failing fast if
       credentials are missing.
    3. Offline Simulation: If require_live is False and explicit credentials are not passed
       (even if present in environment variables), returns MockIdentityVerificationService to
       guarantee offline test isolation for local development and CI pipelines.
    """
    must_be_live = is_production() if require_live is None else require_live
    if must_be_live:
        return LiveIdentityVerificationService.from_env(
            endpoint_url=endpoint_url,
            api_key=api_key,
            http_client=http_client,
            timeout_seconds=timeout_seconds,
        )

    if endpoint_url and api_key:
        return LiveIdentityVerificationService(
            endpoint_url=endpoint_url,
            api_key=api_key,
            http_client=http_client or get_shared_http_client(),
            timeout_seconds=timeout_seconds,
        )

    return MockIdentityVerificationService()
