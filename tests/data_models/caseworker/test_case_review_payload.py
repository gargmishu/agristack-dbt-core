from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.data_models.caseworker import CaseworkerCaseReviewPayload
from src.data_models.common import ApplicationIntent


def test_case_review_payload_valid() -> None:
    payload = CaseworkerCaseReviewPayload(
        escalation_case_id="SPP-CASE-2026-981245",
        session_id="sess_12345678",
        payload_id="550e8400-e29b-41d4-a716-446655440000",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        unprocessed_input_content="Voice note transcript",
        escalation_reason="LOW_CONFIDENCE",
        staged_at=datetime.now(UTC),
    )
    assert payload.escalation_case_id == "SPP-CASE-2026-981245"


def test_case_review_payload_empty_content_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        CaseworkerCaseReviewPayload(
            escalation_case_id="SPP-CASE-2026-981245",
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
            application_intent=ApplicationIntent.APPLY_SUBSIDY,
            unprocessed_input_content="   ",
            escalation_reason="LOW_CONFIDENCE",
            staged_at=datetime.now(UTC),
        )
    assert "unprocessed_input_content cannot be empty or whitespace" in str(exc.value)
