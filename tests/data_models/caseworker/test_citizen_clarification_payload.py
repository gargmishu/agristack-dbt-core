"""Unit tests for CitizenClarificationPayload schema."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.data_models.caseworker import CitizenClarificationPayload


def test_citizen_clarification_payload_valid() -> None:
    now = datetime.now(UTC)
    payload = CitizenClarificationPayload(
        text="My survey number is 1042 in Karnal district.",
        received_at=now,
    )
    assert payload.text == "My survey number is 1042 in Karnal district."
    assert payload.received_at == now


def test_citizen_clarification_payload_too_short_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        CitizenClarificationPayload(
            text="no",
            received_at=datetime.now(UTC),
        )
    assert "String should have at least 3 characters" in str(exc.value)


def test_citizen_clarification_payload_whitespace_stripped() -> None:
    payload = CitizenClarificationPayload(
        text="   Valid clarification message   ",
        received_at=datetime.now(UTC),
    )
    assert payload.text == "Valid clarification message"
