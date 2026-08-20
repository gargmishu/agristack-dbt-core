"""Layer 2 Ingestion Perimeter Firewall.

Unified security facade combining webhook authentication, token-bucket rate limiting,
volatile RAM Zero-Trust PII tokenization, PII purge assertions, adversarial prompt
injection scanning, and payload canonicalization for Layer 3 intake.

See: decisions/step3.2_security_and_ingestion_firewalls.md
See: decisions/step0.3_zero_trust_tokenization.md
"""

import logging

from src.data_models.common import LanguageLocale
from src.data_models.public_agent import PublicAgentStandardizedIntakePayload
from src.data_models.raw_ingress import (
    SmsIngressPayload,
    UssdIngressPayload,
    WhatsAppIngressPayload,
)
from src.gateway.adversarial_prompt_firewall import AdversarialPromptFirewall
from src.gateway.carrier_auth_validator import CarrierAuthValidator
from src.gateway.payload_canonicalizer import IngressPayloadUnion, PayloadCanonicalizer
from src.gateway.pii_purge_guard import PiiPurgeGuard
from src.gateway.rate_limiter import RateLimiter
from src.gateway.zero_trust_identity_tokenizer import ZeroTrustIdentityTokenizer

logger = logging.getLogger(__name__)


class IngestionFirewall:
    """Perimeter security facade coordinating rate limiting, tokenization, and canonicalization.

    Combines rate limiting, identity tokenization, PII redaction, prompt injection
    inspection,
    and payload normalization into a single ingress validation pipeline.

    Pipeline Operations:
    1. Rate Limiting (`RateLimiter`): Enforces request quota per caller identity.
    2. Canonicalization & Tokenization (`PayloadCanonicalizer`): Converts raw ingress
       payloads into
       `PublicAgentStandardizedIntakePayload` with pseudonymous 64-char HMAC citizen tokens.
    3. PII Purge Sentinel (`PiiPurgeGuard.assert_zero_pii`): Verifies that cleartext
       identifiers do not exist.
    4. Adversarial Prompt Scanning (`AdversarialPromptFirewall`): Checks content for
       injection patterns.

    See: decisions/step3.2_security_and_ingestion_firewalls.md
    See: decisions/step0.3_zero_trust_tokenization.md
    """

    def __init__(
        self,
        tokenizer: ZeroTrustIdentityTokenizer,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        """Initializes IngestionFirewall with required security components.

        Args:
            tokenizer: Non-nullable ZeroTrustIdentityTokenizer instance.
            rate_limiter: Optional RateLimiter instance (defaults to standard quota).
        """
        self._tokenizer = tokenizer
        self._rate_limiter = rate_limiter or RateLimiter(rate_per_minute=60, capacity=10)
        self._canonicalizer = PayloadCanonicalizer(tokenizer=tokenizer)

    @classmethod
    def from_env(cls) -> "IngestionFirewall":
        """Factory method to construct firewall with environment-injected secrets."""
        return cls(tokenizer=ZeroTrustIdentityTokenizer.from_env())

    def validate_and_canonicalize(
        self,
        payload: IngressPayloadUnion,
        language_locale: LanguageLocale = LanguageLocale.HINDI,
    ) -> tuple[PublicAgentStandardizedIntakePayload, bool]:
        """Ingests, rate-limits, tokenizes PII in RAM, and scans for adversarial patterns.

        Args:
            payload: WhatsAppIngressPayload, IvrIngressPayload, or UssdIngressPayload.
            language_locale: Target BCP-47 language locale (default: 'hi-IN').

        Returns:
            Tuple of (standardized_payload, is_adversarial_detected).

        Raises:
            PermissionError: If rate limit is exceeded.
            ValueError: If payload fails PII purge assertion.
        """
        # 1. Rate Limit Enforcement
        rate_key = payload.originating_phone_number
        if not self._rate_limiter.is_allowed(rate_key):
            logger.warning("Rate limit exceeded for ingress session=%s", payload.session_id)
            raise PermissionError(f"Rate limit exceeded for session {payload.session_id}")

        # 2. Canonicalization with RAM-only PII tokenization
        standardized_payload = self._canonicalizer.canonicalize(
            payload=payload, language_locale=language_locale
        )

        # 3. PII Purge Sentinel Assertion
        PiiPurgeGuard.assert_zero_pii(standardized_payload)

        # 4. Adversarial Prompt Injection Pre-Inspection
        # Note: Pre-inspects text bodies and USSD selections at the ingress boundary.
        # Audio recordings (IVR/WhatsApp audio) are inspected downstream post-ASR transcription.
        is_adversarial = False
        raw_text = None
        if isinstance(payload, WhatsAppIngressPayload | SmsIngressPayload) and payload.text_body:
            raw_text = payload.text_body
        elif isinstance(payload, UssdIngressPayload) and payload.ussd_user_digit_selection:
            raw_text = payload.ussd_user_digit_selection

        if raw_text is not None:
            is_adversarial, threat_category = AdversarialPromptFirewall.inspect(raw_text)
            if is_adversarial:
                logger.warning(
                    "Adversarial pattern detected during ingress session=%s category=%s",
                    payload.session_id,
                    threat_category,
                )

        return standardized_payload, is_adversarial

    @staticmethod
    def verify_carrier_webhook(
        payload_bytes: bytes,
        signature_header: str | None,
        app_secret: str,
    ) -> bool:
        """Verifies Meta WhatsApp X-Hub-Signature-256 header."""
        return CarrierAuthValidator.validate_whatsapp_signature(
            payload_bytes=payload_bytes,
            signature_header=signature_header,
            app_secret=app_secret,
        )

    @staticmethod
    def verify_carrier_bearer(
        auth_header: str | None,
        expected_token: str,
    ) -> bool:
        """Verifies carrier bearer token for IVR/USSD gateway requests."""
        return CarrierAuthValidator.validate_carrier_bearer_token(
            auth_header=auth_header,
            expected_token=expected_token,
        )
