from datetime import UTC, datetime

import pytest

from src.data_models.caseworker import CaseworkerCaseReviewPayload
from src.data_models.common import ApplicationIntent
from src.services.dpi import SocialRegistryService


@pytest.mark.asyncio
async def test_social_registry_stage_case_review() -> None:
    service = SocialRegistryService()
    payload = CaseworkerCaseReviewPayload(
        escalation_case_id="SPP-CASE-2026-100200",
        session_id="sess_12345678",
        payload_id="ext_12345678",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        unprocessed_input_content="Fasal kharab ho gayi hai",
        escalation_reason="AI extraction confidence below threshold",
        staged_at=datetime.now(UTC),
    )
    staged = await service.stage_case_review(payload)
    assert staged is True
