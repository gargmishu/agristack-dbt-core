import pytest
from pydantic import ValidationError

from src.data_models.common.base import StrictBaseModel
from src.data_models.common.field_types import (
    HmacCitizenToken,
    PhoneNumberE164,
    SessionId,
    UnprocessedInputContent,
)


class DummyValidatorModel(StrictBaseModel):
    session_id: SessionId
    phone: PhoneNumberE164
    hmac_token: HmacCitizenToken
    input_content: UnprocessedInputContent = "default content"


def test_validators_valid() -> None:
    model = DummyValidatorModel(
        session_id="sess_12345678",
        phone="+919876543210",
        hmac_token="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",  # noqa: S106
        input_content="Gehu subsidy registration",
    )
    assert model.session_id == "sess_12345678"
    assert model.input_content == "Gehu subsidy registration"


def test_validators_invalid_phone() -> None:
    with pytest.raises(ValidationError):
        DummyValidatorModel(
            session_id="sess_12345678",
            phone="9876543210",  # Invalid phone format
            hmac_token="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",  # noqa: S106
        )


def test_validators_invalid_unprocessed_input_content_length() -> None:
    with pytest.raises(ValidationError):
        DummyValidatorModel(
            session_id="sess_12345678",
            phone="+919876543210",
            hmac_token="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",  # noqa: S106
            input_content="x" * 5001,  # Exceeds max_length=5000
        )
