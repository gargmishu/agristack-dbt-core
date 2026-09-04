from typing import Final

import pytest
from pydantic import ValidationError

from src.data_models.common import (
    ApplicationIntent,
    DomainEntityKey,
)
from src.data_models.governance.claim_evaluation_payload import (
    ClaimEvaluationPayload,
)
from src.data_models.governance.extracted_entity_payload import (
    ExtractedEntityPayload,
)

MOCK_CITIZEN_TOKEN: Final[str] = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"  # noqa: S105


def _create_sample_extracted_payload() -> ExtractedEntityPayload:
    return ExtractedEntityPayload(
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        ai_confidence_score=0.92,
        domain_entities={
            DomainEntityKey.DISTRICT: "Karnal",
            DomainEntityKey.CROP_NAME: "Wheat",
            DomainEntityKey.SURVEY_NUMBER: "LAND-REC-1002",
        },
    )


def test_claim_evaluation_payload_valid_instantiation() -> None:
    extracted = _create_sample_extracted_payload()
    payload = ClaimEvaluationPayload(
        session_id="sess_eval_12345",
        payload_id="ext-payload-123",
        tokenized_citizen_id=MOCK_CITIZEN_TOKEN,
        extracted_payload=extracted,
        active_season="KHARIF-2026",
        approved_payouts_ledger={(MOCK_CITIZEN_TOKEN, "RABI-2025")},
    )

    assert payload.session_id == "sess_eval_12345"
    assert payload.payload_id == "ext-payload-123"
    assert payload.tokenized_citizen_id == MOCK_CITIZEN_TOKEN
    assert payload.active_season == "KHARIF-2026"
    assert len(payload.approved_payouts_ledger) == 1


def test_claim_evaluation_payload_defaults() -> None:
    extracted = _create_sample_extracted_payload()
    payload = ClaimEvaluationPayload(
        session_id="sess_eval_12345",
        payload_id="ext-payload-123",
        tokenized_citizen_id=MOCK_CITIZEN_TOKEN,
        extracted_payload=extracted,
    )

    assert payload.active_season == "KHARIF-2026"
    assert payload.approved_payouts_ledger == set()


def test_claim_evaluation_payload_invalid_token() -> None:
    extracted = _create_sample_extracted_payload()
    with pytest.raises(ValidationError):
        ClaimEvaluationPayload(
            session_id="sess_eval_12345",
            payload_id="ext-payload-123",
            tokenized_citizen_id="invalid_short_token",
            extracted_payload=extracted,
        )


def test_claim_evaluation_payload_invalid_session_id() -> None:
    extracted = _create_sample_extracted_payload()
    with pytest.raises(ValidationError):
        ClaimEvaluationPayload(
            session_id="shrt",
            payload_id="ext-payload-123",
            tokenized_citizen_id=MOCK_CITIZEN_TOKEN,
            extracted_payload=extracted,
        )
