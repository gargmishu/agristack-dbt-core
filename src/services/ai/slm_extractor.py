"""Foundational AI Block: Small Language Model (SLM) Structured Entity Extractor.

Abstracts sovereign, in-memory structured entity extraction pipeline for Layer 3/4
processing. Extracts domain parameters (district, taluka, village, crop_name, survey_number)
and computes AI extraction confidence scores.

Why local sovereign SLM models?
Sovereign data governance requires processing citizen intent within local memory perimeters
without transmitting un-tokenized queries to remote third-party APIs.

In production environments, enforces live HTTPS communication via LiveSlmExtractor with strict
fail-fast configuration and fail-closed error handling (no mock fallback). In non-production,
MockSlmExtractor provides deterministic mock simulation for offline testing.

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

_DEFAULT_SLM_TIMEOUT_SECONDS: Final[float] = 2.0
_HTTP_STATUS_OK: Final[int] = 200
_HTTP_STATUS_UNAUTHORIZED: Final[int] = 401
_HTTP_STATUS_FORBIDDEN: Final[int] = 403


class SlmExtractor(Protocol):
    """Protocol contract for structured domain entity extraction from natural language text.

    Converts natural language input strings into typed domain parameter dictionaries.
    """

    async def extract_entities(
        self, session_id: str, unprocessed_content: str, language_locale: str
    ) -> ExtractedEntityPayload | None:
        """Extracts domain entities and classifies intent from citizen input."""
        ...


class LiveSlmExtractor:
    """Production live client executing HTTPS calls to sovereign SLM extraction endpoints.

    Strictly requires endpoint URL, API key, and pooled HTTP client. Fails closed with
    ServiceUnavailableError on network errors, timeouts, or remote model outages.
    """

    def __init__(
        self,
        endpoint_url: str,
        api_key: str,
        http_client: httpx.AsyncClient,
        timeout_seconds: float = _DEFAULT_SLM_TIMEOUT_SECONDS,
    ) -> None:
        """Initializes live SLM extractor with mandatory credentials and transport."""
        if not endpoint_url or not endpoint_url.strip():
            raise ServiceConfigurationError(
                "Live Sovereign SLM endpoint URL is required.",
                service_name="slm",
            )
        if not api_key or not api_key.strip():
            raise ServiceConfigurationError(
                "Live Sovereign SLM API key is required.",
                service_name="slm",
            )
        self._endpoint_url = endpoint_url.rstrip("/")
        self._api_key = api_key.strip()
        self._http_client = http_client
        self._timeout_seconds = timeout_seconds

    @classmethod
    def from_env(
        cls,
        http_client: httpx.AsyncClient | None = None,
    ) -> Self:
        """Factory constructor building live instance from validated environment settings."""
        endpoint = get_slm_endpoint()
        api_key = get_slm_api_key()
        if not endpoint:
            raise ServiceConfigurationError(
                "Live Sovereign SLM endpoint URL is required in production mode.",
                service_name="slm",
            )
        if not api_key:
            raise ServiceConfigurationError(
                "Live Sovereign SLM API key is required in production mode.",
                service_name="slm",
            )
        return cls(
            endpoint_url=endpoint,
            api_key=api_key,
            http_client=http_client or get_shared_http_client(),
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
            ServiceUnavailableError: If live SLM service fails, times out, or returns 5xx.
            ServiceAuthenticationError: If live SLM service returns 401/403.
        """
        logger.info(
            "Live extracting entities for session=%s locale=%s", session_id, language_locale
        )

        if not unprocessed_content.strip() or "error" in unprocessed_content.lower():
            return None

        live_result = await self._call_live_extract(
            session_id, unprocessed_content, language_locale
        )
        if live_result is not None:
            return live_result

        raise ServiceUnavailableError(
            f"Live Sovereign SLM extraction failed for session '{session_id}'.",
            service_name="slm",
        )

    # -------------------------------------------------------------------------
    # Private Helpers (Live HTTP Handlers)
    # -------------------------------------------------------------------------

    async def _call_live_extract(
        self, session_id: str, unprocessed_content: str, language_locale: str
    ) -> ExtractedEntityPayload | None:
        """Dispatches live SLM extraction HTTP request."""
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
                data = response.json()
                if isinstance(data, dict):
                    return ExtractedEntityPayload.model_validate(data)
            elif response.status_code in (_HTTP_STATUS_UNAUTHORIZED, _HTTP_STATUS_FORBIDDEN):
                raise ServiceAuthenticationError(
                    f"SLM extraction authentication failed with status={response.status_code}",
                    service_name="slm",
                    status_code=response.status_code,
                )
            logger.warning(
                "Live SLM extraction returned status=%d for session=%s",
                response.status_code,
                session_id,
            )
        except (ServiceAuthenticationError, ServiceUnavailableError):
            raise
        except Exception as error:
            logger.warning("Live SLM extraction call failed for session=%s: %s", session_id, error)
            raise ServiceUnavailableError(
                f"Live SLM extraction failed for session '{session_id}': {error}",
                service_name="slm",
            ) from error
        return None


class MockSlmExtractor:
    """Deterministic local simulation of SLM entity extraction for offline testing."""

    async def extract_entities(
        self, session_id: str, unprocessed_content: str, language_locale: str
    ) -> ExtractedEntityPayload | None:
        """Extracts domain entities using deterministic local heuristic rules."""
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
            ai_confidence_score=rule.confidence_score,
            domain_entities=rule.entities,
            is_adversarial_attempt=is_adversarial,
            is_structured_menu_bypass=False,
        )


def create_slm_extractor(
    endpoint_url: str | None = None,
    api_key: str | None = None,
    http_client: httpx.AsyncClient | None = None,
    timeout_seconds: float = _DEFAULT_SLM_TIMEOUT_SECONDS,
    require_live: bool | None = None,
) -> SlmExtractor:
    """Factory creating appropriate SLM extractor implementation based on environment.

    In production mode (or when require_live=True), constructs LiveSlmExtractor with
    validated credentials, failing fast if credentials are missing.
    In development/testing environments without live credentials, constructs MockSlmExtractor.
    """
    must_be_live = is_production() if require_live is None else require_live
    if must_be_live:
        resolved_endpoint = endpoint_url or get_slm_endpoint()
        resolved_key = api_key or get_slm_api_key()
        if not resolved_endpoint:
            raise ServiceConfigurationError(
                "Live Sovereign SLM endpoint URL is required in production mode.",
                service_name="slm",
            )
        if not resolved_key:
            raise ServiceConfigurationError(
                "Live Sovereign SLM API key is required in production mode.",
                service_name="slm",
            )
        return LiveSlmExtractor(
            endpoint_url=resolved_endpoint,
            api_key=resolved_key,
            http_client=http_client or get_shared_http_client(),
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
