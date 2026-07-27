"""Shared field type annotations and reusable validation rules across domain payloads."""

from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, Field

ChannelSessionId = Annotated[
    str,
    Field(
        min_length=8,
        max_length=128,
        description="Unified channel session ID (entropy floor >=8, ceiling <=128)",
    ),
]

PhoneNumberE164 = Annotated[
    str,
    Field(
        pattern=r"^\+[1-9]\d{1,14}$",
        description="Originating E.164 international phone number format (+919876543210)",
    ),
]

HMACCitizenToken = Annotated[
    str,
    Field(
        pattern=r"^[a-fA-F0-9]{64}$",
        description="Zero-PII SHA-256 HMAC citizen identity token (64-char hex)",
    ),
]

EscalationCaseId = Annotated[
    str,
    Field(
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

MAX_CLOCK_SKEW_SECONDS = 5.0


def validate_utc_freshness(dt: datetime) -> datetime:
    """Ensures timestamp is UTC and rejects future timestamps >5s (clock-skew violation)."""
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
