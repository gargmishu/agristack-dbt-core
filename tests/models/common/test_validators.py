import pytest
from pydantic import ValidationError

from src.models.common.base import StrictBaseModel
from src.models.common.validators import (
    ChannelSessionId,
    HmacCitizenToken,
    PhoneNumberE164,
)


class DummyValidatorModel(StrictBaseModel):
    session_id: ChannelSessionId
    phone: PhoneNumberE164
    hmac_token: HmacCitizenToken


def test_validators_valid() -> None:
    model = DummyValidatorModel(
        session_id="sess_12345678",
        phone="+919876543210",
        hmac_token="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",  # noqa: S106
    )
    assert model.session_id == "sess_12345678"


def test_validators_invalid_phone() -> None:
    with pytest.raises(ValidationError):
        DummyValidatorModel(
            session_id="sess_12345678",
            phone="9876543210",  # Invalid phone format
            hmac_token="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",  # noqa: S106
        )
