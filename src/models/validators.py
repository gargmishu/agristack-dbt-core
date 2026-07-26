"""Shared field type annotations and reusable validation rules across domain payloads."""

from typing import Annotated

from pydantic import Field

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
