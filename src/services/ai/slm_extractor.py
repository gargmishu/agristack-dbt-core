"""Foundational AI Block: Small Language Model (SLM) Structured Entity Extractor.

Abstracts sovereign, in-memory structured entity extraction pipeline for Layer 3/4
processing.
Extracts domain parameters (district, taluka, village, crop_name, survey_number) and
computes
AI extraction confidence scores.

Why local sovereign SLM models?
Sovereign data governance requires processing citizen intent within local memory perimeters
without transmitting un-tokenized queries to remote third-party APIs.

In production environments, enforces live HTTPS communication with strict fail-fast configuration
and fail-closed error handling (no mock fallback). In non-production, supports deterministic
mock simulation for offline testing.

See: decisions/step2.0_canonical_domain_schemas.md (Section 3.5)
See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.1)
See: decisions/step3.6_live_service_integration.md
See: roadmap.md (Phase 2 Step 2.2 Service Abstractions)
"""

import logging
from typing import Final

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


class SlmExtractor:
    """Service client for structured domain entity extraction from natural language text.

    Converts natural language input strings into typed domain parameter dictionaries keyed
    by `DomainEntityKey`.

    Capabilities:
    - Entity Extraction (`extract_entities`): Extracts parameters and computes confidence.
    - Adversarial Defense: Flags inputs with prompt injection patterns.

    In production, mandates live endpoint configuration and pooled persistent HTTP transport.
    In development/testing, supports offline mock simulations.

    See: decisions/step2.0_canonical_domain_schemas.md#slm-extracted-entity-payload
    See: decisions/step3.1_foundational_mock_boundaries.md (Section 3.1)
    See: decisions/step3.6_live_service_integration.md
    """

    def __init__(
        self,
        endpoint_url: str | None = None,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        timeout_seconds: float = _DEFAULT_SLM_TIMEOUT_SECONDS,
        require_live: bool | None = None,
    ) -> None:
        """Initializes SLM extractor.

        Args:
            endpoint_url: Base HTTP URL for live SLM extraction service.
            api_key: Authorization Bearer token or API key for live calls.
            http_client: Async HTTP client for connection pooling.
            timeout_seconds: Request timeout in seconds (default: 2.0s).
            require_live: Whether live endpoints are required (defaults to is_production()).

        Raises:
            ServiceConfigurationError: In production mode if endpoint_url or api_key is missing.
        """
        self._require_live = is_production() if require_live is None else require_live
        self._http_client: httpx.AsyncClient | None

        if self._require_live:
            if not endpoint_url or not endpoint_url.strip():
                raise ServiceConfigurationError(
                    "Live Sovereign SLM endpoint URL is required in production mode."
                )
            if not api_key or not api_key.strip():
                raise ServiceConfigurationError(
                    "Live Sovereign SLM API key is required in production mode."
                )
            self._http_client = http_client or get_shared_http_client()
        else:
            self._http_client = http_client

        self._endpoint_url = (
            endpoint_url.rstrip("/") if endpoint_url and endpoint_url.strip() else None
        )
        self._api_key = api_key.strip() if api_key and api_key.strip() else None
        self._timeout_seconds = timeout_seconds

    @classmethod
    def from_env(
        cls,
        http_client: httpx.AsyncClient | None = None,
        require_live: bool | None = None,
    ) -> "SlmExtractor":
        """Factory constructor building instance from validated environment settings."""
        return cls(
            endpoint_url=get_slm_endpoint(),
            api_key=get_slm_api_key(),
            http_client=http_client,
            require_live=require_live,
        )

    # -------------------------------------------------------------------------
    # Primary Public Workflow Entrypoints
    # -------------------------------------------------------------------------

    async def extract_entities(
        self, session_id: str, unprocessed_content: str, language_locale: str
    ) -> ExtractedEntityPayload | None:
        """Extracts domain entities and classifies intent from citizen input.

        Args:
            session_id: Primary session key tracking end-to-end communication context.
            unprocessed_content: Unprocessed citizen input text or transcribed string.
            language_locale: Language locale identifier (e.g. 'hi-IN').

        Returns:
            ExtractedEntityPayload containing extracted parameters and AI confidence score,
            or None if extraction could not be completed.

        Raises:
            ServiceUnavailableError: In live mode if external SLM service fails or times out.
            ServiceAuthenticationError: In live mode if external SLM service returns 401/403.
            ServiceConfigurationError: In live mode if live endpoint is not configured.
        """
        logger.info("Extracting entities for session=%s locale=%s", session_id, language_locale)

        if not unprocessed_content.strip() or "error" in unprocessed_content.lower():
            return None

        if self._endpoint_url:
            live_result = await self._call_live_extract(
                session_id, unprocessed_content, language_locale
            )
            if live_result is not None:
                return live_result
            if self._require_live:
                raise ServiceUnavailableError(
                    f"Live Sovereign SLM extraction failed for session '{session_id}'."
                )

        if self._require_live:
            raise ServiceConfigurationError(
                "Sovereign SLM cannot execute: live endpoint is required in production."
            )

        return self._mock_extract_entities(session_id, unprocessed_content)

    # -------------------------------------------------------------------------
    # Private Helpers (Live HTTP & Local Mock Handlers)
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
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            client = self._http_client or get_shared_http_client()
            response = await client.post(
                target_url, json=payload, headers=headers, timeout=self._timeout_seconds
            )
            if response.status_code == _HTTP_STATUS_OK:
                data = response.json()
                if isinstance(data, dict):
                    return ExtractedEntityPayload.model_validate(data)
            elif response.status_code in (_HTTP_STATUS_UNAUTHORIZED, _HTTP_STATUS_FORBIDDEN):
                if self._require_live:
                    raise ServiceAuthenticationError(
                        f"SLM extraction authentication failed with status={response.status_code}"
                    )
            logger.warning(
                "Live SLM extraction returned status=%d for session=%s",
                response.status_code,
                session_id,
            )
        except (ServiceAuthenticationError, ServiceUnavailableError):
            raise
        except Exception as error:
            logger.warning(
                "Live SLM extraction call failed for session=%s: %s; fallback_allowed=%s",
                session_id,
                error,
                not self._require_live,
            )
            if self._require_live:
                raise ServiceUnavailableError(
                    f"Live SLM extraction failed for session '{session_id}': {error}"
                ) from error
        return None

    @staticmethod
    def _mock_extract_entities(session_id: str, unprocessed_content: str) -> ExtractedEntityPayload:
        """Deterministic local SLM rule simulation."""
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
