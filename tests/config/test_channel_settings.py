"""Unit tests for centralized channel configuration module."""

import pytest

from src.config import (
    DEFAULT_HELPLINE_TOLL_FREE,
    DEFAULT_IVR_INTERFACE,
    DEFAULT_SIGTRAN_INTERFACE,
    DEFAULT_SIP_TRUNK_INTERFACE,
    DEFAULT_SMS_GATEWAY,
    DEFAULT_SMS_INTERFACE,
    DEFAULT_USSD_INTERFACE,
    DEFAULT_WHATSAPP_INTERFACE,
    get_helpline_number,
    get_ivr_interface_id,
    get_sigtran_interface_id,
    get_sip_trunk_interface_id,
    get_sms_gateway_id,
    get_sms_interface_id,
    get_ussd_interface_id,
    get_whatsapp_interface_id,
)


def test_channel_settings_defaults() -> None:
    assert get_whatsapp_interface_id() == DEFAULT_WHATSAPP_INTERFACE
    assert get_ivr_interface_id() == DEFAULT_IVR_INTERFACE
    assert get_ussd_interface_id() == DEFAULT_USSD_INTERFACE
    assert get_sms_interface_id() == DEFAULT_SMS_INTERFACE
    assert get_helpline_number() == DEFAULT_HELPLINE_TOLL_FREE

    # Backwards compatibility assertions
    assert get_sip_trunk_interface_id() == DEFAULT_SIP_TRUNK_INTERFACE
    assert get_sigtran_interface_id() == DEFAULT_SIGTRAN_INTERFACE
    assert get_sms_gateway_id() == DEFAULT_SMS_GATEWAY


def test_channel_settings_environment_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("WHATSAPP_INTERFACE_ID", "CUSTOM_WHATSAPP_GW")
    monkeypatch.setenv("IVR_INTERFACE_ID", "CUSTOM_IVR_GW")
    monkeypatch.setenv("USSD_INTERFACE_ID", "CUSTOM_USSD_GW")
    monkeypatch.setenv("SMS_INTERFACE_ID", "CUSTOM_SMS_GW")
    monkeypatch.setenv("HELPLINE_TOLL_FREE_NUMBER", "1800-000-0000")

    assert get_whatsapp_interface_id() == "CUSTOM_WHATSAPP_GW"
    assert get_ivr_interface_id() == "CUSTOM_IVR_GW"
    assert get_ussd_interface_id() == "CUSTOM_USSD_GW"
    assert get_sms_interface_id() == "CUSTOM_SMS_GW"
    assert get_helpline_number() == "1800-000-0000"


def test_channel_settings_legacy_env_fallbacks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("IVR_INTERFACE_ID", raising=False)
    monkeypatch.delenv("USSD_INTERFACE_ID", raising=False)
    monkeypatch.delenv("SMS_INTERFACE_ID", raising=False)

    monkeypatch.setenv("IVR_SIP_TRUNK_INTERFACE_ID", "LEGACY_IVR_GW")
    monkeypatch.setenv("USSD_SIGTRAN_INTERFACE_ID", "LEGACY_USSD_GW")
    monkeypatch.setenv("SMS_GATEWAY_INTERFACE_ID", "LEGACY_SMS_GW")

    assert get_ivr_interface_id() == "LEGACY_IVR_GW"
    assert get_ussd_interface_id() == "LEGACY_USSD_GW"
    assert get_sms_interface_id() == "LEGACY_SMS_GW"
