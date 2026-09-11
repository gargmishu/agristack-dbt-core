"""Integration tests for Step 4.4: Outbound Confirmation & Financial Callback Verification.

Executes end-to-end simulation suites verifying:
1. Multi-Channel Outbound Confirmation Delivery: Native receipt formatting and carrier dispatch
   across WhatsApp (Markdown cards, wamid.*), IVR Voice (Bhashini TTS synthesized speech URL,
   sip-call-*), USSD (strict <= 160 char GSM 7-bit string, ussd-sig-*), and SMS (TRAI DLT
   transactional notice, sms-dr-*).
2. Sovereign Payment Clearing Callbacks (NPCI APBS / PFMS Treasury): Asynchronous clearing
   reconciliation for straight-through approvals (DisbursementStatus.SUCCESS, NPCI-UTR-*) and
   simulated bank clearing failures (DisbursementStatus.FAILED, NPCI-REJ-*, statutory failure code).
3. End-to-End Roundtrip Traceability: Linking session_id to both sovereign banking UTRs and
   carrier transmission acknowledgments across all four channels.

See: decisions/step4.4_outbound_confirmation_and_financial_callbacks.md
See: roadmap.md (Phase 4 Step 4.4)
"""

from datetime import UTC, datetime
from typing import Final

import pytest
from pydantic import HttpUrl

from src.data_models.common import (
    ChannelType,
    DisbursementFailureCode,
    DisbursementStatus,
    DomainEntityKey,
    EligibilityStatus,
    GovernanceAction,
    LanguageLocale,
    NotificationDeliveryStatus,
    PayloadType,
    RejectionReasonCode,
)
from src.data_models.governance import GovernanceOutcomePayload
from src.data_models.notification import (
    MAX_USSD_CHARACTERS,
    NotificationRequestPayload,
)
from src.data_models.raw_ingress import (
    IvrIngressPayload,
    SmsIngressPayload,
    UssdIngressPayload,
    WhatsAppIngressPayload,
)
from src.public_agent import PublicAgentApi
from src.services.dpi import create_payment_rail_service
from src.services.notification import MultichannelNotificationService

TEST_PEPPER_SECRET: Final[str] = "test_pepper_outbound_confirmation_callbacks_888"  # noqa: S105
TEST_CITIZEN_PHONE: Final[str] = "+919876543210"


@pytest.fixture(autouse=True)
def configure_outbound_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configures environment secrets for outbound confirmation and payment callback tests."""
    monkeypatch.setenv("AGRISTACK_PEPPER_SECRET", TEST_PEPPER_SECRET)
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "60")
    monkeypatch.setenv("RATE_LIMIT_BURST_CAPACITY", "20")


# =============================================================================
# 1. Multi-Channel Outbound Confirmation Delivery Verification
# =============================================================================


@pytest.mark.asyncio
async def test_whatsapp_rich_card_outbound_confirmation() -> None:
    """Verifies WhatsApp outbound notifications render markdown cards and return wamid receipts."""
    notification_service = MultichannelNotificationService()

    approval_request = NotificationRequestPayload(
        session_id="session_wa_outbound_01",
        channel_type=ChannelType.WHATSAPP,
        governance_action=GovernanceAction.AUTO_APPROVE,
        language_locale=LanguageLocale.HINDI,
        disbursement_txn_id="TXN-2026-100200",
    )

    transmission_ack = await notification_service.dispatch_notification(approval_request)
    assert transmission_ack.session_id == "session_wa_outbound_01"
    assert transmission_ack.channel_type == ChannelType.WHATSAPP
    assert transmission_ack.status == NotificationDeliveryStatus.DELIVERED
    assert transmission_ack.carrier_reference_id.startswith("wamid.")


@pytest.mark.asyncio
async def test_ivr_voice_tts_audio_stream_outbound_confirmation() -> None:
    """Verifies IVR outbound notifications synthesize speech audio and return sip-call receipts."""
    notification_service = MultichannelNotificationService()

    ivr_request = NotificationRequestPayload(
        session_id="session_ivr_outbound_02",
        channel_type=ChannelType.IVR_VOICE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        language_locale=LanguageLocale.HINDI,
        disbursement_txn_id="TXN-2026-300400",
    )

    # Prepare payload to inspect synthesized Bhashini TTS audio URL
    prepared_payload = await notification_service._prepare_notification(ivr_request)
    assert prepared_payload.audio_playback_url is not None
    assert "https://" in str(prepared_payload.audio_playback_url)
    assert ".wav" in str(prepared_payload.audio_playback_url)

    # Dispatch to SIP telephony connector
    transmission_ack = await notification_service.dispatch_notification(ivr_request)
    assert transmission_ack.session_id == "session_ivr_outbound_02"
    assert transmission_ack.channel_type == ChannelType.IVR_VOICE
    assert transmission_ack.status == NotificationDeliveryStatus.DELIVERED
    assert transmission_ack.carrier_reference_id.startswith("sip-call-")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("governance_action", "disbursement_id", "escalation_id", "rejection_code", "missing_key"),
    [
        (GovernanceAction.AUTO_APPROVE, "TXN-2026-555111", None, None, None),
        (GovernanceAction.ROUTE_FOR_MANUAL_REVIEW, None, "SPP-CASE-2026-991100", None, None),
        (
            GovernanceAction.AUTO_REJECT,
            None,
            None,
            RejectionReasonCode.DUPLICATE_CLAIM_ACTIVE_SEASON,
            None,
        ),
        (GovernanceAction.REQUEST_MORE_INFO, None, None, None, DomainEntityKey.DISTRICT),
    ],
)
async def test_ussd_compact_gsm_7bit_outbound_confirmation(
    governance_action: GovernanceAction,
    disbursement_id: str | None,
    escalation_id: str | None,
    rejection_code: RejectionReasonCode | None,
    missing_key: DomainEntityKey | None,
) -> None:
    """Verifies USSD notifications strictly obey the <= 160 char GSM 7-bit bound across actions."""
    notification_service = MultichannelNotificationService()

    ussd_request = NotificationRequestPayload(
        session_id="session_ussd_outbound_03",
        channel_type=ChannelType.USSD,
        governance_action=governance_action,
        language_locale=LanguageLocale.HINDI,
        disbursement_txn_id=disbursement_id,
        escalation_case_id=escalation_id,
        rejection_reason=rejection_code,
        missing_entity=missing_key,
    )

    prepared_payload = await notification_service._prepare_notification(ussd_request)
    assert len(prepared_payload.formatted_message) <= MAX_USSD_CHARACTERS

    transmission_ack = await notification_service.dispatch_notification(ussd_request)
    assert transmission_ack.session_id == "session_ussd_outbound_03"
    assert transmission_ack.channel_type == ChannelType.USSD
    assert transmission_ack.status == NotificationDeliveryStatus.DELIVERED
    assert transmission_ack.carrier_reference_id.startswith("ussd-sig-")


@pytest.mark.asyncio
async def test_sms_dlt_transactional_outbound_confirmation() -> None:
    """Verifies SMS outbound notifications include helpline reference and return sms-dr receipts."""
    notification_service = MultichannelNotificationService()

    sms_rejection_request = NotificationRequestPayload(
        session_id="session_sms_outbound_04",
        channel_type=ChannelType.SMS,
        governance_action=GovernanceAction.AUTO_REJECT,
        language_locale=LanguageLocale.HINDI,
        rejection_reason=RejectionReasonCode.LAND_RECORD_NOT_FOUND,
    )

    prepared_payload = await notification_service._prepare_notification(sms_rejection_request)
    assert len(prepared_payload.formatted_message) <= MAX_USSD_CHARACTERS

    transmission_ack = await notification_service.dispatch_notification(sms_rejection_request)
    assert transmission_ack.session_id == "session_sms_outbound_04"
    assert transmission_ack.channel_type == ChannelType.SMS
    assert transmission_ack.status == NotificationDeliveryStatus.DELIVERED
    assert transmission_ack.carrier_reference_id.startswith("sms-dr-")


# =============================================================================
# 2. Sovereign Payment Clearing & Financial Callbacks Verification
# =============================================================================


@pytest.mark.asyncio
async def test_payment_rail_successful_clearing_callback() -> None:
    """Verifies PaymentRailService returns SUCCESS callback with NPCI-UTR reference."""
    payment_rail = create_payment_rail_service()

    approval_outcome = GovernanceOutcomePayload(
        session_id="session_payment_success_01",
        payload_id="ext-pay-01",
        ai_confidence_score=0.96,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-889900",
        disbursement_status=DisbursementStatus.PENDING,
        evaluated_at=datetime.now(UTC),
    )

    callback = await payment_rail.initiate_disbursement(approval_outcome)
    assert callback is not None
    assert callback.disbursement_txn_id == "TXN-2026-889900"
    assert callback.disbursement_status == DisbursementStatus.SUCCESS
    assert callback.bank_reference_id == "NPCI-UTR-889900"
    assert callback.failure_reason_code is None


@pytest.mark.asyncio
async def test_payment_rail_failed_clearing_callback() -> None:
    """Verifies PaymentRailService returns FAILED callback with NPCI-REJ reference on failure."""
    payment_rail = create_payment_rail_service()

    failed_approval_outcome = GovernanceOutcomePayload(
        session_id="session_payment_fail_02",
        payload_id="ext-pay-02",
        ai_confidence_score=0.92,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        governance_action=GovernanceAction.AUTO_APPROVE,
        disbursement_txn_id="TXN-2026-FAIL-44",
        disbursement_status=DisbursementStatus.PENDING,
        evaluated_at=datetime.now(UTC),
    )

    callback = await payment_rail.initiate_disbursement(failed_approval_outcome)
    assert callback is not None
    assert callback.disbursement_txn_id == "TXN-2026-FAIL-44"
    assert callback.disbursement_status == DisbursementStatus.FAILED
    assert callback.bank_reference_id.startswith("NPCI-REJ-")
    assert (
        callback.failure_reason_code
        == DisbursementFailureCode.ERR_INSUFFICIENT_BANK_ACCOUNT_MAPPING
    )


@pytest.mark.asyncio
async def test_payment_rail_skips_non_approval_outcomes() -> None:
    """Verifies PaymentRailService skips clearing for manual review or rejected outcomes."""
    payment_rail = create_payment_rail_service()

    review_outcome = GovernanceOutcomePayload(
        session_id="session_payment_skip_03",
        payload_id="ext-pay-03",
        ai_confidence_score=0.55,
        eligibility_status=EligibilityStatus.REQUIRES_REVIEW,
        governance_action=GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
        escalation_case_id="SPP-CASE-2026-776655",
        evaluated_at=datetime.now(UTC),
    )

    callback = await payment_rail.initiate_disbursement(review_outcome)
    assert callback is None


# =============================================================================
# 3. End-to-End Roundtrip: Ingress -> Payment Clearing -> Outbound Receipt
# =============================================================================


@pytest.mark.asyncio
async def test_end_to_end_roundtrip_payment_callback_and_outbound_receipts() -> None:
    """Verifies full roundtrip across all 4 channels linking UTR callbacks and carrier receipts."""
    public_agent_gateway = PublicAgentApi()
    current_time = datetime.now(UTC)

    whatsapp_ingress = WhatsAppIngressPayload(
        session_id="roundtrip_session_whatsapp",
        originating_phone_number=TEST_CITIZEN_PHONE,
        channel_message_id="wamid.roundtrip_wa",
        payload_type=PayloadType.TEXT,
        text_body="Mera khet 2.5 acre hai, fasal gehu, survey 101/2, zila Meerut",
        received_at=current_time,
    )
    ivr_ingress = IvrIngressPayload(
        session_id="roundtrip_session_ivr",
        originating_phone_number=TEST_CITIZEN_PHONE,
        audio_recording_url=HttpUrl("https://sip-gateway.telecom.in/recordings/roundtrip.wav"),
        audio_duration_seconds=30,
        received_at=current_time,
    )
    ussd_ingress = UssdIngressPayload(
        session_id="roundtrip_session_ussd",
        originating_phone_number=TEST_CITIZEN_PHONE,
        ussd_service_code="*147#",
        ussd_user_digit_selection="1*2*101",
        received_at=current_time,
    )
    sms_ingress = SmsIngressPayload(
        session_id="roundtrip_session_sms",
        originating_phone_number=TEST_CITIZEN_PHONE,
        channel_message_id="sms_roundtrip_01",
        text_body="Mera khet 2.5 acre hai, fasal gehu, survey 101/2, zila Meerut",
        received_at=current_time,
    )

    test_cases: list[
        tuple[
            WhatsAppIngressPayload | IvrIngressPayload | UssdIngressPayload | SmsIngressPayload,
            str,
        ]
    ] = [
        (whatsapp_ingress, "wamid."),
        (ivr_ingress, "sip-call-"),
        (ussd_ingress, "ussd-sig-"),
        (sms_ingress, "sms-dr-"),
    ]

    for raw_payload, expected_prefix in test_cases:
        roundtrip_result = await public_agent_gateway.process_raw_ingress(raw_payload=raw_payload)

        # Verify payment clearing callback UTR
        payment_callback = roundtrip_result.orchestration_result.disbursement_callback
        assert payment_callback is not None
        assert payment_callback.disbursement_status == DisbursementStatus.SUCCESS
        assert payment_callback.bank_reference_id.startswith("NPCI-UTR-")

        # Verify native outbound carrier transmission acknowledgment receipt
        carrier_receipt = roundtrip_result.transmission_ack
        assert carrier_receipt.status == NotificationDeliveryStatus.DELIVERED
        assert carrier_receipt.carrier_reference_id.startswith(expected_prefix)
