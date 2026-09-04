from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.data_models.caseworker import CaseworkerCaseReviewPayload
from src.data_models.common import ApplicationIntent, EscalationReasonCode


def test_case_review_payload_valid() -> None:
    payload = CaseworkerCaseReviewPayload(
        escalation_case_id="SPP-CASE-2026-981245",
        session_id="sess_12345678",
        payload_id="550e8400-e29b-41d4-a716-446655440000",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        unprocessed_input_content="Voice note transcript",
        escalation_reason=EscalationReasonCode.LOW_AI_CONFIDENCE,
        staged_at=datetime.now(UTC),
    )
    assert payload.escalation_case_id == "SPP-CASE-2026-981245"
    assert payload.escalation_reason == EscalationReasonCode.LOW_AI_CONFIDENCE


def test_case_review_payload_empty_content_rejected() -> None:
    with pytest.raises(ValidationError) as exception_info:
        CaseworkerCaseReviewPayload(
            escalation_case_id="SPP-CASE-2026-981245",
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
            application_intent=ApplicationIntent.APPLY_SUBSIDY,
            unprocessed_input_content="   ",
            escalation_reason=EscalationReasonCode.LOW_AI_CONFIDENCE,
            staged_at=datetime.now(UTC),
        )
    assert "String should have at least 1 character" in str(exception_info.value)


def test_case_review_payload_invalid_enum_reason_rejected() -> None:
    with pytest.raises(ValidationError) as exception_info:
        CaseworkerCaseReviewPayload(
            escalation_case_id="SPP-CASE-2026-981245",
            session_id="sess_12345678",
            payload_id="550e8400-e29b-41d4-a716-446655440000",
            tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
            application_intent=ApplicationIntent.APPLY_SUBSIDY,
            unprocessed_input_content="Voice note transcript",
            escalation_reason="INVALID_REASON",  # type: ignore[arg-type]
            staged_at=datetime.now(UTC),
        )
    assert "Input should be 'LOW_AI_CONFIDENCE'" in str(exception_info.value)
