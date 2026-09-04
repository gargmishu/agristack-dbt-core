"""Unit tests for SmsIngressPayload data model."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from src.data_models.raw_ingress import SmsIngressPayload


def test_sms_ingress_valid() -> None:
    payload = SmsIngressPayload(
        session_id="sms_sess_998877",
        originating_phone_number="+919876543210",
        channel_message_id="sms_msg_12345",
        text_body="STATUS PM-KISAN 9876543210",
        received_at=datetime.now(UTC),
    )
    assert payload.session_id == "sms_sess_998877"
    assert payload.originating_phone_number == "+919876543210"
    assert payload.channel_message_id == "sms_msg_12345"
    assert payload.text_body == "STATUS PM-KISAN 9876543210"


def test_sms_ingress_invalid_phone_number() -> None:
    with pytest.raises(ValidationError):
        SmsIngressPayload(
            session_id="sms_sess_998877",
            originating_phone_number="9876543210",  # Missing leading +
            channel_message_id="sms_msg_12345",
            text_body="STATUS",
            received_at=datetime.now(UTC),
        )


def test_sms_ingress_empty_whitespace_text_body() -> None:
    with pytest.raises(ValidationError):
        SmsIngressPayload(
            session_id="sms_sess_998877",
            originating_phone_number="+919876543210",
            channel_message_id="sms_msg_12345",
            text_body="   ",
            received_at=datetime.now(UTC),
        )


def test_sms_ingress_future_timestamp_clock_skew() -> None:
    future_dt = datetime.now(UTC) + timedelta(seconds=10)
    with pytest.raises(ValidationError) as exception_info:
        SmsIngressPayload(
            session_id="sms_sess_998877",
            originating_phone_number="+919876543210",
            channel_message_id="sms_msg_12345",
            text_body="STATUS",
            received_at=future_dt,
        )
    assert "clock-skew violation" in str(exception_info.value)
