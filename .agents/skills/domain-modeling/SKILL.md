---
name: domain-modeling
description: Pydantic v2 domain modeling standards, StrictBaseModel configuration, type promotion rules (field_types.py vs inline), Contract Truth Tables, and model validator guidelines. Use whenever designing, refactoring, or writing Pydantic schemas, validators, or data contracts.
---

# Pydantic v2 Domain Modeling & Schema Standards

This document establishes the canonical standards for domain schemas, type annotations, and model validation across all layers of the platform.

---

## 1. Base Model Configuration (`StrictBaseModel`)

All domain schemas across all layers must inherit from `StrictBaseModel` (`src/data_models/common/base.py`), which enforces immutability and strict payload validation:

```python
class StrictBaseModel(BaseModel):
    """Base model for all inter-layer payloads."""

    model_config = ConfigDict(
        extra="forbid",             # Rejects unexpected / injected keys
        frozen=True,                # Guarantees immutability post-instantiation
        validate_assignment=True,   # Validates assignments if unfrozen
        str_strip_whitespace=True,  # Auto-strips leading/trailing whitespace
        use_enum_values=True,       # Coerces enum values for clean serialization
    )
```

---

## 2. "Shift-Left" Contract Truth Table Methodology

Before writing model code or validators, define an explicit **Contract Truth Table**:

1. **Field Name & Type**: Use constrained type aliases (`SessionId`, `CropSeason`).
2. **Cardinality & Nullability**: Required, Optional, or Strictly Forbidden (`None`) per lifecycle state.
3. **Non-Empty / Non-Whitespace Guard**: String fields representing identifiers, reasons, notes, or input content MUST reject empty strings or whitespace (`.strip()`).
4. **Foreign Key Survival**: Upstream audit tracking keys (`session_id`, `payload_id`, `escalation_case_id`) must survive across layer transitions.

---

## 3. Centralized Types (`field_types.py`) vs. Inline Model Fields

### 3.1 When to Promote to `field_types.py` (Centralized Type Aliases)
Promote a field to `src/data_models/common/field_types.py` as an `Annotated[T, Field(...)]` type alias when:
* **Cross-Cutting Identifiers**: The field crosses **2 or more architecture layers, channels, or lifecycle states** (e.g. `SessionId`, `PhoneNumberE164`, `EscalationCaseId`, `DisbursementTxnId`, `CropSeason`, `ExtractionPayloadId`, `UnprocessedInputContent`).
* **System-Wide Compliance Invariants**: The field enforces non-negotiable platform-level constraints:
  * Zero-Trust anonymity (`HmacCitizenToken`: exact 64-character SHA-256 hex digest).
  * Clock-skew freshness (`UtcTimestamp`: 5-second maximum future skew check via `AfterValidator`).
  * Resource protection ceilings (`AudioDurationSeconds`: bounded $[1, 600]$ seconds).
  * Confidence scoring bounds (`AiConfidenceScore`: bounded $[0.0, 1.0]$).

### 3.2 When to Keep Field Definitions Inline in Domain Models
Keep field constraints inline within specific domain models when:
* **Protocol / Channel-Specific Framing**: The field belongs strictly to a single transport adapter or carrier protocol (e.g. `channel_message_id` for WhatsApp `wamid`; `ussd_service_code` for GSM SS7 `*147#` shortcodes).
* **Stage-Specific Metadata**: The attribute exists only at a single adjudication step (e.g. `reviewer_id` in caseworker review; `bank_reference_id` in bank callback).
* **Context-Varying Free Text**: Length bounds depend on the specific business role (e.g. `text_body` $\le 1000$ chars, `review_notes` $5 \le \text{len} \le 2000$).

### 3.3 Pydantic v2 Metadata Inheritance (Clean Declarations)
* **Rely on Centralized Metadata**: When a model field uses a type alias from `field_types.py`, declare it cleanly as `field_name: FieldType` without redundant `Field(...)` wrapping:
  ```python
  # CORRECT: Relies on centralized bounds and descriptions in field_types.py
  session_id: SessionId
  tokenized_citizen_id: HmacCitizenToken
  active_season: CropSeason = "KHARIF-2026"

  # INCORRECT: Redundant duplicate description / empty Field wrapping
  tokenized_citizen_id: HmacCitizenToken = Field(
      ..., description="Zero-PII SHA-256 HMAC citizen identity token"
  )
  ```
* **Contextual Override Only**: Use `Field(..., description="...")` on a typed field *only* when providing domain-specific documentation that intentionally overrides the generic base description in generated OpenAPI schemas.

---

## 4. Focused Single-Responsibility Validators

* Split validation logic into separate `@model_validator(mode="after")` methods rather than creating monolithic validator functions.
* Keep branch count under 12 per validator method to eliminate `# noqa: PLR0912` suppressions.

```python
# GOOD: Focused single-responsibility validators
@model_validator(mode="after")
def validate_non_empty_content(self) -> "PublicAgentStandardizedIntakePayload":
    if not self.unprocessed_input_content or not self.unprocessed_input_content.strip():
        raise ValueError("unprocessed_input_content cannot be empty or whitespace-only")
    return self

@model_validator(mode="after")
def validate_channel_structure_matrix(self) -> "PublicAgentStandardizedIntakePayload":
    # Validate channel_type vs structure_level compatibility matrix
    return self
```
