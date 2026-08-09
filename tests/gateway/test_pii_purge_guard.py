"""Unit tests for Layer 2 PII Purge Guard Sentinel."""

from datetime import UTC, datetime

import pytest

from src.data_models.common import ChannelType, PayloadType, StructureLevel
from src.data_models.public_agent import PublicAgentStandardizedIntakePayload
from src.gateway.pii_purge_guard import PiiPurgeGuard


def test_pii_purge_guard_detects_cleartext_phone() -> None:
    assert PiiPurgeGuard.contains_cleartext_phone("+919876543210") is True
    assert PiiPurgeGuard.contains_cleartext_phone("9876543210") is True
    assert (
        PiiPurgeGuard.contains_cleartext_phone(
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        is False
    )
    assert PiiPurgeGuard.contains_cleartext_phone("") is False
    assert PiiPurgeGuard.contains_cleartext_phone("   ") is False


def test_pii_purge_guard_detects_cleartext_aadhaar() -> None:
    assert PiiPurgeGuard.contains_cleartext_aadhaar("1234 5678 9012") is True
    assert PiiPurgeGuard.contains_cleartext_aadhaar("123456789012") is True
    assert PiiPurgeGuard.contains_cleartext_aadhaar("Survey number 1002") is False
    assert PiiPurgeGuard.contains_cleartext_aadhaar("") is False
    assert PiiPurgeGuard.contains_cleartext_aadhaar("   ") is False


def test_pii_purge_guard_asserts_valid_payload() -> None:
    valid_payload = PublicAgentStandardizedIntakePayload(
        session_id="session-12345678",
        tokenized_citizen_id="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale="hi-IN",
        unprocessed_input_content="Gehu subsidy claim",
        received_at=datetime.now(UTC),
    )
    # Should not raise
    PiiPurgeGuard.assert_zero_pii(valid_payload)


def test_pii_purge_guard_rejects_invalid_token_length() -> None:
    valid_payload = PublicAgentStandardizedIntakePayload(
        session_id="session-12345678",
        tokenized_citizen_id="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale="hi-IN",
        unprocessed_input_content="Gehu subsidy claim",
        received_at=datetime.now(UTC),
    )
    object.__setattr__(valid_payload, "tokenized_citizen_id", "short_token_12345")
    with pytest.raises(ValueError, match="must be a 64-character SHA-256 HMAC token"):
        PiiPurgeGuard.assert_zero_pii(valid_payload)


def test_pii_purge_guard_rejects_raw_phone_in_token_field() -> None:
    # A 64-char string starting with raw phone number (all hex digits)
    raw_phone_padded = "919876543210" + "a" * 52
    payload = PublicAgentStandardizedIntakePayload(
        session_id="session-12345678",
        tokenized_citizen_id=raw_phone_padded,
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale="hi-IN",
        unprocessed_input_content="Gehu subsidy claim",
        received_at=datetime.now(UTC),
    )
    with pytest.raises(ValueError, match="Cleartext phone number detected"):
        PiiPurgeGuard.assert_zero_pii(payload)


def test_pii_purge_guard_rejects_raw_aadhaar_in_token_field() -> None:
    # A 64-char string starting with raw Aadhaar number (all valid hex digits)
    raw_aadhaar_padded = "123456789012" + "a" * 52
    payload = PublicAgentStandardizedIntakePayload(
        session_id="session-12345678",
        tokenized_citizen_id=raw_aadhaar_padded,
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale="hi-IN",
        unprocessed_input_content="Gehu subsidy claim",
        received_at=datetime.now(UTC),
    )
    with pytest.raises(ValueError, match="Cleartext Aadhaar number detected"):
        PiiPurgeGuard.assert_zero_pii(payload)


def test_pii_purge_guard_rejects_raw_pii_in_unprocessed_input_content() -> None:
    valid_token = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"  # noqa: S105

    phone_leaked_payload = PublicAgentStandardizedIntakePayload(
        session_id="session-12345678",
        tokenized_citizen_id=valid_token,
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale="hi-IN",
        unprocessed_input_content="Mera phone number 9876543210 par call karo",
        received_at=datetime.now(UTC),
    )
    with pytest.raises(
        ValueError,
        match="Cleartext phone number detected in unprocessed_input_content",
    ):
        PiiPurgeGuard.assert_zero_pii(phone_leaked_payload)

    aadhaar_leaked_payload = PublicAgentStandardizedIntakePayload(
        session_id="session-12345678",
        tokenized_citizen_id=valid_token,
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale="hi-IN",
        unprocessed_input_content="Aadhaar number 1234 5678 9012 linked hai",
        received_at=datetime.now(UTC),
    )
    with pytest.raises(
        ValueError,
        match="Cleartext Aadhaar number detected in unprocessed_input_content",
    ):
        PiiPurgeGuard.assert_zero_pii(aadhaar_leaked_payload)
