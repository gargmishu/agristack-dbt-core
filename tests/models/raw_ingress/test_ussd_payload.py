from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from src.models.raw_ingress import UssdIngressPayload


def test_ussd_ingress_valid() -> None:
    payload = UssdIngressPayload(
        session_id="ussd_sess_998877",
        originating_phone_number="+919876543210",
        ussd_service_code="*147*1*2#",
        ussd_user_digit_selection="1*2*9876543210",
        ingress_timestamp=datetime.now(UTC),
    )
    assert payload.ussd_service_code == "*147*1*2#"


def test_ussd_ingress_invalid_shortcode() -> None:
    with pytest.raises(ValidationError):
        UssdIngressPayload(
            session_id="ussd_sess_998877",
            originating_phone_number="+919876543210",
            ussd_service_code="147#",  # Missing leading *
            ussd_user_digit_selection="1*2",
            ingress_timestamp=datetime.now(UTC),
        )


def test_ussd_ingress_future_timestamp_clock_skew() -> None:
    future_dt = datetime.now(UTC) + timedelta(seconds=10)
    with pytest.raises(ValidationError) as exc:
        UssdIngressPayload(
            session_id="ussd_sess_998877",
            originating_phone_number="+919876543210",
            ussd_service_code="*147#",
            ussd_user_digit_selection="1",
            ingress_timestamp=future_dt,  # >5s in the future
        )
    assert "clock-skew violation" in str(exc.value)
