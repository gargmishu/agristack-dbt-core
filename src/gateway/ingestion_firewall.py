"""Layer 2 Ingestion Perimeter Firewall.

Unified security facade combining webhook authentication, token-bucket rate limiting,
volatile RAM Zero-Trust PII tokenization, PII purge assertions, adversarial prompt
injection scanning, and payload canonicalization for Layer 3 intake.

See: decisions/step3.2_security_and_ingestion_firewalls.md
See: decisions/step0.3_zero_trust_tokenization.md
"""

import logging
from typing import Self

from src.config import get_rate_limit_capacity, get_rate_per_minute
from src.data_models.common import LanguageLocale
from src.data_models.public_agent import PublicAgentStandardizedIntakePayload
from src.data_models.raw_ingress import (
    IvrIngressPayload,
    SmsIngressPayload,
    UssdIngressPayload,
    WhatsAppIngressPayload,
)
from src.gateway.adversarial_prompt_firewall import AdversarialPromptFirewall
from src.gateway.carrier_auth_validator import CarrierAuthValidator
from src.gateway.payload_canonicalizer import PayloadCanonicalizer
from src.gateway.pii_purge_guard import PiiPurgeGuard
from src.gateway.rate_limiter import RateLimiter
from src.gateway.zero_trust_identity_tokenizer import ZeroTrustIdentityTokenizer

logger = logging.getLogger(__name__)

__all__ = ["IngestionFirewall"]


class IngestionFirewall:
    """Perimeter security facade coordinating rate limiting, tokenization, and canonicalization.

    Combines rate limiting, identity tokenization, PII redaction, prompt injection
    inspection, and payload normalization into a single ingress validation pipeline.

    Pipeline Operations:
    1. Rate Limiting: Enforces request quotas per caller identity.
    2. Canonicalization & Tokenization: Converts raw ingress payloads into standardized
       intake contracts with pseudonymous 64-char HMAC citizen tokens.
    3. Zero-PII Sentinel: Verifies that no cleartext identifiers leak into downstream fields.
    4. Adversarial Prompt Scanning: Checks content for prompt injection and override patterns.

    See: decisions/step3.2_security_and_ingestion_firewalls.md
    See: decisions/step0.3_zero_trust_tokenization.md
    """

    def __init__(
        self,
        tokenizer: ZeroTrustIdentityTokenizer,
        rate_limiter: RateLimiter,
    ) -> None:
        """Initializes all firewall members from injected security components.

        Args:
            tokenizer: Identity tokenizer component.
            rate_limiter: Rate limiter component controlling ingress request quotas.
        """
        self._tokenizer = tokenizer
        self._rate_limiter = rate_limiter
        self._canonicalizer = PayloadCanonicalizer(tokenizer=tokenizer)

    @classmethod
    def from_env(cls) -> Self:
        """Builds a firewall with an environment-configured tokenizer.

        Environment resolution happens here; all instance members are initialized by
        ``__init__`` using the same dependency-injection path as direct construction.
        """
        return cls(
            tokenizer=ZeroTrustIdentityTokenizer.from_env(),
            rate_limiter=RateLimiter(
                rate_per_minute=get_rate_per_minute(),
                capacity=get_rate_limit_capacity(),
            ),
        )

    def process_ingress(
        self,
        payload: WhatsAppIngressPayload
        | IvrIngressPayload
        | UssdIngressPayload
        | SmsIngressPayload,
        language_locale: LanguageLocale = LanguageLocale.HINDI,
    ) -> PublicAgentStandardizedIntakePayload:
        """Unified ingress pipeline orchestrator: validates security, tokenizes, and canonicalizes.

        Args:
            payload: Raw carrier ingress payload (WhatsApp, IVR, USSD, or SMS).
            language_locale: Target BCP-47 language locale (default: 'hi-IN').

        Returns:
            PublicAgentStandardizedIntakePayload normalized for Layer 3 intake.

        Raises:
            PermissionError: If rate limit is exceeded.
            ValueError: If payload fails PII purge assertion.
        """
        self._inspect_security(payload)
        return self._canonicalize(payload, language_locale=language_locale)

    @staticmethod
    def verify_carrier_webhook(
        payload_bytes: bytes,
        signature_header: str | None,
        app_secret: str,
    ) -> bool:
        """Verifies carrier SHA-256 HMAC payload signatures (e.g. Meta WhatsApp, BSPs).

        Args:
            payload_bytes: Raw request body bytes.
            signature_header: The value of the signature header (e.g., X-Hub-Signature-256).
            app_secret: Shared HMAC secret key.

        Returns:
            True if signature is valid and authentic, False otherwise.
        """
        return CarrierAuthValidator.validate_hmac_signature(
            payload_bytes=payload_bytes,
            signature_header=signature_header,
            app_secret=app_secret,
        )

    @staticmethod
    def verify_carrier_bearer(
        auth_header: str | None,
        expected_token: str,
    ) -> bool:
        """Verifies carrier bearer token for IVR (SIP), USSD (SS7), and SMS gateway requests.

        Args:
            auth_header: Authorization header string (e.g. 'Bearer <token>').
            expected_token: Shared carrier bearer token secret.

        Returns:
            True if bearer token matches, False otherwise.
        """
        return CarrierAuthValidator.validate_carrier_bearer_token(
            auth_header=auth_header,
            expected_token=expected_token,
        )

    # -------------------------------------------------------------------------
    # Private Security & Canonicalization Helpers
    # -------------------------------------------------------------------------

    def _inspect_security(
        self,
        payload: WhatsAppIngressPayload
        | IvrIngressPayload
        | UssdIngressPayload
        | SmsIngressPayload,
    ) -> bool:
        """Enforces caller rate limits and scans for adversarial prompt injections.

        Args:
            payload: Ingress carrier payload.

        Returns:
            bool: True if an adversarial threat/prompt injection is detected, False otherwise.

        Raises:
            PermissionError: If rate limit is exceeded for the originating phone number.
        """
        # 1. Rate Limit Enforcement
        # Note: Rate limits are tracked in-memory by originating_phone_number to throttle
        # callers across multiple sessions. The session_id is logged instead of the cleartext
        # phone number to adhere strictly to the Zero-PII logging invariant.
        if not self._rate_limiter.is_allowed(payload.originating_phone_number):
            logger.warning("Rate limit exceeded for ingress session=%s", payload.session_id)
            raise PermissionError(f"Rate limit exceeded for session {payload.session_id}")

        # 2. Adversarial Prompt Injection Pre-Inspection
        # Note: Pre-inspects free-text message bodies (WhatsApp text, SMS) at the ingress boundary.
        # Audio recordings (IVR/WhatsApp audio) are inspected downstream post-ASR transcription.
        raw_text = self._extract_inspectable_text(payload)
        if raw_text is not None:
            threat_category = AdversarialPromptFirewall.inspect(raw_text)
            if threat_category is not None:
                logger.warning(
                    "Adversarial pattern detected during ingress session=%s category=%s",
                    payload.session_id,
                    threat_category,
                )
                return True

        return False

    def _canonicalize(
        self,
        payload: WhatsAppIngressPayload
        | IvrIngressPayload
        | UssdIngressPayload
        | SmsIngressPayload,
        language_locale: LanguageLocale = LanguageLocale.HINDI,
    ) -> PublicAgentStandardizedIntakePayload:
        """Transforms a raw carrier ingress payload into a zero-PII standardized contract.

        Args:
            payload: Raw carrier ingress payload with phone number.
            language_locale: Target BCP-47 language locale (default: 'hi-IN').

        Returns:
            PublicAgentStandardizedIntakePayload with RAM-tokenized citizen identifier.

        Raises:
            ValueError: If the normalized payload fails the PII purge assertion.
        """
        standardized_payload = self._canonicalizer.canonicalize(
            payload=payload, language_locale=language_locale
        )
        PiiPurgeGuard.assert_zero_pii(standardized_payload)
        return standardized_payload

    def _extract_inspectable_text(
        self,
        payload: WhatsAppIngressPayload
        | IvrIngressPayload
        | UssdIngressPayload
        | SmsIngressPayload,
    ) -> str | None:
        """Extracts free-form text content for ingress prompt injection screening.

        Args:
            payload: Raw carrier ingress payload across supported channels.

        Returns:
            Extractable text string if payload contains text, or None if audio/digit menu.
        """
        if isinstance(payload, WhatsAppIngressPayload | SmsIngressPayload) and payload.text_body:
            return payload.text_body
        return None
