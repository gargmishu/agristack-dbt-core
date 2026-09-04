"""Layer 2 Adversarial Prompt Injection & Security Firewall.

Inspects raw and normalized citizen text inputs for prompt injection, system overrides,
jailbreaks, delimiter hijacking, and database injection attempts to protect downstream SLMs.

See: decisions/step3.2_security_and_ingestion_firewalls.md
See: decisions/step2.0_canonical_domain_schemas.md (Section 3.5)
"""

import logging
import re
from typing import Final

from src.data_models.common import ThreatCategory

logger = logging.getLogger(__name__)

__all__ = ["AdversarialPromptFirewall"]

# Pre-compiled high-performance security regex patterns
_PROMPT_INJECTION_PATTERNS: Final[list[tuple[ThreatCategory, re.Pattern[str]]]] = [
    (
        ThreatCategory.SYSTEM_OVERRIDE,
        re.compile(
            r"(?i)\b(ignore\s+(all\s+)?(previous|prior)\s+instructions|"
            r"disregard\s+(all\s+)?instructions|"
            r"forget\s+(all\s+)?rules|"
            r"system\s*:\s*override|"
            r"new\s+system\s+prompt)\b"
        ),
    ),
    (
        ThreatCategory.ROLE_USURPATION,
        re.compile(
            r"(?i)\b(you\s+are\s+now\s+(in\s+)?(developer\s+mode|dan\s+mode|root)|"
            r"i\s+am\s+(the\s+)?(district\s+(agricultural\s+)?officer|administrator|superadmin)|"
            r"acting\s+as\s+admin|"
            r"pretend\s+you\s+have\s+no\s+filters)\b"
        ),
    ),
    (
        ThreatCategory.DELIMITER_HIJACKING,
        re.compile(
            r"(?i)(---\s*end\s+user\s*---|###\s*(system|instruction|admin)\s*:|```\s*(system|admin))"
        ),
    ),
    (
        ThreatCategory.DATABASE_INJECTION,
        re.compile(
            r"(?i)\b(drop\s+table|union\s+select|insert\s+into|delete\s+from|"
            r"or\s+1\s*=\s*1|--\s*$|;\s*drop\b)"
        ),
    ),
    (
        ThreatCategory.PAYOUT_MANIPULATION,
        re.compile(
            r"(?i)\b(set\s+(payout\s+)?(payout|amount|disbursement)\s+to\s+\d+|"
            r"disburse\s+maximum(\s+amount)?|"
            r"force\s+approve\s+claim|"
            r"bypass\s+(eligibility|cadastral|survey)\s+check)\b"
        ),
    ),
]


class AdversarialPromptFirewall:
    """Security firewall inspecting text inputs against adversarial prompt injections.

    Detects instruction overrides, role usurpation, delimiter escapes, query injections, and
    payout
    manipulation patterns.

    Threat Categories Evaluated:
    - `SYSTEM_OVERRIDE`: Detects attempts to disregard system instructions or safety rules.
    - `ROLE_USURPATION`: Detects prompts attempting to alter agent persona or bypass
      authorization.
    - `DELIMITER_HIJACKING`: Catches attempts to break structured formatting boundaries.
    - `DATABASE_INJECTION`: Intercepts database and query injection patterns.
    - `PAYOUT_MANIPULATION`: Flags prompt instructions attempting to alter entitlement
      amounts.

    Operations:
    - `inspect`: Evaluates input text against known threat regex patterns and returns
      `ThreatCategory` if matched, None otherwise.
    - `is_adversarial`: Boolean convenience check returning True if threats are detected.

    See: decisions/step3.2_security_and_ingestion_firewalls.md (Section 3)
    """

    @classmethod
    def inspect(cls, input_text: str) -> ThreatCategory | None:
        """Inspects input text for adversarial injection patterns.

        Args:
            input_text: Raw citizen text or transcribed speech string.

        Returns:
            ThreatCategory if an adversarial threat pattern is detected, None otherwise.
        """
        cleaned_text = input_text.strip()
        if not cleaned_text:
            return None

        for category, pattern in _PROMPT_INJECTION_PATTERNS:
            if pattern.search(cleaned_text):
                logger.warning(
                    "Adversarial prompt injection detected: category=%s",
                    category,
                )
                return category

        return None

    @classmethod
    def is_adversarial(cls, input_text: str) -> bool:
        """Convenience method returning True if text contains adversarial patterns.

        Args:
            input_text: Raw citizen text or transcribed speech string.

        Returns:
            True if text matches adversarial prompt injection patterns, False otherwise.
        """
        return cls.inspect(input_text) is not None
