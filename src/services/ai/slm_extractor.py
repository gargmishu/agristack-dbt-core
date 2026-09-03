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

from httpx import AsyncClient

from src.config.service_settings import (
    get_slm_api_key,
    get_slm_endpoint,
    is_production,
)
from src.data_models.governance import ExtractedEntityPayload
from src.errors.service_errors import ServiceResponsePayloadError
from src.services.ai.ai_mock_fixtures import (
    ADVERSARIAL_INJECTION_KEYWORDS,
    MISSING_ENTITY_KEYWORDS,
    MOCK_SLM_RULES,
    STATUS_CHECK_KEYWORDS,
    SUBSIDY_CLAIM_KEYWORDS,
)
from src.services.http_transport import (
    ServiceHttpTransport,
    ServiceTransportConfig,
    get_shared_http_client,
)

logger = logging.getLogger(__name__)

__all__ = [
    "LiveSlmExtractor",
    "MockSlmExtractor",
    "SlmExtractor",
    "create_slm_extractor",
]

_DEFAULT_AI_TIMEOUT_SECONDS: Final[float] = 2.0
_ENTITY_EXTRACT_PATH: Final[str] = "/v1/extract"


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
        http_client: AsyncClient,
        timeout_seconds: float = _DEFAULT_AI_TIMEOUT_SECONDS,
    ) -> None:
        """Initializes live SLM extractor with mandatory credentials and transport."""
        self._transport = ServiceHttpTransport(
            http_client=http_client,
            api_key=api_key,
            config=ServiceTransportConfig(
                service_name="sovereign_slm",
                service_title="SLM extraction",
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
        timeout_seconds: float = _DEFAULT_AI_TIMEOUT_SECONDS,
    ) -> Self:
        """Factory constructor building live instance from environment settings or overrides."""
        return cls(
            endpoint_url=endpoint_url or get_slm_endpoint() or "",
            api_key=api_key or get_slm_api_key() or "",
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

        if not unprocessed_content.strip():
            return None

        payload = {
            "session_id": session_id,
            "unprocessed_content": unprocessed_content,
            "language_locale": language_locale,
        }

        response_data = await self._transport.post_json(
            _ENTITY_EXTRACT_PATH,
            payload=payload,
            context_label=f"session_id={session_id}",
        )
        try:
            return ExtractedEntityPayload.model_validate(response_data)
        except Exception as error:
            target_url = self._transport.resolve_url(_ENTITY_EXTRACT_PATH)
            raise ServiceResponsePayloadError(
                f"Live SLM extraction response from {target_url} violated schema: {error}",
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
    http_client: AsyncClient | None = None,
    timeout_seconds: float = _DEFAULT_AI_TIMEOUT_SECONDS,
    require_live: bool | None = None,
) -> SlmExtractor:
    """Factory creating appropriate SLM extractor implementation based on environment.

    Resolution follows a 3-tier precedence model:
    1.  Mandatory Production: If require_live=True (or ENVIRONMENT='production' is set),
       constructs LiveSlmExtractor via environment settings, failing fast if credentials
       are missing.
    2. Explicit Parameters: If endpoint_url and api_key are provided directly as arguments,
       constructs LiveSlmExtractor targeting those coordinates (useful for local WireMock,
       stub proxies, or partial sandbox integration without enforcing production invariants).
    3. Offline Simulation: If require_live is False and explicit credentials are not passed
       (even if present in environment variables), returns MockSlmExtractor to guarantee
       offline test isolation for local development and CI pipelines.
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
