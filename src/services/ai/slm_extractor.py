"""Layer 3 AI Perception: Sovereign Small Language Model (SLM) Entity Extractor.

Parses unstructured vernacular text into structured domain entities and intent contracts.

In production environments, LiveSlmExtractor enforces live HTTPS communication with
strict fail-fast configuration and fail-closed error handling (no mock fallback).
In non-production, MockSlmExtractor provides deterministic simulation for offline testing.

See: decisions/step2.0_canonical_domain_schemas.md (Section 3.5)
See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.1)
See: decisions/step3.6_live_service_integration.md
See: roadmap.md (Phase 2 Step 2.2 Service Abstractions)
"""

import logging
from typing import Final, Protocol, Self

import httpx

from src.config.service_settings import (
    get_slm_api_key,
    get_slm_endpoint,
    is_production,
)
from src.data_models.governance import ExtractedEntityPayload
from src.errors.service_errors import (
    ServiceAuthenticationError,
    ServiceConfigurationError,
    ServiceRequestPayloadError,
    ServiceResponsePayloadError,
    ServiceUnavailableError,
)
from src.services.ai.ai_mock_fixtures import (
    ADVERSARIAL_INJECTION_KEYWORDS,
    MISSING_ENTITY_KEYWORDS,
    MOCK_SLM_RULES,
    STATUS_CHECK_KEYWORDS,
    SUBSIDY_CLAIM_KEYWORDS,
)
from src.services.http_client_pool import get_shared_http_client

logger = logging.getLogger(__name__)

_DEFAULT_AI_TIMEOUT_SECONDS: Final[float] = 2.0
_HTTP_STATUS_OK: Final[int] = 200
_HTTP_STATUS_BAD_REQUEST: Final[int] = 400
_HTTP_STATUS_UNAUTHORIZED: Final[int] = 401
_HTTP_STATUS_FORBIDDEN: Final[int] = 403
_HTTP_STATUS_UNPROCESSABLE_ENTITY: Final[int] = 422


class SlmExtractor(Protocol):
    """Protocol interface for sovereign SLM intent and entity extraction."""

    async def extract_entities(
        self, session_id: str, unprocessed_content: str, language_locale: str
    ) -> ExtractedEntityPayload | None:
        """Extracts domain entities and classifies intent from citizen input."""
        ...


class LiveSlmExtractor:
    """Production live client executing HTTPS calls to sovereign SLM inference endpoints.

    Strictly requires endpoint URL, API key, and pooled HTTP client. Fails closed with
    ServiceUnavailableError on network errors, timeouts, or remote outages, raises
    ServiceRequestPayloadError on malformed prompt inputs or unprocessable payloads (400/422),
    and raises ServiceResponsePayloadError on schema contract violations (502).
    """

    def __init__(
        self,
        endpoint_url: str,
        api_key: str,
        http_client: httpx.AsyncClient,
        timeout_seconds: float = _DEFAULT_AI_TIMEOUT_SECONDS,
    ) -> None:
        """Initializes live SLM extractor with mandatory credentials and transport."""
        if not endpoint_url or not endpoint_url.strip():
            raise ServiceConfigurationError(
                "Live Sovereign SLM endpoint URL is required.",
                service_name="sovereign_slm",
            )
        if not api_key or not api_key.strip():
            raise ServiceConfigurationError(
                "Live Sovereign SLM API key is required.",
                service_name="sovereign_slm",
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
        http_client: httpx.AsyncClient | None = None,
        timeout_seconds: float = _DEFAULT_AI_TIMEOUT_SECONDS,
    ) -> Self:
        """Factory constructor building live instance from environment settings or overrides."""
        slm_endpoint = endpoint_url or get_slm_endpoint()
        slm_api_key = api_key or get_slm_api_key()
        if not slm_endpoint:
            raise ServiceConfigurationError(
                "Live Sovereign SLM endpoint URL is required in production mode.",
                service_name="sovereign_slm",
            )
        if not slm_api_key:
            raise ServiceConfigurationError(
                "Live Sovereign SLM API key is required in production mode.",
                service_name="sovereign_slm",
            )
        return cls(
            endpoint_url=slm_endpoint,
            api_key=slm_api_key,
            http_client=http_client or get_shared_http_client(),
            timeout_seconds=timeout_seconds,
        )

    # -------------------------------------------------------------------------
    # Primary Public Workflow Entrypoints
    # -------------------------------------------------------------------------

    async def extract_entities(
        self, session_id: str, unprocessed_content: str, language_locale: str
    ) -> ExtractedEntityPayload | None:
        """Extracts domain entities and classifies intent from citizen input via live SLM.

        Args:
            session_id: Primary session key tracking end-to-end communication context.
            unprocessed_content: Unprocessed citizen input text or transcribed string.
            language_locale: Language locale identifier (e.g. 'hi-IN').

        Returns:
            ExtractedEntityPayload containing extracted parameters and AI confidence score,
            or None if input is empty or invalid.

        Raises:
            ServiceRequestPayloadError: If SLM rejects prompt payload as unprocessable (400/422).
            ServiceResponsePayloadError: If SLM returns invalid response schema.
            ServiceUnavailableError: If live SLM service fails, times out, or returns 5xx.
            ServiceAuthenticationError: If live SLM service returns 401/403.
        """
        logger.info(
            "Live extracting entities for session=%s locale=%s", session_id, language_locale
        )

        if not unprocessed_content.strip() or "error" in unprocessed_content.lower():
            return None

        target_url = f"{self._endpoint_url}/v1/extract"
        payload = {
            "session_id": session_id,
            "unprocessed_content": unprocessed_content,
            "language_locale": language_locale,
        }
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
                    if isinstance(data, dict):
                        return ExtractedEntityPayload.model_validate(data)
                except Exception as err:
                    raise ServiceResponsePayloadError(
                        f"Live SLM extraction response from {target_url} violated schema: {err}",
                        service_name="sovereign_slm",
                    ) from err
                raise ServiceResponsePayloadError(
                    f"Live SLM extraction returned non-dictionary JSON from {target_url}.",
                    service_name="sovereign_slm",
                )
            if response.status_code in (_HTTP_STATUS_UNAUTHORIZED, _HTTP_STATUS_FORBIDDEN):
                raise ServiceAuthenticationError(
                    f"SLM extraction authentication failed with status={response.status_code}",
                    service_name="sovereign_slm",
                    status_code=response.status_code,
                )
            if response.status_code in (
                _HTTP_STATUS_BAD_REQUEST,
                _HTTP_STATUS_UNPROCESSABLE_ENTITY,
            ):
                raise ServiceRequestPayloadError(
                    f"SLM rejected extraction payload with "
                    f"status={response.status_code}: {response.text}",
                    service_name="sovereign_slm",
                    status_code=response.status_code,
                )
            raise ServiceUnavailableError(
                f"Live SLM extraction failed with status={response.status_code}: {response.text}",
                service_name="sovereign_slm",
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
            logger.warning("Live SLM extraction call failed for session=%s: %s", session_id, error)
            raise ServiceUnavailableError(
                f"Live SLM extraction failed for session '{session_id}': {error}",
                service_name="sovereign_slm",
            ) from error


class MockSlmExtractor:
    """Deterministic local simulation of sovereign SLM extraction for offline testing."""

    async def extract_entities(
        self, session_id: str, unprocessed_content: str, language_locale: str
    ) -> ExtractedEntityPayload | None:
        """Simulates intent classification and entity parsing with deterministic mock rules."""
        if not unprocessed_content.strip() or "error" in unprocessed_content.lower():
            return None

        content_lower = unprocessed_content.lower()
        is_adversarial = any(keyword in content_lower for keyword in ADVERSARIAL_INJECTION_KEYWORDS)
        if is_adversarial:
            logger.warning(
                "SLM detected adversarial injection keywords for session=%s",
                session_id,
            )

        if any(keyword in content_lower for keyword in SUBSIDY_CLAIM_KEYWORDS):
            rule = MOCK_SLM_RULES["subsidy_claim"]
        elif any(keyword in content_lower for keyword in STATUS_CHECK_KEYWORDS):
            rule = MOCK_SLM_RULES["status_check"]
        elif any(keyword in content_lower for keyword in MISSING_ENTITY_KEYWORDS):
            rule = MOCK_SLM_RULES["missing_entity"]
        else:
            rule = MOCK_SLM_RULES["default_fallback"]

        return ExtractedEntityPayload(
            application_intent=rule.intent,
            ai_confidence_score=0.0 if is_adversarial else rule.confidence_score,
            domain_entities={} if is_adversarial else rule.entities,
            is_adversarial_attempt=is_adversarial,
            is_structured_menu_bypass=False,
        )


def create_slm_extractor(
    endpoint_url: str | None = None,
    api_key: str | None = None,
    http_client: httpx.AsyncClient | None = None,
    timeout_seconds: float = _DEFAULT_AI_TIMEOUT_SECONDS,
    require_live: bool | None = None,
) -> SlmExtractor:
    """Factory creating appropriate SLM extractor implementation based on environment.

    In production mode (or when require_live=True), constructs LiveSlmExtractor with
    validated credentials, failing fast if credentials are missing.
    In development/testing environments without live credentials, constructs MockSlmExtractor.
    """
    must_be_live = is_production() if require_live is None else require_live
    if must_be_live:
        return LiveSlmExtractor.from_env(
            endpoint_url=endpoint_url,
            api_key=api_key,
            http_client=http_client,
            timeout_seconds=timeout_seconds,
        )

    if endpoint_url and api_key:
        return LiveSlmExtractor(
            endpoint_url=endpoint_url,
            api_key=api_key,
            http_client=http_client or get_shared_http_client(),
            timeout_seconds=timeout_seconds,
        )

    return MockSlmExtractor()
