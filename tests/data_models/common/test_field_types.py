import pytest
from pydantic import Field, ValidationError

from src.data_models.common.base import StrictBaseModel
from src.data_models.common.enums import DomainEntityKey
from src.data_models.common.field_types import (
    DomainEntities,
    HmacCitizenToken,
    PhoneNumberE164,
    SessionId,
    UnprocessedInputContent,
)


class DummyValidatorModel(StrictBaseModel):
    """Test model used to verify common field types and custom validators."""

    session_id: SessionId
    phone: PhoneNumberE164
    hmac_token: HmacCitizenToken
    input_content: UnprocessedInputContent = "default content"
    entities: DomainEntities = Field(default_factory=dict)


def test_validators_valid() -> None:
    expected_acres = 2.5
    expected_survey_num = 102
    model = DummyValidatorModel(
        session_id="sess_12345678",
        phone="+919876543210",
        hmac_token="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",  # noqa: S106
        input_content="Gehu subsidy registration",
        entities={
            DomainEntityKey.DISTRICT: "Pune",
            DomainEntityKey.LAND_SIZE_ACRES: expected_acres,
            DomainEntityKey.SURVEY_NUMBER: expected_survey_num,
        },
    )
    assert model.session_id == "sess_12345678"
    assert model.input_content == "Gehu subsidy registration"
    assert model.entities[DomainEntityKey.DISTRICT] == "Pune"
    assert model.entities[DomainEntityKey.LAND_SIZE_ACRES] == expected_acres
    assert model.entities[DomainEntityKey.SURVEY_NUMBER] == expected_survey_num


def test_domain_entities_default_empty() -> None:
    model = DummyValidatorModel(
        session_id="sess_12345678",
        phone="+919876543210",
        hmac_token="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",  # noqa: S106
    )
    assert model.entities == {}


def test_domain_entities_invalid_key_rejected() -> None:
    with pytest.raises(ValidationError):
        DummyValidatorModel(
            session_id="sess_12345678",
            phone="+919876543210",
            hmac_token="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",  # noqa: S106
            entities={"invalid_key": "some_value"},  # type: ignore[dict-item]
        )


def test_domain_entities_invalid_nested_value_rejected() -> None:
    with pytest.raises(ValidationError):
        DummyValidatorModel(
            session_id="sess_12345678",
            phone="+919876543210",
            hmac_token="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",  # noqa: S106
            entities={DomainEntityKey.DISTRICT: {"nested": "dict"}},  # type: ignore[dict-item]
        )


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
