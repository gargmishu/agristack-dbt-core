"""Authoritative DPI Registry: Identity Verification Service.

Provides Zero-PII identity token verification against authoritative MOSIP/Aadhaar
registries.

Why operate exclusively on Zero-PII HMAC tokens?
Cleartext PII (phone numbers, Aadhaar numbers, cleartext names) is strictly forbidden from
touching persistent database ledgers or disk storage under Aadhaar Act §29 and national
privacy mandates. While active tokenization occurs at the Layer 2 perimeter,
all downstream registry verification operates exclusively on pre-computed 64-character hex
tokens (`HmacCitizenToken`).

See: decisions/step0.3_zero_trust_tokenization.md
See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.1)
See: roadmap.md (Phase 3 Step 3.1 Service Abstractions)
"""

import logging
from typing import Any, Final

import httpx

from src.services.dpi.dpi_mock_fixtures import (
    UNVERIFIED_IDENTITY_PREFIX,
    UNVERIFIED_IDENTITY_TOKEN_ZERO,
)

logger = logging.getLogger(__name__)

_DEFAULT_DPI_TIMEOUT_SECONDS: Final[float] = 3.0
_HTTP_STATUS_OK: Final[int] = 200


class IdentityVerificationService:
    """Service client for sovereign identity registry verification.

    Verifies active citizen registration using pseudonymous 64-character SHA-256 HMAC tokens.

    Supports live REST endpoints with automatic, graceful fallback to deterministic local fixtures.

    See: decisions/step0.3_zero_trust_tokenization.md
    See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.1)
    See: decisions/step3.6_live_service_integration.md
    """

    def __init__(
        self,
        endpoint_url: str | None = None,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        timeout_seconds: float = _DEFAULT_DPI_TIMEOUT_SECONDS,
    ) -> None:
        """Initializes identity verification client with optional live endpoint configuration.

        Args:
            endpoint_url: Optional base HTTP URL for live MOSIP/Aadhaar identity service.
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

    async def verify_identity_token(self, tokenized_citizen_id: str) -> bool:
        """Verifies if tokenized citizen identity token exists in authoritative registry.

        Args:
            tokenized_citizen_id: 64-character SHA-256 HMAC citizen identity token.

        Returns:
            True if identity token is verified and active in registry, False otherwise.
        """
        logger.info("Verifying identity token=%s...", tokenized_citizen_id[:16])

        if self._endpoint_url:
            live_result = await self._call_live_verify(tokenized_citizen_id)
            if live_result is not None:
                return live_result

        return self._mock_verify_identity_token(tokenized_citizen_id)

    # -------------------------------------------------------------------------
    # Private Helpers (Live HTTP & Local Mock Handlers)
    # -------------------------------------------------------------------------

    async def _call_live_verify(self, tokenized_citizen_id: str) -> bool | None:
        """Dispatches live identity verification HTTP request with graceful fallback."""
        target_url = f"{self._endpoint_url}/v1/identity/verify"
        payload: dict[str, Any] = {"tokenized_citizen_id": tokenized_citizen_id}
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
                if isinstance(data, dict) and "is_verified" in data:
                    return bool(data["is_verified"])
            logger.warning(
                "Live identity verification returned status=%d for token=%s...",
                response.status_code,
                tokenized_citizen_id[:16],
            )
        except Exception as error:
            logger.warning(
                "Live identity call failed for token=%s...: %s; using mock fallback",
                tokenized_citizen_id[:16],
                error,
            )
        return None

    @staticmethod
    def _mock_verify_identity_token(tokenized_citizen_id: str) -> bool:
        """Deterministic local identity verification simulation."""
        is_verified = (
            tokenized_citizen_id != UNVERIFIED_IDENTITY_TOKEN_ZERO
            and not tokenized_citizen_id.startswith(UNVERIFIED_IDENTITY_PREFIX)
        )
        if not is_verified:
            logger.warning(
                "Identity verification rejected for token=%s...",
                tokenized_citizen_id[:16],
            )
        return is_verified
