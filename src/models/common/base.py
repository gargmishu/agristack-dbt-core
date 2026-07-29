from pydantic import BaseModel, ConfigDict


class StrictBaseModel(BaseModel):
    """Base model for all inter-layer payloads.

    See: decisions/step2.0_canonical_domain_schemas.md#31-base-configuration-strictbasemodel
    See: decisions/step1.2_runtime_strictness_linting.md

    - extra="forbid": Rejects payload pollution / unexpected injected keys.
    - frozen=True: Guarantees immutability as data moves between layers.
    - validate_assignment=True: Validates mutations if model is unfrozen.
    - str_strip_whitespace=True: Auto-strips leading/trailing whitespace.
    - use_enum_values=True: Coerces enum values for clean serialization.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_assignment=True,
        str_strip_whitespace=True,
        use_enum_values=True,
    )
