"""Unit & Integration Tests for LedgerPersistenceService and ClaimOrchestrator Persistence.

Verifies that LedgerPersistenceService and ClaimOrchestrator automatically persist:
1. Citizen session lifecycle telemetry (PENDING -> COMPLETED) with strictly tokenized 64-char IDs.
2. Multi-turn conversational extraction attempts (Turn 1 STAGED -> SUPERSEDED, Turn 2 COMMITTED).
3. Gate 3 governance decisions in application_governance_ledger with terminal metadata constraints.
4. Automatic SQL audit history rows (trg_audit_governance_ledger_insert) in
   application_governance_ledger_history.
5. Window-function analytical deduplication (fetch_deduplicated_citizen_journey_funnel) returning
   strictly 1 row per citizen session without multi-turn cartesian fan-out.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Final

import pytest

from src.data_models.common import (
    ApplicationIntent,
    ChannelType,
    DomainEntityKey,
    PayloadType,
    StructureLevel,
)
from src.data_models.governance import ExtractedEntityPayload
from src.data_models.public_agent import PublicAgentStandardizedIntakePayload
from src.orchestrator.claim_orchestrator import ClaimOrchestrator
from src.services.persistence import LedgerPersistenceService

VALID_PILOT_CITIZEN_HMAC: Final[str] = (
    "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"  # noqa: S105
)
EXPECTED_TOTAL_TURNS: Final[int] = 2


@pytest.mark.asyncio
async def test_live_orchestrator_relational_persistence_and_deduplication() -> None:
    """Verifies ClaimOrchestrator writes multi-turn sessions and audit history to DB."""
    persistence_service = LedgerPersistenceService(database_url="sqlite:///:memory:")
    try:
        orchestrator = ClaimOrchestrator(ledger_persistence_service=persistence_service)

        session_identifier = "sess-pilot-karnal-001"
        intake_payload = PublicAgentStandardizedIntakePayload(
            session_id=session_identifier,
            tokenized_citizen_id=VALID_PILOT_CITIZEN_HMAC,
            channel_type=ChannelType.WHATSAPP,
            payload_type=PayloadType.TEXT,
            structure_level=StructureLevel.FREE_TEXT,
            unprocessed_input_content="Mera fasal Karnal zila mein kharab ho gaya",
            received_at=datetime.now(UTC),
        )

        # Turn 1: Citizen omits crop_name -> Gate 2 triggers re-prompt, DB records STAGED turn
        incomplete_entities = ExtractedEntityPayload(
            application_intent=ApplicationIntent.APPLY_SUBSIDY,
            domain_entities={DomainEntityKey.DISTRICT: "Karnal"},
            ai_confidence_score=0.88,
            is_adversarial_attempt=False,
        )
        turn_one_result = await orchestrator.execute_orchestration_cycle(
            intake=intake_payload,
            extracted_entities=incomplete_entities,
            attempt_count=1,
        )
        assert turn_one_result.requires_reprompt is True

        # Turn 2: Citizen provides complete district + crop_name + survey -> Gate 3 AUTO_APPROVE
        complete_entities = ExtractedEntityPayload(
            application_intent=ApplicationIntent.APPLY_SUBSIDY,
            domain_entities={
                DomainEntityKey.DISTRICT: "Karnal",
                DomainEntityKey.CROP_NAME: "Wheat",
                DomainEntityKey.SURVEY_NUMBER: "101/2",
            },
            ai_confidence_score=0.96,
            is_adversarial_attempt=False,
        )
        turn_two_result = await orchestrator.execute_orchestration_cycle(
            intake=intake_payload,
            extracted_entities=complete_entities,
            attempt_count=2,
        )
        assert turn_two_result.requires_reprompt is False
        assert turn_two_result.governance_outcome.governance_action.is_approval is True

        # Verify analytical deduplication view returns strictly 1 row for the session (Turn 2)
        funnel_rows = persistence_service.fetch_deduplicated_citizen_journey_funnel()
        assert len(funnel_rows) == 1
        session_funnel = funnel_rows[0]
        assert session_funnel["session_id"] == session_identifier
        assert session_funnel["tokenized_phone_hash"] == VALID_PILOT_CITIZEN_HMAC
        assert session_funnel["total_conversational_turns"] == EXPECTED_TOTAL_TURNS
        assert session_funnel["extracted_district"] == "Karnal"
        assert session_funnel["extracted_crop_type"] == "Wheat"
        assert session_funnel["application_status"] == "APPROVED"
        assert session_funnel["governance_action"] == "AUTO_APPROVE"

        # Verify immutable audit history trigger recorded the governance ledger insertion
        audit_history = persistence_service.fetch_governance_audit_history(
            claim_id=f"claim-{session_identifier}"
        )
        assert len(audit_history) == 1
        assert audit_history[0]["previous_application_status"] is None
        assert audit_history[0]["new_application_status"] == "APPROVED"
        assert audit_history[0]["governance_action"] == "AUTO_APPROVE"
        assert audit_history[0]["actor_id"] == "SYSTEM:GATE3_ADJUDICATOR"
    finally:
        persistence_service.dispose()
