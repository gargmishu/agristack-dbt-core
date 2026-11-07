"""Authoritative DPI Registry: Seasonal Crop & Remote-Sensing Verification Service.

Connects to digital crop survey and remote-sensing landscape monitoring gateways to verify
seasonal crop cultivation and plot-level vegetation stress on registered agricultural parcels.

In production environments, LiveCropVerificationService enforces live HTTPS communication with
strict fail-fast configuration and fail-closed error handling (no mock fallback).
In non-production, MockCropVerificationService provides deterministic offline simulation.

See: decisions/step2.0_canonical_domain_schemas.md (Section 4.3)
See: decisions/step2.3_governance_flows_and_state_transitions.md
See: decisions/step3.7_live_service_integration.md
See: roadmap.md (Phase 3 Step 3.1 Service Abstractions)
"""

import logging
from typing import Any, Final, Protocol, Self

from httpx import AsyncClient

from src.config.service_settings import (
    get_crop_satellite_api_key,
    get_crop_satellite_endpoint,
    is_production,
)
from src.errors.service_errors import ServiceResponsePayloadError
from src.services.dpi.dpi_mock_fixtures import (
    INELIGIBLE_CROP_PREFIX,
    INVALID_LAND_RECORD_PREFIX,
    INVALID_SURVEY_NUMBER,
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
    "CropVerificationService",
    "LiveCropVerificationService",
    "MockCropVerificationService",
    "create_crop_verification_service",
]

_DEFAULT_DPI_TIMEOUT_SECONDS: Final[float] = 3.0
_CROP_VERIFY_PATH: Final[str] = "/v1/crop-satellite/verify"


class CropVerificationService(Protocol):
    """Protocol contract for seasonal crop survey and remote-sensing verification operations."""

    async def verify_crop_cultivation(
        self,
        tokenized_citizen_id: str,
        land_record_id: str,
        crop_name: str,
        active_season: str = "KHARIF-2026",
    ) -> bool:
        """Verifies seasonal crop sowing and remote-sensing landscape cultivation on a plot."""
        ...


class LiveCropVerificationService:
    """Production live client executing HTTPS calls to remote-sensing crop verification gateways.

    Strictly requires endpoint URL, API key, and pooled HTTP client. Fails closed with
    ServiceUnavailableError on network errors, timeouts, or remote outages, raises
    ServiceRequestPayloadError on malformed crop verification requests (400/422),
    and raises ServiceResponsePayloadError on schema contract violations (502).
    """

    def __init__(
        self,
        endpoint_url: str,
        api_key: str,
        http_client: AsyncClient,
        timeout_seconds: float = _DEFAULT_DPI_TIMEOUT_SECONDS,
    ) -> None:
        """Initializes live crop verification client with mandatory credentials and transport."""
        self._transport = ServiceHttpTransport(
            http_client=http_client,
            api_key=api_key,
            config=ServiceTransportConfig(
                service_name="crop_satellite",
                service_title="Crop Satellite Verification",
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
            endpoint_url=endpoint_url or get_crop_satellite_endpoint() or "",
            api_key=api_key or get_crop_satellite_api_key() or "",
            http_client=http_client or get_shared_http_client(),
            timeout_seconds=timeout_seconds,
        )

    # -------------------------------------------------------------------------
    # Primary Public Workflow Entrypoints
    # -------------------------------------------------------------------------

    async def verify_crop_cultivation(
        self,
        tokenized_citizen_id: str,
        land_record_id: str,
        crop_name: str,
        active_season: str = "KHARIF-2026",
    ) -> bool:
        """Verifies seasonal crop sowing and remote-sensing cultivation status via live API.

        Queries the digital crop survey and remote-sensing landscape monitoring gateway
        to confirm that the claimed crop was actively cultivated on the specified plot
        during the active agricultural season.

        Args:
            tokenized_citizen_id: 64-character SHA-256 HMAC citizen identity token.
            land_record_id: Land record survey/plot identifier.
            crop_name: Claimed agricultural crop variety.
            active_season: Active agricultural season identifier (e.g., 'KHARIF-2026').

        Returns:
            True if seasonal crop cultivation and remote-sensing verification pass, False otherwise.

        Raises:
            ServiceRequestPayloadError: If crop verification payload is rejected (400/422).
            ServiceResponsePayloadError: If remote-sensing gateway returns invalid schema.
            ServiceUnavailableError: If remote-sensing gateway fails, times out, or returns 5xx.
            ServiceAuthenticationError: If remote-sensing gateway returns 401/403.
        """
        logger.info(
            "Live verifying crop=%s season=%s on land_record=%s for token=%s...",
            crop_name,
            active_season,
            land_record_id,
            tokenized_citizen_id[:16],
        )

        payload: dict[str, Any] = {
            "tokenized_citizen_id": tokenized_citizen_id,
            "land_record_id": land_record_id,
            "crop_name": crop_name,
            "active_season": active_season,
        }

        response_data = await self._transport.post_json(
            _CROP_VERIFY_PATH,
            payload=payload,
            context_label=f"{land_record_id}:{crop_name}",
        )
        if "is_crop_verified" in response_data:
            return bool(response_data["is_crop_verified"])

        target_url = self._transport.resolve_url(_CROP_VERIFY_PATH)
        raise ServiceResponsePayloadError(
            f"Live crop satellite verification returned invalid schema from {target_url}.",
            service_name="crop_satellite",
        )


class MockCropVerificationService:
    """Deterministic local simulation of seasonal crop and remote-sensing checks."""

    async def verify_crop_cultivation(
        self,
        tokenized_citizen_id: str,
        land_record_id: str,
        crop_name: str,
        active_season: str = "KHARIF-2026",
    ) -> bool:
        """Simulates seasonal crop survey and remote-sensing verification rules."""
        normalized_crop = crop_name.strip().upper()
        return bool(
            normalized_crop
            and active_season.strip()
            and land_record_id.strip()
            and not normalized_crop.startswith(INELIGIBLE_CROP_PREFIX)
            and not land_record_id.startswith(INVALID_LAND_RECORD_PREFIX)
            and INVALID_SURVEY_NUMBER not in land_record_id
            and tokenized_citizen_id != UNVERIFIED_IDENTITY_TOKEN_ZERO
            and not tokenized_citizen_id.startswith(UNVERIFIED_IDENTITY_PREFIX)
        )


def create_crop_verification_service(
    endpoint_url: str | None = None,
    api_key: str | None = None,
    http_client: AsyncClient | None = None,
    timeout_seconds: float = _DEFAULT_DPI_TIMEOUT_SECONDS,
    require_live: bool | None = None,
) -> CropVerificationService:
    """Factory creating appropriate crop verification service implementation based on environment.

    Resolution follows a 3-tier precedence model:
    1. Mandatory Production: If require_live=True (or ENVIRONMENT='production' is set),
       constructs LiveCropVerificationService via environment settings, failing fast if credentials
       are missing.
    2. Explicit Parameters: If endpoint_url and api_key are provided directly as arguments,
       constructs LiveCropVerificationService targeting those coordinates.
    3. Offline Simulation: If require_live is False and explicit credentials are not passed,
       returns MockCropVerificationService to guarantee offline test isolation.
    """
    must_be_live = is_production() if require_live is None else require_live
    if must_be_live:
        return LiveCropVerificationService.from_env(
            endpoint_url=endpoint_url,
            api_key=api_key,
            http_client=http_client,
            timeout_seconds=timeout_seconds,
        )

    if endpoint_url and api_key:
        return LiveCropVerificationService(
            endpoint_url=endpoint_url,
            api_key=api_key,
            http_client=http_client or get_shared_http_client(),
            timeout_seconds=timeout_seconds,
        )

    return MockCropVerificationService()
