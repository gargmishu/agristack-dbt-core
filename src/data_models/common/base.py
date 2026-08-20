"""Shared base Pydantic model configuration across all layers."""

from pydantic import BaseModel, ConfigDict


class StrictBaseModel(BaseModel):
    """Foundational immutable base model for all AgriStack domain contracts and payloads.

    Enforces strict typing, immutability, extra-field rejection, and whitespace sanitization
    across all inter-layer communication boundaries (Layer 1 -> Layer 2 -> Layer 3 -> Layer
    4).

    Core Configuration & Security Guarantees:
    - `extra="forbid"`: Rejects payload pollution, prototype tampering, and unexpected
      injected
      keys.
    - `frozen=True`: Guarantees thread-safe immutability across async processing pipelines.
    - `validate_assignment=True`: Ensures runtime validation rules are executed if models
      are
      unfrozen.
    - `str_strip_whitespace=True`: Automatically strips leading and trailing whitespace from
      string fields.
    - `use_enum_values=False`: Preserves native enum instances during processing for direct
      member comparisons.

    See: decisions/step2.0_canonical_domain_schemas.md#31-base-configuration-strictbasemodel
    See: decisions/step1.2_runtime_strictness_linting.md
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_assignment=True,
        str_strip_whitespace=True,
        use_enum_values=False,
    )
