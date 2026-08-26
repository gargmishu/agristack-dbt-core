"""Foundational AI Block: Small Language Model (SLM) Structured Entity Extractor.

Abstracts sovereign, in-memory structured entity extraction pipeline for Layer 3/4
processing.
Extracts domain parameters (district, taluka, village, crop_name, survey_number) and
computes
AI extraction confidence scores.

Why local sovereign SLM models?
Sovereign data governance requires processing citizen intent within local memory perimeters
without transmitting un-tokenized queries to remote third-party APIs.

See: decisions/step2.0_canonical_domain_schemas.md (Section 3.5)
See: roadmap.md (Phase 2 Step 2.2 Service Abstractions)
"""

import logging
from typing import Final

import httpx

from src.data_models.governance import ExtractedEntityPayload
from src.services.ai.ai_mock_fixtures import (
    ADVERSARIAL_INJECTION_KEYWORDS,
    MISSING_ENTITY_KEYWORDS,
    MOCK_SLM_RULES,
    STATUS_CHECK_KEYWORDS,
    SUBSIDY_CLAIM_KEYWORDS,
)

logger = logging.getLogger(__name__)

_DEFAULT_SLM_TIMEOUT_SECONDS: Final[float] = 2.0
_HTTP_STATUS_OK: Final[int] = 200


class SlmExtractor:
    """Service client for structured domain entity extraction from natural language text.

    Converts natural language input strings into typed domain parameter dictionaries keyed
    by `DomainEntityKey`.

    Capabilities:
    - Entity Extraction (`extract_entities`): Extracts parameters and computes confidence.
    - Adversarial Defense: Flags inputs with prompt injection patterns.

    Supports live REST endpoints with automatic, graceful fallback to deterministic local fixtures.

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
    ) -> None:
        """Initializes SLM extractor with optional live endpoint configuration.

        Args:
            endpoint_url: Optional base HTTP URL for live SLM extraction service.
            api_key: Optional authorization Bearer token or API key for live calls.
            http_client: Optional async HTTP client for connection pooling.
            timeout_seconds: Request timeout in seconds (default: 2.0s).
        """
        self._endpoint_url = endpoint_url.rstrip("/") if endpoint_url else None
        self._api_key = api_key
        self._http_client = http_client
        self._timeout_seconds = timeout_seconds

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

        return self._mock_extract_entities(session_id, unprocessed_content)

    # -------------------------------------------------------------------------
    # Private Helpers (Live HTTP & Local Mock Handlers)
    # -------------------------------------------------------------------------

    async def _call_live_extract(
        self, session_id: str, unprocessed_content: str, language_locale: str
    ) -> ExtractedEntityPayload | None:
        """Dispatches live SLM extraction HTTP request with graceful fallback."""
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
                if isinstance(data, dict):
                    return ExtractedEntityPayload.model_validate(data)
            logger.warning(
                "Live SLM extraction returned non-200 status=%d for session=%s",
                response.status_code,
                session_id,
            )
        except Exception as error:
            logger.warning(
                "Live SLM call failed for session=%s: %s; using mock fallback",
                session_id,
                error,
            )
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
