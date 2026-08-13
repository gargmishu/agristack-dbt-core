"""Shared constrained field type annotations across domain payloads.

See: decisions/step2.0_canonical_domain_schemas.md#40-shared--reusable-validation-rules
See: decisions/step0.3_zero_trust_tokenization.md
"""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, Field

# Allow 5 seconds of clock skew between edge connectors and core services to handle
# minor network latency and NTP drift while preventing replay attacks and future-dated payloads.
MAX_CLOCK_SKEW_SECONDS = 5.0

# Session ID entropy bounds (8 to 128 chars):
# - min=8: Entropy floor (8 alphanumeric chars ≈ 48 bits) preventing brute-force guessing.
# - max=128: Hard ceiling covering long carrier UUIDs (e.g. Meta wamid, SIP Call-ID) while
#   rejecting oversized injections.
SessionId = Annotated[
    str,
    Field(
        min_length=8,
        max_length=128,
        description="Unified session ID (entropy floor >=8, ceiling <=128)",
    ),
]

PhoneNumberE164 = Annotated[
    str,
    Field(
        min_length=2,
        max_length=16,
        pattern=r"^\+[1-9]\d{1,14}$",
        description="Originating E.164 international phone number format (+919876543210)",
    ),
]

# Zero-PII SHA-256 HMAC digest (64 hex characters):
# Encrypts sensitive citizen identity (MSISDN or UIDAI Token UID under Aadhaar Act §29)
# to guarantee Zero-Trust anonymity across downstream processing layers.
HmacCitizenToken = Annotated[
    str,
    Field(
        min_length=64,
        max_length=64,
        pattern=r"^[a-fA-F0-9]{64}$",
        description="Zero-PII SHA-256 HMAC citizen identity token (exact 64-char hex string)",
    ),
]

EscalationCaseId = Annotated[
    str,
    Field(
        min_length=16,
        max_length=64,
        pattern=r"^\w+-CASE-\d{4}-\d{6,}$",
        description="Incident ticket ID pattern (e.g. SPP-CASE-2026-981245)",
    ),
]

DisbursementTxnId = Annotated[
    str,
    Field(
        min_length=8,
        max_length=128,
        description="Unique payment clearing transaction ID (entropy floor >=8, ceiling <=128)",
    ),
]

ExtractionPayloadId = Annotated[
    str,
    Field(
        min_length=8,
        max_length=128,
        description="Foreign key referencing original extraction payload_id",
    ),
]

# Fail-fast audio duration gatekeeper (1s to 600s / 10 min):
# - min=1: Rejects dropped calls with duration=0 before allocating ASR resources.
# - max=600: Prevents Out-Of-Memory (OOM) GPU crashes and context truncation hallucinations
#   on SLM workers.
AudioDurationSeconds = Annotated[
    int,
    Field(
        ge=1,
        le=600,
        description="Voice audio recording duration in seconds (1 to 600s ceiling)",
    ),
]

AiConfidenceScore = Annotated[
    float,
    Field(
        ge=0.0,
        le=1.0,
        description="SLM/Governance confidence score bounded [0.0, 1.0]",
    ),
]


def validate_utc_freshness(dt: datetime) -> datetime:
    """Ensures timestamp is UTC and rejects future timestamps >5s (clock-skew violation).

    Why 5s? A tight 5-second window accommodates legitimate NTP server drift between edge
    connectors and core microservices while strictly blocking future-timestamp replay attacks.
    """
    now = datetime.now(UTC)
    parsed_dt = dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)

    if (parsed_dt - now).total_seconds() > MAX_CLOCK_SKEW_SECONDS:
        raise ValueError("Timestamp cannot be >5 seconds in the future (clock-skew violation)")
    return parsed_dt


UtcTimestamp = Annotated[
    datetime,
    Field(description="Valid ISO-8601 UTC timestamp with freshness check"),
    AfterValidator(validate_utc_freshness),
]
