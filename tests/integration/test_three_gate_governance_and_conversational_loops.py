"""Integration tests for Step 4.3: Three-Gate Governance & Conversational Loop Verification.

Executes end-to-end simulation suites verifying:
1. Gate 1 (Ingress & Structure Gate): Audio routing (Speech ASR -> SLM extraction) vs. USSD
   fast-path structured menu bypass (1.0 confidence, 0ms AI latency).
2. Gate 2 (Intake Validation Gate & Conversational Loop): Missing mandatory entity detection
   (District & Crop Name), multi-attempt conversational correction loops capped at 3 attempts,
   turn 2 recovery, and turn 3 exhaustion escalation.
3. Gate 3 (Deterministic Governance Routing Matrix): Tri-state routing across Automated Payout
   Approval (AUTO_APPROVE), Caseworker Escalation (ROUTE_FOR_MANUAL_REVIEW), and Automated
   Rejection (AUTO_REJECT) across duplicate season claims, unverified identity tokens, and
   cadastral land survey mismatches.

See: decisions/step4.3_three_gate_governance_and_conversational_loops.md
See: roadmap.md (Phase 4 Step 4.3)
"""

from datetime import UTC, datetime
from typing import Final

import pytest
from pydantic import HttpUrl

from src.data_models.common import (
    ApplicationIntent,
    ChannelType,
    DomainEntityKey,
    EligibilityStatus,
    GovernanceAction,
    LanguageLocale,
    PayloadType,
    RejectionReasonCode,
    StructureLevel,
)
from src.data_models.governance import ExtractedEntityPayload
from src.data_models.public_agent import PublicAgentStandardizedIntakePayload
from src.data_models.raw_ingress import (
    IvrIngressPayload,
    UssdIngressPayload,
    WhatsAppIngressPayload,
)
from src.orchestrator import ClaimOrchestrator
from src.public_agent import PublicAgentApi
from src.services.dpi.dpi_mock_fixtures import (
    INVALID_SURVEY_NUMBER,
    UNVERIFIED_IDENTITY_TOKEN_ZERO,
)

TEST_PEPPER_SECRET: Final[str] = "test_pepper_three_gate_governance_simulation_777"  # noqa: S105
TEST_CITIZEN_PHONE: Final[str] = "+919876543210"
VALID_HMAC_TOKEN: Final[str] = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"  # noqa: S105


@pytest.fixture(autouse=True)
def configure_governance_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configures environment secrets for three-gate governance simulations."""
    monkeypatch.setenv("AGRISTACK_PEPPER_SECRET", TEST_PEPPER_SECRET)
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "60")
    monkeypatch.setenv("RATE_LIMIT_BURST_CAPACITY", "20")


# =============================================================================
# 1. Gate 1: Ingress Modality & Structure Gate Verification
# =============================================================================


@pytest.mark.asyncio
async def test_gate1_ingress_audio_routing_vs_ussd_structured_bypass() -> None:
    """Verifies Gate 1 routes audio streams through ASR+SLM while USSD executes fast-path bypass."""
    public_agent_gateway = PublicAgentApi()
    current_time = datetime.now(UTC)

    # Path A: Audio Stream Ingress (IVR Voice Call -> Speech ASR -> SLM Entity Extraction)
    ivr_audio_payload = IvrIngressPayload(
        session_id="session_gate1_audio_01",
        originating_phone_number=TEST_CITIZEN_PHONE,
        audio_recording_url=HttpUrl("https://sip-gateway.telecom.in/audio/gate1_voice.wav"),
        audio_duration_seconds=25,
        received_at=current_time,
    )
    audio_result = await public_agent_gateway.process_raw_ingress(
        raw_payload=ivr_audio_payload,
        language_locale=LanguageLocale.HINDI,
    )
    audio_extracted = audio_result.orchestration_result.extracted_entities
    assert audio_result.intake_payload.payload_type == PayloadType.AUDIO
    assert audio_result.intake_payload.structure_level == StructureLevel.FREE_TEXT
    assert audio_extracted.is_structured_menu_bypass is False
    assert audio_extracted.ai_confidence_score >= 0.85  # noqa: PLR2004
    assert audio_extracted.application_intent == ApplicationIntent.APPLY_SUBSIDY

    # Path B: Structured Menu Ingress (USSD Signaling -> Fast-Path Bypass, 1.0 Confidence)
    ussd_menu_payload = UssdIngressPayload(
        session_id="session_gate1_ussd_02",
        originating_phone_number=TEST_CITIZEN_PHONE,
        ussd_service_code="*147#",
        ussd_user_digit_selection="1*2*101",
        received_at=current_time,
    )
    ussd_result = await public_agent_gateway.process_raw_ingress(
        raw_payload=ussd_menu_payload,
        language_locale=LanguageLocale.HINDI,
    )
    ussd_extracted = ussd_result.orchestration_result.extracted_entities
    assert ussd_result.intake_payload.structure_level == StructureLevel.DTMF_SELECTION
    assert ussd_extracted.is_structured_menu_bypass is True
    assert ussd_extracted.ai_confidence_score == 1.0
    assert ussd_extracted.domain_entities[DomainEntityKey.DISTRICT] == "Karnal"


# =============================================================================
# 2. Gate 2: Intake Completeness & Multi-Attempt Conversational Loop (Cap = 3)
# =============================================================================


@pytest.mark.asyncio
async def test_gate2_multi_attempt_conversational_loop_and_reprompt_recovery() -> None:
    """Verifies Gate 2 missing entity detection, 3-attempt cap, turn 2 recovery, and exhaustion."""
    public_agent_gateway = PublicAgentApi()
    current_time = datetime.now(UTC)

    incomplete_whatsapp_payload = WhatsAppIngressPayload(
        session_id="session_gate2_loop_100",
        originating_phone_number=TEST_CITIZEN_PHONE,
        channel_message_id="wamid.gate2_incomplete_1",
        payload_type=PayloadType.TEXT,
        text_body="missing crop details",
        received_at=current_time,
    )

    # Turn 1 (Attempt 1): Missing mandatory crop entity -> Triggers REQUEST_MORE_INFO reprompt
    turn1_result = await public_agent_gateway.process_raw_ingress(
        raw_payload=incomplete_whatsapp_payload,
        language_locale=LanguageLocale.HINDI,
        attempt_count=1,
    )
    assert turn1_result.orchestration_result.requires_reprompt is True
    assert (
        turn1_result.orchestration_result.governance_outcome.governance_action
        == GovernanceAction.REQUEST_MORE_INFO
    )
    assert turn1_result.orchestration_result.reprompt_message is not None
    assert "crop_name" in turn1_result.orchestration_result.reprompt_message

    # Turn 2 (Attempt 2 - Still Incomplete): Triggers second REQUEST_MORE_INFO reprompt
    turn2_incomplete = await public_agent_gateway.process_raw_ingress(
        raw_payload=incomplete_whatsapp_payload,
        language_locale=LanguageLocale.HINDI,
        attempt_count=2,
    )
    assert turn2_incomplete.orchestration_result.requires_reprompt is True
    assert (
        turn2_incomplete.orchestration_result.governance_outcome.governance_action
        == GovernanceAction.REQUEST_MORE_INFO
    )

    # Turn 2 Recovery (Citizen supplies complete entities on Turn 2) -> Advances to AUTO_APPROVE
    complete_whatsapp_payload = WhatsAppIngressPayload(
        session_id="session_gate2_loop_100",
        originating_phone_number=TEST_CITIZEN_PHONE,
        channel_message_id="wamid.gate2_complete_2",
        payload_type=PayloadType.TEXT,
        text_body="Mera khet 2.5 acre hai, fasal gehu, survey 101/2, zila Meerut",
        received_at=current_time,
    )
    turn2_recovered = await public_agent_gateway.process_raw_ingress(
        raw_payload=complete_whatsapp_payload,
        language_locale=LanguageLocale.HINDI,
        attempt_count=2,
    )
    assert turn2_recovered.orchestration_result.requires_reprompt is False
    assert (
        turn2_recovered.orchestration_result.governance_outcome.governance_action
        == GovernanceAction.AUTO_APPROVE
    )
    assert (
        turn2_recovered.orchestration_result.governance_outcome.eligibility_status
        == EligibilityStatus.ELIGIBLE
    )

    # Turn 3 (Attempt 3 Exhaustion - Max attempts reached with missing entities)
    # Loop terminates (requires_reprompt=False) and escalates to caseworker review
    turn3_exhausted = await public_agent_gateway.process_raw_ingress(
        raw_payload=incomplete_whatsapp_payload,
        language_locale=LanguageLocale.HINDI,
        attempt_count=3,
    )
    assert turn3_exhausted.orchestration_result.requires_reprompt is False
    assert (
        turn3_exhausted.orchestration_result.governance_outcome.governance_action
        == GovernanceAction.ROUTE_FOR_MANUAL_REVIEW
    )
    assert (
        turn3_exhausted.orchestration_result.governance_outcome.eligibility_status
        == EligibilityStatus.REQUIRES_REVIEW
    )
    assert turn3_exhausted.orchestration_result.caseworker_ticket_id is not None


# =============================================================================
# 3. Gate 3: Deterministic Policy Adjudication Matrix Verification
# =============================================================================


@pytest.mark.asyncio
async def test_gate3_automated_payout_approval_branch() -> None:
    """Verifies Gate 3 AUTO_APPROVE branch initiates automated payment clearance."""
    orchestrator = ClaimOrchestrator()
    standardized_intake = PublicAgentStandardizedIntakePayload(
        session_id="session_gate3_approve_01",
        tokenized_citizen_id=VALID_HMAC_TOKEN,
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale=LanguageLocale.HINDI,
        unprocessed_input_content="Complete agricultural claim input",
        received_at=datetime.now(UTC),
    )
    high_confidence_entities = ExtractedEntityPayload(
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        ai_confidence_score=0.95,
        domain_entities={
            DomainEntityKey.DISTRICT: "Karnal",
            DomainEntityKey.CROP_NAME: "Wheat",
            DomainEntityKey.SURVEY_NUMBER: "LAND-REC-1002",
        },
        is_adversarial_attempt=False,
        is_structured_menu_bypass=False,
    )

    execution_result = await orchestrator.execute_orchestration_cycle(
        intake=standardized_intake,
        extracted_entities=high_confidence_entities,
        attempt_count=1,
    )

    outcome = execution_result.governance_outcome
    assert outcome.governance_action == GovernanceAction.AUTO_APPROVE
    assert outcome.eligibility_status == EligibilityStatus.ELIGIBLE
    assert outcome.disbursement_txn_id is not None
    assert outcome.disbursement_txn_id.startswith("TXN-2026-")
    assert execution_result.disbursement_callback is not None
    assert execution_result.caseworker_ticket_id is None


@pytest.mark.asyncio
async def test_gate3_manual_caseworker_review_branch() -> None:
    """Verifies Gate 3 ROUTE_FOR_MANUAL_REVIEW branch stages caseworker review ticket."""
    orchestrator = ClaimOrchestrator()
    standardized_intake = PublicAgentStandardizedIntakePayload(
        session_id="session_gate3_review_02",
        tokenized_citizen_id=VALID_HMAC_TOKEN,
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale=LanguageLocale.HINDI,
        unprocessed_input_content="Ambiguous agricultural claim input",
        received_at=datetime.now(UTC),
    )
    low_confidence_entities = ExtractedEntityPayload(
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        ai_confidence_score=0.60,
        domain_entities={
            DomainEntityKey.DISTRICT: "Karnal",
            DomainEntityKey.CROP_NAME: "Wheat",
            DomainEntityKey.SURVEY_NUMBER: "LAND-REC-1002",
        },
        is_adversarial_attempt=False,
        is_structured_menu_bypass=False,
    )

    execution_result = await orchestrator.execute_orchestration_cycle(
        intake=standardized_intake,
        extracted_entities=low_confidence_entities,
        attempt_count=1,
    )

    outcome = execution_result.governance_outcome
    assert outcome.governance_action == GovernanceAction.ROUTE_FOR_MANUAL_REVIEW
    assert outcome.eligibility_status == EligibilityStatus.REQUIRES_REVIEW
    assert outcome.escalation_case_id is not None
    assert outcome.escalation_case_id.startswith("SPP-CASE-2026-")
    assert execution_result.caseworker_ticket_id == outcome.escalation_case_id
    assert execution_result.disbursement_callback is None


@pytest.mark.asyncio
async def test_gate3_auto_reject_duplicate_claim_active_season() -> None:
    """Verifies Gate 3 AUTO_REJECT branch for duplicate claim in the active crop season."""
    orchestrator = ClaimOrchestrator()
    standardized_intake = PublicAgentStandardizedIntakePayload(
        session_id="session_gate3_reject_duplicate",
        tokenized_citizen_id=VALID_HMAC_TOKEN,
        channel_type=ChannelType.SMS,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale=LanguageLocale.HINDI,
        unprocessed_input_content="Duplicate claim submission",
        received_at=datetime.now(UTC),
    )
    valid_entities = ExtractedEntityPayload(
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        ai_confidence_score=0.95,
        domain_entities={
            DomainEntityKey.DISTRICT: "Karnal",
            DomainEntityKey.CROP_NAME: "Wheat",
            DomainEntityKey.SURVEY_NUMBER: "LAND-REC-1002",
        },
        is_adversarial_attempt=False,
        is_structured_menu_bypass=False,
    )

    # Pre-populate ledger with existing active season claim for this citizen token
    existing_ledger = {(VALID_HMAC_TOKEN, "KHARIF-2026")}

    execution_result = await orchestrator.execute_orchestration_cycle(
        intake=standardized_intake,
        extracted_entities=valid_entities,
        attempt_count=1,
        approved_payouts_ledger=existing_ledger,
        active_season="KHARIF-2026",
    )

    outcome = execution_result.governance_outcome
    assert outcome.governance_action == GovernanceAction.AUTO_REJECT
    assert outcome.eligibility_status == EligibilityStatus.INELIGIBLE
    assert outcome.rejection_reason == RejectionReasonCode.DUPLICATE_CLAIM_ACTIVE_SEASON
    assert execution_result.disbursement_callback is None


@pytest.mark.asyncio
async def test_gate3_auto_reject_unverified_identity_token() -> None:
    """Verifies Gate 3 AUTO_REJECT branch when MOSIP identity verification fails."""
    orchestrator = ClaimOrchestrator()
    unverified_intake = PublicAgentStandardizedIntakePayload(
        session_id="session_gate3_reject_identity",
        tokenized_citizen_id=UNVERIFIED_IDENTITY_TOKEN_ZERO,
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale=LanguageLocale.HINDI,
        unprocessed_input_content="Claim with unverified identity token",
        received_at=datetime.now(UTC),
    )
    valid_entities = ExtractedEntityPayload(
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        ai_confidence_score=0.95,
        domain_entities={
            DomainEntityKey.DISTRICT: "Karnal",
            DomainEntityKey.CROP_NAME: "Wheat",
            DomainEntityKey.SURVEY_NUMBER: "LAND-REC-1002",
        },
        is_adversarial_attempt=False,
        is_structured_menu_bypass=False,
    )

    execution_result = await orchestrator.execute_orchestration_cycle(
        intake=unverified_intake,
        extracted_entities=valid_entities,
        attempt_count=1,
    )

    outcome = execution_result.governance_outcome
    assert outcome.governance_action == GovernanceAction.AUTO_REJECT
    assert outcome.eligibility_status == EligibilityStatus.INELIGIBLE
    assert outcome.rejection_reason == RejectionReasonCode.IDENTITY_NOT_VERIFIED
    assert execution_result.disbursement_callback is None


@pytest.mark.asyncio
async def test_gate3_auto_reject_cadastral_land_mismatch() -> None:
    """Verifies Gate 3 AUTO_REJECT branch when AgriStack cadastral survey verification fails."""
    orchestrator = ClaimOrchestrator()
    standardized_intake = PublicAgentStandardizedIntakePayload(
        session_id="session_gate3_reject_land",
        tokenized_citizen_id=VALID_HMAC_TOKEN,
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale=LanguageLocale.HINDI,
        unprocessed_input_content="Claim with invalid land survey number",
        received_at=datetime.now(UTC),
    )
    mismatched_land_entities = ExtractedEntityPayload(
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        ai_confidence_score=0.95,
        domain_entities={
            DomainEntityKey.DISTRICT: "Karnal",
            DomainEntityKey.CROP_NAME: "Wheat",
            DomainEntityKey.SURVEY_NUMBER: INVALID_SURVEY_NUMBER,
        },
        is_adversarial_attempt=False,
        is_structured_menu_bypass=False,
    )

    execution_result = await orchestrator.execute_orchestration_cycle(
        intake=standardized_intake,
        extracted_entities=mismatched_land_entities,
        attempt_count=1,
    )

    outcome = execution_result.governance_outcome
    assert outcome.governance_action == GovernanceAction.AUTO_REJECT
    assert outcome.eligibility_status == EligibilityStatus.INELIGIBLE
    assert outcome.rejection_reason == RejectionReasonCode.LAND_RECORD_NOT_FOUND
    assert execution_result.disbursement_callback is None
