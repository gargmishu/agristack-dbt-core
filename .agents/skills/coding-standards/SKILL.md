---
name: coding-standards
description: Coding rules, naming conventions, package structure, and modularity guidelines established for AgriStack core development. Use whenever designing, refactoring, or writing Python models, validators, or package structures.
---

# AgriStack Core Coding Standards & Guidelines

This document defines the architectural, structural, and coding standards established for the AgriStack codebase. All new code, refactorings, and schema definitions must strictly adhere to these principles.

---

## 0. "Shift-Left" First-Principles Engineering Methodology (Preventing Errors Right From the Outset)

To prevent logical errors, state inconsistencies, and validation gaps **before writing a single line of implementation code**:

### 0.1 Contract Truth Table Specification (Pre-Implementation Mandate)
Before defining any domain model, validator, or state-machine router, write down an explicit **Contract Truth Table** defining for every single field:
1. **Field Name & Type**: Type alias with domain constraints.
2. **Cardinality & Nullability**: Is it Required, Optional, or Strictly Forbidden (`None`) per state?
3. **Non-Empty / Non-Whitespace Guard**: Does every text/string field explicitly reject empty strings and whitespace (`.strip()`)?
4. **Foreign Key Survival**: Does this field carry an upstream audit ID (`session_id`, `payload_id`, `escalation_case_id`)?

### 0.2 Default Non-Empty Guard Rule for Text Fields
Every string field representing text, reasons, notes, or input content MUST have an explicit non-empty guard (`min_length=1` or `model_validator` checking `.strip()`) unless explicitly declared as `None` or optional.

### 0.3 Exhaustive State-Matrix Pre-Check
Before writing validator methods, map out **100% of Enum states** in a matrix table. Reconcile automated machine paths (where human context `escalation_case_id = None`) against human adjudication paths (where `escalation_case_id` is required).

---

## 1. Naming Conventions

### 1.1 Class & Type Alias Naming (Strict PascalCase / Upper CamelCase)
* **Capitalize Acronyms as Words**: Multi-word acronyms in class names and type aliases must treat acronyms as capitalized words (Upper CamelCase) rather than ALL-CAPS to avoid visual collisions (e.g., `CC` collisions) and maintain readability.
  * **Correct**: `IvrIngressPayload`, `UssdIngressPayload`, `HmacCitizenToken`, `WhatsAppIngressPayload`
  * **Incorrect**: `IVRIngressPayload`, `USSDIngressPayload`, `HMACCitizenToken`, `WhatsappIngressPayload`
* **Align with Standard Libraries & Pydantic**: Matches conventions like `HttpUrl`, `HttpClient`, and `hashlib.pbkdf2_hmac`.

### 1.2 Attribute & Field Naming (`snake_case`)
* All model attributes, function parameters, and variables must strictly use `snake_case`.

### 1.3 Timestamp Attribute Standard (`<action>_at`)
* All timestamp fields across all 4 architecture layers must follow the clean **`<action>_at`** convention. Avoid redundant `_timestamp` suffixes.
  * `received_at`: UTC timestamp when raw carrier ingress or Layer 3 intake payload arrived.
  * `evaluated_at`: UTC timestamp when rules engine evaluation outcome was rendered.
  * `reviewed_at`: UTC timestamp when officer submitted review outcome on dashboard.
  * `staged_at`: UTC timestamp when incident ticket was staged in caseworker queue.
  * `cleared_at`: UTC timestamp when payment rail cleared transaction.

### 1.4 Unified Session Key (`session_id`)
* The primary session key tracking end-to-end communication across all layers must be named **`session_id`** (typed with `SessionId`).
* Avoid layer-specific stutter like `channel_session_id`.

### 1.5 Phone Number Standard (`originating_phone_number`)
* Use `originating_phone_number` consistently across all Layer 1 ingress payloads (e.g., WhatsApp, IVR, USSD).

### 1.6 Module-to-Class Naming Symmetry
* For operational components (gateways, connectors, orchestrator rules, and services), Python module filenames in `snake_case` must strictly match their primary class names in `PascalCase` (e.g., `CarrierAuthValidator` in `carrier_auth_validator.py`, `PaymentRailService` in `payment_rail_service.py`). Do not omit descriptive suffixes like `_validator`, `_tokenizer`, or `_service` from module names.

### 1.7 Domain Schema Namespacing
* Within categorized domain model subpackages (`raw_ingress`, `caseworker`, `disbursement`), file names represent the schema entity (e.g. `review_outcome_payload.py`), while model class names may include the domain namespace prefix (e.g. `CaseworkerReviewOutcomePayload`) to avoid symbol collisions when imported into cross-domain contexts.

---

## 2. Package & Directory Structure

### 2.1 Categorized Domain Subpackages
Organize domain models and services into logical, single-purpose subpackages under `src/`:

```
src/
├── connectors/                      # Layer 1 Channel Edge Connectors
│   ├── whatsapp_connector.py
│   ├── ivr_connector.py
│   └── ussd_connector.py
├── gateway/                         # Layer 2 Gateway & Perimeter Security
│   ├── carrier_auth_validator.py    # Webhook HMAC signature & Bearer token verification
│   ├── zero_trust_identity_tokenizer.py # RAM-only SHA-256 HMAC Zero-PII identity tokenization
│   ├── pii_purge_guard.py           # In-memory Zero-PII assertion sentinel
│   ├── adversarial_prompt_firewall.py # Adversarial prompt injection & override defense
│   ├── payload_canonicalizer.py     # Ingress payload canonicalization (Raw -> StandardizedIntake)
│   ├── rate_limiter.py              # Token bucket rate limiter & quota guard
│   └── ingestion_firewall.py        # Unified Layer 2 perimeter firewall facade
├── public_agent/                    # Layer 3 Public Agent Intake Gateway Surface
│   ├── public_agent_api.py          # Public Agent Gateway API Surface
│   └── intake_payload_evaluator.py  # Structure level & NLU routing evaluator
├── orchestrator/                    # Layer 4 Orchestrator Brain & Governance Engine
│   ├── governance_router.py         # Decision matrix & threshold routing
│   ├── state_machine.py             # Deterministic state transitions & gates
│   └── case_management_service.py   # Layer 4 internal caseworker queue & review service
├── services/                        # External DPI Registries & AI Adapter Services ONLY
│   ├── ai/
│   │   ├── bhashini_service.py
│   │   └── slm_extractor.py
│   └── dpi/
│       ├── agri_registry_service.py
│       ├── identity_verification_service.py
│       ├── payment_rail_service.py
│       └── social_registry_service.py # External OpenSPP registry boundary client
├── data_models/                     # Domain data contracts & Pydantic validation schemas
│   ├── common/                      # Shared foundational primitives & type annotations
│   │   ├── base.py                  # StrictBaseModel definition
│   │   ├── enums.py                 # StrEnum definitions
│   │   └── field_types.py           # Constrained Annotated type aliases & validators
│   ├── raw_ingress/                 # Layer 1 -> Layer 2 carrier raw ingress payloads
│   │   ├── ivr_payload.py
│   │   ├── ussd_payload.py
│   │   └── whatsapp_payload.py
│   ├── public_agent/                # Layer 2 -> Layer 3 normalized intake contracts
│   │   └── standardized_intake_payload.py
│   ├── governance/                  # Layer 4 governance models & extraction payloads
│   │   ├── extracted_entity_payload.py
│   │   └── governance_outcome_payload.py
│   ├── caseworker/                  # Caseworker portal review staging & outcome models
│   │   ├── case_review_payload.py
│   │   └── review_outcome_payload.py
│   └── disbursement/                # Financial clearing callback models
│       └── disbursement_callback_payload.py
```

### 2.2 Strict Test Hierarchy Mirroring
The test suite under `tests/` must mirror `src/` 1:1. Each source module must have a corresponding test file in the matching subdirectory:

```
tests/
├── connectors/
│   ├── test_whatsapp_connector.py
│   ├── test_ivr_connector.py
│   └── test_ussd_connector.py
├── gateway/
│   ├── test_carrier_auth_validator.py
│   ├── test_zero_trust_identity_tokenizer.py
│   ├── test_pii_purge_guard.py
│   ├── test_adversarial_prompt_firewall.py
│   ├── test_payload_canonicalizer.py
│   ├── test_rate_limiter.py
│   └── test_ingestion_firewall.py
├── public_agent/
│   ├── test_public_agent_api.py
│   └── test_intake_payload_evaluator.py
├── orchestrator/
│   ├── test_governance_router.py
│   ├── test_state_machine.py
│   └── test_case_management_service.py
├── services/
│   ├── ai/
│   │   ├── test_bhashini_service.py
│   │   └── test_slm_extractor.py
│   └── dpi/
│       ├── test_agri_registry_service.py
│       ├── test_identity_verification_service.py
│       ├── test_payment_rail_service.py
│       └── test_social_registry_service.py
├── data_models/
│   ├── common/
│   │   ├── test_base.py
│   │   ├── test_enums.py
│   │   └── test_field_types.py
│   ├── raw_ingress/
│   │   ├── test_ivr_payload.py
│   │   ├── test_ussd_payload.py
│   │   └── test_whatsapp_payload.py
│   ├── public_agent/
│   │   └── test_standardized_intake_payload.py
│   ├── governance/
│   │   └── test_governance_outcome_payload.py
│   ├── caseworker/
│   │   ├── test_case_review_payload.py
│   │   └── test_review_outcome_payload.py
│   └── disbursement/
│       └── test_disbursement_callback_payload.py
```

---

## 3. Modular Code, Documentation & Rationale (SRP)

### 3.1 Focused Model Validators
* Split validation logic into separate, single-purpose `@model_validator(mode="after")` methods rather than creating monolithic validator functions.
* **Keep Cyclomatic Complexity Low**: Each validator method should validate one concern (e.g. non-empty check, matrix compatibility, format validation). Keep branch count under 12 to eliminate `# noqa: PLR0912` suppressions.

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

@model_validator(mode="after")
def validate_content_format(self) -> "PublicAgentStandardizedIntakePayload":
    # Validate content formatting (URL, DTMF regex, max length)
    return self
```

### 3.2 Direct Enum Member Comparisons
* Domain Enums inherit from `StrEnum`. Compare Enum members directly (`self.payload_type == PayloadType.AUDIO`) instead of using `.value` or wrapping with `str(...)`.
* **Correct**: `if self.payload_type == PayloadType.AUDIO:`
* **Incorrect**: `if str(self.payload_type) == PayloadType.AUDIO.value:`

### 3.3 Explicit Rationale Comments ("WHY" Explanations)
* Always add comments or docstrings explaining **why** a non-obvious constraint, length formula, or security override exists:
  * **Identity Pseudonymization**: Document why `tokenized_citizen_id` is agnostic to identity source (MSISDN vs. UIDAI Token UID under Aadhaar Act §29).
  * **Resource Ceilings**: Document why `AudioDurationSeconds` caps at 600s (prevents GPU memory overflow and context truncation on SLM workers).
  * **Security Zeroing**: Document why `object.__setattr__` is used to override frozen models during prompt-injection neutralization.

### 3.4 Architecture Decision Record (ADR) References
* All model classes, validation handlers, and foundational modules **must include reference links to their respective ADR `.md` files** in `decisions/`:

```python
class PublicAgentStandardizedIntakePayload(StrictBaseModel):
    """Normalized, zero-PII public agent intake payload (Layer 2 -> Layer 3).

    See: decisions/step2.0_canonical_domain_schemas.md (Section 4.2)
    See: decisions/step0.3_zero_trust_tokenization.md
    """
```

### 3.5 Model-Agnostic Comments & Future-Proofing
* **Avoid Specific Vendor/Model Names**: Never hardcode specific model, vendor, or framework names (e.g. `Ollama`, `LLaMA-3`, `Whisper`, `GPT-4`) in code comments or docstrings, as underlying AI models will evolve or be replaced.
* **Use Architectural Role Terms**: Always use generic, role-based terminology:
  * **Correct**: `SLM/NLU extraction pipeline`, `ASR/STT audio transcription worker`, `AI governance engine`
  * **Incorrect**: `Ollama pipeline`, `Whisper transcription worker`, `LLaMA model`

---

## 4. Strict Type Safety & Immutability

### 4.1 Base Model Configuration (`StrictBaseModel`)
All domain models must inherit from `StrictBaseModel`, which enforces strict security and immutability:

```python
class StrictBaseModel(BaseModel):
    """Base model for all inter-layer payloads.

    See: decisions/step2.0_canonical_domain_schemas.md#31-base-configuration-strictbasemodel
    See: decisions/step1.2_runtime_strictness_linting.md
    """
    model_config = ConfigDict(
        extra="forbid",             # Rejects unexpected / injected keys
        frozen=True,                # Guarantees immutability post-instantiation
        validate_assignment=True,   # Validates assignments if unfrozen
        str_strip_whitespace=True,  # Auto-strips leading/trailing whitespace
        use_enum_values=True,       # Coerces enum values for clean serialization
    )
```

### 4.2 Reusable Constrained Types (`src/data_models/common/field_types.py`)
* Use `Annotated` type aliases with Pydantic `Field` constraints and `AfterValidator` functions for reusable domain types (`SessionId`, `PhoneNumberE164`, `HmacCitizenToken`, `UtcTimestamp`, `AudioDurationSeconds`, `AiConfidenceScore`).

### 4.3 Strict Dependency Injection & Non-Nullable Constructors
* **No Magic `None` Fallbacks in Constructors**: Never accept `None` as a default parameter value in class constructors (`__init__`) to implicitly trigger default instantiation or environment variable reads. Doing so obscures dependency contracts and masks upstream configuration bugs.
* **Explicit Dependency Injection**: Constructor parameters for core domain components, gateways, and services must be strictly non-nullable (e.g., `pepper_key: str`, `tokenizer: ZeroTrustIdentityTokenizer`).
* **Dedicated Factory Class Methods**: When effortless construction from default components or environment variables is desired, implement explicit `@classmethod` factories (e.g., `from_env(cls)` or `from_default(cls)`).
* **Permitted Nullability**: `None` is acceptable as a parameter value only at perimeter security boundaries (to evaluate absent HTTP headers cleanly) and within Pydantic schema state matrices representing inapplicable state fields.

---

## 5. Systemic Logical Error Prevention & Verification Methodology

To systematically prevent logical errors anywhere across the system (models, connectors, orchestrators, state machines, and API boundaries):

### 5.1 Lifecycle Dataflow Tracing
* **Trace Across Boundaries**: Never design validation rules or logic for a single component in isolation. Always trace:
  1. *Origin*: Where did this payload or state originate?
  2. *Survival*: What foreign keys or context must survive across this transition to maintain auditability?
  3. *Destination*: Who consumes this payload next, and what guarantees do they expect?

### 5.2 Global System Invariants
Code validators and business logic against non-negotiable system invariants:
* **Identity Invariant**: Zero cleartext PII in Layer 3 and Layer 4 contracts.
* **Auditability Invariant**: Every human manual adjudication MUST reference the escalation ticket ID (`SPP-CASE-...`) and carry officer audit notes (`review_notes`).
* **Financial Invariant**: Payout transaction IDs (`disbursement_txn_id`) and statuses exist ONLY for approved outcomes; rejection reasons exist ONLY for rejected outcomes.
* **Security Zeroing Invariant**: Adversarial injection attempts strictly zero confidence scores (`0.0`) and wipe extracted entities.
* **Fail-Fast Configuration & Secrets Invariant**: Never define fallback cryptographic keys or default production secrets in code. If an environment-injected secret (e.g. cryptographic pepper key, bearer token) is missing or empty, fail fast immediately with an explicit exception (`ValueError` or `RuntimeError`). Do not fall back to insecure default strings.

### 5.3 Exhaustive Matrix & Property-Based Testing
* **100% Enum Coverage**: State machine models and decision routers must use `@pytest.mark.parametrize` across 100% of Enum members to verify required, optional, and forbidden fields for every state.
* **Property-Based Verification**: Use property-based testing to stress-test logical boundaries against unexpected edge-case combinations.

---

## 6. Verification Checklist

Before committing any changes to models, schemas, or logic:

1. **Ruff Linter & Formatter**:
   ```bash
   .venv/bin/ruff check --fix . && .venv/bin/ruff format .
   ```
2. **Pytest Test Suite**:
   ```bash
   .venv/bin/pytest
   ```
3. **MyPy Static Type Checker**:
   ```bash
   .venv/bin/mypy src tests
   ```
