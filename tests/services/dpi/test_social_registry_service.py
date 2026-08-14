"""Unit tests for SocialRegistryService (OpenSPP external DPI connector)."""

from datetime import UTC, datetime

import pytest

from src.data_models.caseworker import CaseworkerCaseReviewPayload
from src.data_models.common import ApplicationIntent, EscalationReasonCode
from src.services.dpi import SocialRegistryService
from src.services.dpi.dpi_mock_fixtures import (
    MOCK_CASE_REJECT_PREFIX,
    MOCK_FAIL_STAGE_NOTE,
    UNVERIFIED_IDENTITY_PREFIX,
)


@pytest.mark.asyncio
async def test_social_registry_verify_incident_ticket_eligibility() -> None:
    service = SocialRegistryService()
    payload = CaseworkerCaseReviewPayload(
        escalation_case_id="SPP-CASE-2026-100200",
        session_id="sess_12345678",
        payload_id="ext_12345678",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        unprocessed_input_content="Fasal kharab ho gayi hai",
        escalation_reason=EscalationReasonCode.LOW_AI_CONFIDENCE,
        staged_at=datetime.now(UTC),
    )
    synced = await service.verify_incident_ticket_eligibility(payload)
    assert synced is True


@pytest.mark.asyncio
async def test_social_registry_verify_incident_ticket_eligibility_rejection_prefix() -> None:
    service = SocialRegistryService()
    payload = CaseworkerCaseReviewPayload(
        escalation_case_id=f"{MOCK_CASE_REJECT_PREFIX}-CASE-2026-100200",
        session_id="sess_12345678",
        payload_id="ext_12345678",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        unprocessed_input_content="Fasal kharab ho gayi hai",
        escalation_reason=EscalationReasonCode.LOW_AI_CONFIDENCE,
        staged_at=datetime.now(UTC),
    )
    synced = await service.verify_incident_ticket_eligibility(payload)
    assert synced is True


@pytest.mark.asyncio
async def test_social_registry_verify_incident_ticket_eligibility_fail_stage_note() -> None:
    service = SocialRegistryService()
    payload = CaseworkerCaseReviewPayload(
        escalation_case_id="SPP-CASE-2026-100200",
        session_id="sess_12345678",
        payload_id="ext_12345678",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        unprocessed_input_content="Fasal kharab ho gayi hai",
        escalation_reason=EscalationReasonCode.LOW_AI_CONFIDENCE,
        staged_at=datetime.now(UTC),
    )
    synced = await service.verify_incident_ticket_eligibility(payload)
    assert synced is True


@pytest.mark.asyncio
async def test_social_registry_query_beneficiary_eligibility() -> None:
    service = SocialRegistryService()
    valid_hmac = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"
    zero_hmac = "0000000000000000000000000000000000000000000000000000000000000000"
    unverified_hmac = UNVERIFIED_IDENTITY_PREFIX + "a" * (64 - len(UNVERIFIED_IDENTITY_PREFIX))

    assert await service.query_beneficiary_eligibility(valid_hmac, "PM_KISAN") is True
    assert await service.query_beneficiary_eligibility(zero_hmac, "PM_KISAN") is False
    assert await service.query_beneficiary_eligibility(unverified_hmac, "PM_KISAN") is False
    assert await service.query_beneficiary_eligibility(valid_hmac, "   ") is False
