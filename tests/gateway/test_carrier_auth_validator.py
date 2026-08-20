import hmac
from hashlib import sha256

from src.gateway import CarrierAuthValidator


def test_hmac_signature_valid() -> None:
    app_secret = "meta_app_secret_12345"  # noqa: S105
    payload_bytes = b'{"object": "whatsapp_business_account", "entry": []}'
    computed_sig = hmac.new(app_secret.encode("utf-8"), payload_bytes, sha256).hexdigest()
    header_val = f"sha256={computed_sig}"

    assert (
        CarrierAuthValidator.validate_hmac_signature(payload_bytes, header_val, app_secret) is True
    )


def test_hmac_signature_invalid_and_missing() -> None:
    app_secret = "meta_app_secret_12345"  # noqa: S105
    payload_bytes = b'{"object": "whatsapp_business_account", "entry": []}'

    assert (
        CarrierAuthValidator.validate_hmac_signature(
            payload_bytes, "sha256=invalid_sig", app_secret
        )
        is False
    )
    assert CarrierAuthValidator.validate_hmac_signature(payload_bytes, None, app_secret) is False
    assert (
        CarrierAuthValidator.validate_hmac_signature(payload_bytes, "invalid_prefix", app_secret)
        is False
    )


def test_carrier_bearer_token_valid() -> None:
    bearer_key = "secret_carrier_token_9988"  # noqa: S105
    auth_header = f"Bearer {bearer_key}"

    assert CarrierAuthValidator.validate_carrier_bearer_token(auth_header, bearer_key) is True


def test_carrier_bearer_token_invalid_and_missing() -> None:
    bearer_key = "secret_carrier_token_9988"  # noqa: S105
    assert (
        CarrierAuthValidator.validate_carrier_bearer_token("Bearer wrong_token", bearer_key)
        is False
    )
    assert CarrierAuthValidator.validate_carrier_bearer_token(None, bearer_key) is False
    assert CarrierAuthValidator.validate_carrier_bearer_token("Basic 12345", bearer_key) is False
