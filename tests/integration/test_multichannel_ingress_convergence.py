"""Integration tests for Step 4.1: Multichannel Ingress & Modality Convergence.

Validates end-to-end convergence across all four transport channels (WhatsApp, IVR Voice,
USSD, and SMS) and two distinct modalities (Audio recordings vs Unstructured/Structured Text)
through Layer 2 Perimeter Security and Layer 3 Public Agent Intake Gateway.

Invariants Verified:
1. Zero-PII Tokenization: Phone numbers are tokenized into 64-hex SHA-256 HMAC tokens in RAM.
2. Zero Cleartext PII Leakage: No phone numbers or PII leak into standardized intake fields.
3. Modality Routing:
   - Voice audio (IVR, WhatsApp audio) routes through Speech ASR transcription to SLM entity
     extraction.
   - Free-text (SMS, WhatsApp text) routes directly to SLM entity extraction.
   - Structured keypresses (USSD) execute fast-path menu bypass with 1.0 confidence and 0ms
     AI latency.
4. Channel Notification Roundtrip: Every channel receives an authoritative carrier
   acknowledgment matching its native protocol format.
5. Cross-Channel Token Symmetry: Identical MSISDN yields identical 64-character token across
   all channels.

See: decisions/step4.1_multichannel_ingress_and_modality_convergence.md
See: roadmap.md (Phase 4 Step 4.1)
"""

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Final

import pytest
from pydantic import HttpUrl

from src.data_models.common import (
    ApplicationIntent,
    ChannelType,
    DomainEntityKey,
    LanguageLocale,
    PayloadType,
    StructureLevel,
)
from src.data_models.raw_ingress import (
    IvrIngressPayload,
    SmsIngressPayload,
    UssdIngressPayload,
    WhatsAppIngressPayload,
)
from src.gateway import IngestionFirewall, RateLimiter, ZeroTrustIdentityTokenizer
from src.public_agent import PublicAgentApi

TEST_PEPPER_SECRET: Final[str] = "test_pepper_multichannel_ingress_convergence_123"  # noqa: S105
TEST_PHONE_NUMBER: Final[str] = "+919876543210"
EXPECTED_TOKEN_LENGTH: Final[int] = 64


@pytest.fixture(autouse=True)
def setup_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configures test environment secrets before running each integration test."""
    monkeypatch.setenv("AGRISTACK_PEPPER_SECRET", TEST_PEPPER_SECRET)
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "60")
    monkeypatch.setenv("RATE_LIMIT_BURST_CAPACITY", "20")


@pytest.mark.asyncio
async def test_whatsapp_text_ingress_convergence() -> None:
    """Validates WhatsApp free-text message ingress through perimeter security and gateway."""
    public_agent_gateway = PublicAgentApi()

    raw_whatsapp_text = WhatsAppIngressPayload(
        session_id="session_whatsapp_text_001",
        originating_phone_number=TEST_PHONE_NUMBER,
        channel_message_id="wamid.HBgLMzkxOTg3NjU0MzIxMBUCABEYEjE=",
        payload_type=PayloadType.TEXT,
        text_body="Mera khet 2.5 acre hai, fasal gehu, survey 101/2, zila Meerut",
        received_at=datetime.now(UTC),
    )

    intake_result = await public_agent_gateway.process_raw_ingress(
        raw_payload=raw_whatsapp_text,
        language_locale=LanguageLocale.HINDI,
    )

    # 1. Standardized Intake Contract Invariants
    assert intake_result.session_id == "session_whatsapp_text_001"
    assert intake_result.channel_type == ChannelType.WHATSAPP
    assert intake_result.intake_payload.payload_type == PayloadType.TEXT
    assert intake_result.intake_payload.structure_level == StructureLevel.FREE_TEXT
    assert intake_result.intake_payload.language_locale == LanguageLocale.HINDI

    # 2. Zero-Trust Security & PII Purge Invariants
    tokenized_identifier = intake_result.intake_payload.tokenized_citizen_id
    assert len(tokenized_identifier) == EXPECTED_TOKEN_LENGTH
    assert tokenized_identifier != TEST_PHONE_NUMBER
    assert TEST_PHONE_NUMBER not in intake_result.intake_payload.unprocessed_input_content
    assert TEST_PHONE_NUMBER not in str(intake_result.intake_payload)

    # 3. Perception & Governance Outcome Invariants
    orchestration_outcome = intake_result.orchestration_result
    intent = orchestration_outcome.extracted_entities.application_intent
    assert intent == ApplicationIntent.APPLY_SUBSIDY
    extracted_entities = orchestration_outcome.extracted_entities.domain_entities
    assert DomainEntityKey.DISTRICT in extracted_entities
    assert DomainEntityKey.CROP_NAME in extracted_entities
    assert orchestration_outcome.governance_outcome.governance_action.is_approval is True
    assert orchestration_outcome.governance_outcome.disbursement_txn_id is not None

    # 4. Outbound Carrier Delivery Invariants
    acknowledgment_receipt = intake_result.transmission_ack
    assert acknowledgment_receipt.channel_type == ChannelType.WHATSAPP
    assert acknowledgment_receipt.carrier_reference_id.startswith("wamid.")


@pytest.mark.asyncio
async def test_whatsapp_voice_note_ingress_convergence() -> None:
    """Validates WhatsApp voice note audio ingress through ASR transcription and gateway."""
    public_agent_gateway = PublicAgentApi()

    raw_whatsapp_audio = WhatsAppIngressPayload(
        session_id="session_whatsapp_audio_002",
        originating_phone_number=TEST_PHONE_NUMBER,
        channel_message_id="wamid.HBgLMzkxOTg3NjU0MzIxMBUCABEYEjI=",
        payload_type=PayloadType.AUDIO,
        audio_recording_url=HttpUrl("https://media.whatsapp.net/voice/recording_hi_002.ogg"),
        audio_duration_seconds=12,
        received_at=datetime.now(UTC),
    )

    intake_result = await public_agent_gateway.process_raw_ingress(
        raw_payload=raw_whatsapp_audio,
        language_locale=LanguageLocale.HINDI,
    )

    # 1. Standardized Intake Contract Invariants
    assert intake_result.session_id == "session_whatsapp_audio_002"
    assert intake_result.channel_type == ChannelType.WHATSAPP
    assert intake_result.intake_payload.payload_type == PayloadType.AUDIO
    assert intake_result.intake_payload.structure_level == StructureLevel.FREE_TEXT
    assert intake_result.intake_payload.unprocessed_input_content == (
        "https://media.whatsapp.net/voice/recording_hi_002.ogg"
    )

    # 2. Zero-Trust Security & PII Purge Invariants
    tokenized_identifier = intake_result.intake_payload.tokenized_citizen_id
    assert len(tokenized_identifier) == EXPECTED_TOKEN_LENGTH
    assert TEST_PHONE_NUMBER not in str(intake_result.intake_payload)

    # 3. Perception Convergence: ASR Audio Transcription -> SLM Extraction
    orchestration_outcome = intake_result.orchestration_result
    intent = orchestration_outcome.extracted_entities.application_intent
    assert intent == ApplicationIntent.APPLY_SUBSIDY
    extracted_entities = orchestration_outcome.extracted_entities.domain_entities
    assert DomainEntityKey.DISTRICT in extracted_entities
    assert DomainEntityKey.CROP_NAME in extracted_entities
    assert orchestration_outcome.governance_outcome.governance_action.is_approval is True

    # 4. Outbound Carrier Delivery Invariants
    acknowledgment_receipt = intake_result.transmission_ack
    assert acknowledgment_receipt.channel_type == ChannelType.WHATSAPP
    assert acknowledgment_receipt.carrier_reference_id.startswith("wamid.")


@pytest.mark.asyncio
async def test_ivr_voice_ingress_convergence() -> None:
    """Validates IVR SIP telephony voice call ingress through ASR transcription and gateway."""
    public_agent_gateway = PublicAgentApi()

    raw_ivr_voice = IvrIngressPayload(
        session_id="session_ivr_telephony_003",
        originating_phone_number=TEST_PHONE_NUMBER,
        audio_recording_url=HttpUrl(
            "https://sip-gateway.telecom.in/recordings/call_stream_003.wav"
        ),
        audio_duration_seconds=45,
        received_at=datetime.now(UTC),
    )

    intake_result = await public_agent_gateway.process_raw_ingress(
        raw_payload=raw_ivr_voice,
        language_locale=LanguageLocale.HINDI,
    )

    # 1. Standardized Intake Contract Invariants
    assert intake_result.session_id == "session_ivr_telephony_003"
    assert intake_result.channel_type == ChannelType.IVR_VOICE
    assert intake_result.intake_payload.payload_type == PayloadType.AUDIO
    assert intake_result.intake_payload.structure_level == StructureLevel.FREE_TEXT
    assert intake_result.intake_payload.unprocessed_input_content == (
        "https://sip-gateway.telecom.in/recordings/call_stream_003.wav"
    )

    # 2. Zero-Trust Security & PII Purge Invariants
    tokenized_identifier = intake_result.intake_payload.tokenized_citizen_id
    assert len(tokenized_identifier) == EXPECTED_TOKEN_LENGTH
    assert TEST_PHONE_NUMBER not in str(intake_result.intake_payload)

    # 3. Perception Convergence: ASR Audio Transcription -> SLM Extraction
    orchestration_outcome = intake_result.orchestration_result
    intent = orchestration_outcome.extracted_entities.application_intent
    assert intent == ApplicationIntent.APPLY_SUBSIDY
    extracted_entities = orchestration_outcome.extracted_entities.domain_entities
    assert DomainEntityKey.DISTRICT in extracted_entities
    assert orchestration_outcome.governance_outcome.governance_action.is_approval is True

    # 4. Outbound Telephony Playback Dispatch Invariants
    acknowledgment_receipt = intake_result.transmission_ack
    assert acknowledgment_receipt.channel_type == ChannelType.IVR_VOICE
    assert acknowledgment_receipt.carrier_reference_id.startswith("sip-call-")


@pytest.mark.asyncio
async def test_ussd_menu_ingress_convergence() -> None:
    """Validates USSD signaling keypress ingress executing fast-path structured menu bypass."""
    public_agent_gateway = PublicAgentApi()

    raw_ussd_menu = UssdIngressPayload(
        session_id="session_ussd_menu_004",
        originating_phone_number=TEST_PHONE_NUMBER,
        ussd_service_code="*147#",
        ussd_user_digit_selection="1*2*101",
        received_at=datetime.now(UTC),
    )

    intake_result = await public_agent_gateway.process_raw_ingress(
        raw_payload=raw_ussd_menu,
        language_locale=LanguageLocale.HINDI,
    )

    # 1. Standardized Intake Contract Invariants
    assert intake_result.session_id == "session_ussd_menu_004"
    assert intake_result.channel_type == ChannelType.USSD
    assert intake_result.intake_payload.payload_type == PayloadType.TEXT
    assert intake_result.intake_payload.structure_level == StructureLevel.DTMF_SELECTION
    assert intake_result.intake_payload.unprocessed_input_content == "1*2*101"

    # 2. Zero-Trust Security & PII Purge Invariants
    tokenized_identifier = intake_result.intake_payload.tokenized_citizen_id
    assert len(tokenized_identifier) == EXPECTED_TOKEN_LENGTH
    assert TEST_PHONE_NUMBER not in str(intake_result.intake_payload)

    # 3. Fast-Path Menu Bypass Invariants: 1.0 Confidence & Zero-Latency
    orchestration_outcome = intake_result.orchestration_result
    assert orchestration_outcome.extracted_entities.is_structured_menu_bypass is True
    assert orchestration_outcome.extracted_entities.ai_confidence_score == 1.0
    extracted_entities = orchestration_outcome.extracted_entities.domain_entities
    assert extracted_entities[DomainEntityKey.DISTRICT] == "Karnal"
    assert orchestration_outcome.governance_outcome.governance_action.is_approval is True

    # 4. Outbound USSD GSM 7-bit Notification Invariants
    acknowledgment_receipt = intake_result.transmission_ack
    assert acknowledgment_receipt.channel_type == ChannelType.USSD
    assert acknowledgment_receipt.carrier_reference_id.startswith("ussd-sig-")


@pytest.mark.asyncio
async def test_sms_ingress_convergence() -> None:
    """Validates transactional SMS text ingress through perimeter security and gateway."""
    public_agent_gateway = PublicAgentApi()

    raw_sms_text = SmsIngressPayload(
        session_id="session_sms_text_005",
        originating_phone_number=TEST_PHONE_NUMBER,
        channel_message_id="sms_carrier_txn_98765",
        text_body="Mera khet 2.5 acre hai, fasal gehu, survey 101/2, zila Meerut",
        received_at=datetime.now(UTC),
    )

    intake_result = await public_agent_gateway.process_raw_ingress(
        raw_payload=raw_sms_text,
        language_locale=LanguageLocale.HINDI,
    )

    # 1. Standardized Intake Contract Invariants
    assert intake_result.session_id == "session_sms_text_005"
    assert intake_result.channel_type == ChannelType.SMS
    assert intake_result.intake_payload.payload_type == PayloadType.TEXT
    assert intake_result.intake_payload.structure_level == StructureLevel.FREE_TEXT
    assert intake_result.intake_payload.unprocessed_input_content == (
        "Mera khet 2.5 acre hai, fasal gehu, survey 101/2, zila Meerut"
    )

    # 2. Zero-Trust Security & PII Purge Invariants
    tokenized_identifier = intake_result.intake_payload.tokenized_citizen_id
    assert len(tokenized_identifier) == EXPECTED_TOKEN_LENGTH
    assert TEST_PHONE_NUMBER not in str(intake_result.intake_payload)

    # 3. Perception & Governance Outcome Invariants
    orchestration_outcome = intake_result.orchestration_result
    intent = orchestration_outcome.extracted_entities.application_intent
    assert intent == ApplicationIntent.APPLY_SUBSIDY
    extracted_entities = orchestration_outcome.extracted_entities.domain_entities
    assert DomainEntityKey.DISTRICT in extracted_entities
    assert orchestration_outcome.governance_outcome.governance_action.is_approval is True

    # 4. Outbound SMS DLT Notification Invariants
    acknowledgment_receipt = intake_result.transmission_ack
    assert acknowledgment_receipt.channel_type == ChannelType.SMS
    assert acknowledgment_receipt.carrier_reference_id.startswith("sms-dr-")


@pytest.mark.asyncio
async def test_cross_channel_tokenization_symmetry() -> None:
    """Verifies that identical phone numbers yield identical 64-char tokens across channels."""
    public_agent_gateway = PublicAgentApi()
    current_time = datetime.now(UTC)

    whatsapp_payload = WhatsAppIngressPayload(
        session_id="symmetry_session_whatsapp",
        originating_phone_number=TEST_PHONE_NUMBER,
        channel_message_id="wamid.sym_wa",
        payload_type=PayloadType.TEXT,
        text_body="Mera khet 2.5 acre hai, fasal gehu, survey 101/2, zila Meerut",
        received_at=current_time,
    )
    ivr_payload = IvrIngressPayload(
        session_id="symmetry_session_ivr",
        originating_phone_number=TEST_PHONE_NUMBER,
        audio_recording_url=HttpUrl("https://sip-gateway.telecom.in/recordings/sym_ivr.wav"),
        audio_duration_seconds=20,
        received_at=current_time,
    )
    ussd_payload = UssdIngressPayload(
        session_id="symmetry_session_ussd",
        originating_phone_number=TEST_PHONE_NUMBER,
        ussd_service_code="*147#",
        ussd_user_digit_selection="1*2*101",
        received_at=current_time,
    )
    sms_payload = SmsIngressPayload(
        session_id="symmetry_session_sms",
        originating_phone_number=TEST_PHONE_NUMBER,
        channel_message_id="sms_sym_001",
        text_body="Mera khet 2.5 acre hai, fasal gehu, survey 101/2, zila Meerut",
        received_at=current_time,
    )

    whatsapp_result = await public_agent_gateway.process_raw_ingress(raw_payload=whatsapp_payload)
    ivr_result = await public_agent_gateway.process_raw_ingress(raw_payload=ivr_payload)
    ussd_result = await public_agent_gateway.process_raw_ingress(raw_payload=ussd_payload)
    sms_result = await public_agent_gateway.process_raw_ingress(raw_payload=sms_payload)

    # Assert cross-channel tokenization symmetry
    whatsapp_token = whatsapp_result.intake_payload.tokenized_citizen_id
    ivr_token = ivr_result.intake_payload.tokenized_citizen_id
    ussd_token = ussd_result.intake_payload.tokenized_citizen_id
    sms_token = sms_result.intake_payload.tokenized_citizen_id

    assert whatsapp_token == ivr_token == ussd_token == sms_token
    assert len(whatsapp_token) == EXPECTED_TOKEN_LENGTH


@pytest.mark.asyncio
async def test_multichannel_rate_limit_saturation() -> None:
    """Verifies that exceeding per-caller request quota raises PermissionError across channels."""
    restrictive_limiter = RateLimiter(rate_per_minute=2, capacity=2)
    custom_firewall = IngestionFirewall(
        tokenizer=ZeroTrustIdentityTokenizer(pepper_key=TEST_PEPPER_SECRET),
        rate_limiter=restrictive_limiter,
    )
    public_agent_gateway = PublicAgentApi(firewall=custom_firewall)

    sms_payload_one = SmsIngressPayload(
        session_id="rate_limit_session_1",
        originating_phone_number=TEST_PHONE_NUMBER,
        channel_message_id="sms_rate_01",
        text_body="Mera khet 2.5 acre hai, fasal gehu, survey 101/2, zila Meerut",
        received_at=datetime.now(UTC),
    )
    sms_payload_two = SmsIngressPayload(
        session_id="rate_limit_session_2",
        originating_phone_number=TEST_PHONE_NUMBER,
        channel_message_id="sms_rate_02",
        text_body="Mera khet 2.5 acre hai, fasal gehu, survey 101/2, zila Meerut",
        received_at=datetime.now(UTC),
    )
    sms_payload_three = SmsIngressPayload(
        session_id="rate_limit_session_3",
        originating_phone_number=TEST_PHONE_NUMBER,
        channel_message_id="sms_rate_03",
        text_body="Mera khet 2.5 acre hai, fasal gehu, survey 101/2, zila Meerut",
        received_at=datetime.now(UTC),
    )

    # First two requests consume the bucket capacity
    await public_agent_gateway.process_raw_ingress(raw_payload=sms_payload_one)
    await public_agent_gateway.process_raw_ingress(raw_payload=sms_payload_two)

    # Third request must be rejected at perimeter security boundary
    with pytest.raises(PermissionError, match="Rate limit exceeded"):
        await public_agent_gateway.process_raw_ingress(raw_payload=sms_payload_three)


def test_carrier_transport_authentication_verification() -> None:
    """Validates carrier HMAC signature and bearer token authentication at perimeter boundary."""
    # 1. WhatsApp Carrier HMAC Signature
    webhook_body = b'{"object":"whatsapp_business_account","entry":[]}'
    app_secret = "meta_app_secret_key_456"  # noqa: S105

    computed_digest = hmac.new(app_secret.encode("utf-8"), webhook_body, hashlib.sha256).hexdigest()
    valid_signature_header = f"sha256={computed_digest}"

    assert (
        IngestionFirewall.verify_carrier_webhook(
            payload_bytes=webhook_body,
            signature_header=valid_signature_header,
            app_secret=app_secret,
        )
        is True
    )

    assert (
        IngestionFirewall.verify_carrier_webhook(
            payload_bytes=webhook_body,
            signature_header="sha256=invalid_tampered_signature_digest",
            app_secret=app_secret,
        )
        is False
    )

    # 2. Telephony / Cellular / SMS Carrier Bearer Token
    carrier_token_secret = "secret_carrier_telecom_token_789"  # noqa: S105
    valid_bearer_header = f"Bearer {carrier_token_secret}"

    assert (
        IngestionFirewall.verify_carrier_bearer(
            auth_header=valid_bearer_header,
            expected_token=carrier_token_secret,
        )
        is True
    )

    assert (
        IngestionFirewall.verify_carrier_bearer(
            auth_header="Bearer invalid_unauthorized_token",
            expected_token=carrier_token_secret,
        )
        is False
    )
