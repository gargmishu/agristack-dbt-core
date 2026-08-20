import pytest
from pydantic import ValidationError

from src.data_models.common.base import StrictBaseModel


class SampleModel(StrictBaseModel):
    """Test model used to verify StrictBaseModel whitespace stripping and immutability."""

    name: str
    age: int


def test_strict_base_model_valid() -> None:
    model = SampleModel(name="  Farmer  ", age=40)
    assert model.name == "Farmer"  # Stripped whitespace
    assert model.age == 40  # noqa: PLR2004


def test_strict_base_model_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        SampleModel(name="Farmer", age=40, extra_field="forbidden")  # type: ignore[call-arg]
