"""Unit tests for centralized channel configuration module."""

import pytest

from src.config import (
    DEFAULT_HELPLINE_NUMBER,
    DEFAULT_IVR_INTERFACE,
    DEFAULT_SMS_INTERFACE,
    DEFAULT_USSD_INTERFACE,
    DEFAULT_WHATSAPP_INTERFACE,
    get_helpline_number,
    get_ivr_interface_id,
    get_rate_limit_capacity,
    get_rate_per_minute,
    get_sms_interface_id,
    get_ussd_interface_id,
    get_whatsapp_interface_id,
)


def test_channel_settings_defaults() -> None:
    assert get_whatsapp_interface_id() == DEFAULT_WHATSAPP_INTERFACE
    assert get_ivr_interface_id() == DEFAULT_IVR_INTERFACE
    assert get_ussd_interface_id() == DEFAULT_USSD_INTERFACE
    assert get_sms_interface_id() == DEFAULT_SMS_INTERFACE
    assert get_helpline_number() == DEFAULT_HELPLINE_NUMBER


def test_channel_settings_environment_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WHATSAPP_INTERFACE_ID", "CUSTOM_WHATSAPP_GW")
    monkeypatch.setenv("IVR_INTERFACE_ID", "CUSTOM_IVR_GW")
    monkeypatch.setenv("USSD_INTERFACE_ID", "CUSTOM_USSD_GW")
    monkeypatch.setenv("SMS_INTERFACE_ID", "CUSTOM_SMS_GW")
    monkeypatch.setenv("HELPLINE_NUMBER", "1800-000-0000")

    assert get_whatsapp_interface_id() == "CUSTOM_WHATSAPP_GW"
    assert get_ivr_interface_id() == "CUSTOM_IVR_GW"
    assert get_ussd_interface_id() == "CUSTOM_USSD_GW"
    assert get_sms_interface_id() == "CUSTOM_SMS_GW"
    assert get_helpline_number() == "1800-000-0000"


def test_rate_limit_settings_environment_values(monkeypatch: pytest.MonkeyPatch) -> None:
    expected_rate_per_minute = 120
    expected_rate_limit_capacity = 25
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", str(expected_rate_per_minute))
    monkeypatch.setenv("RATE_LIMIT_CAPACITY", str(expected_rate_limit_capacity))

    assert get_rate_per_minute() == expected_rate_per_minute
    assert get_rate_limit_capacity() == expected_rate_limit_capacity
