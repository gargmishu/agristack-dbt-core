# Runtime Strictness, Schema Validation & Code Quality Design

**Framework Step:** Phase 1 · Step 1.2: Enforce Runtime Strictness & Linting  
**Target Architecture:** FastAPI + Pydantic v2 + Ruff + MyPy  
**Related Documents:**
- [roadmap.md](../roadmap.md)
- [tech_stack_evaluation.md](./tech_stack_evaluation.md)
- [flowchart.md](../design-specs/step3-guardrails/flowchart.md)
- [database_schema_design.md](./database_schema_design.md)
- [zero_trust_tokenization.md](./zero_trust_tokenization.md)

---

## 1. Executive Summary

This document defines the implementation specifications for **Step 1.2 of the Master Roadmap**. To satisfy Zero-Trust security and prevent AI hallucination or malformed payload injection, all data passing between system layers (Layer 1 Connectors $\rightarrow$ Layer 2 Gateways $\rightarrow$ Layer 3 Public Agent Intake $\rightarrow$ Layer 4 Orchestrator Brain) must be strictly validated at runtime using **Pydantic v2** models with extra-field prohibition (`extra="forbid"`), immutable assignment, and explicit type checking.

Additionally, static code quality and security boundaries are enforced using **Ruff** (linting/formatting), **MyPy** (strict type checking), **pytest** (async validation tests), and **pre-commit** hooks.

---

## 2. Tooling & Infrastructure Specifications

### 2.1 Linter & Formatter (`ruff`)
We adopt **Ruff** as the single unified engine for Python linting and formatting. Ruff is configured via `pyproject.toml` with the following rule suites:

- `E` / `W`: Pycodestyle errors and warnings.
- `F`: Pyflakes logical checks.
- `B`: Flake8-bugbear (common bug patterns).
- `UP`: Pyupgrade (modern Python 3.11+ syntax enforcement).
- `S`: Bandit security checks (detecting hardcoded secrets, unsafe deserialization).
- `I`: Isort (automatic import sorting).
- `SIM`: Code simplification rules.
- `PL`: Pylint rule subset.

```toml
# pyproject.toml snippet
[tool.ruff]
target-version = "py311"
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "W", "F", "B", "UP", "S", "I", "SIM", "PL"]
ignore = ["S101"] # Allow assert in tests

[tool.ruff.lint.isort]
known-first-party = ["src"]
```

### 2.2 Static Type Checker (`mypy`)
Static typing guarantees that inter-layer payloads match declared interfaces before execution.

```toml
[tool.mypy]
python_version = "3.11"
strict = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_return_any = true
plugins = ["pydantic.mypy"]
```

### 2.3 Pre-Commit Hooks (`.pre-commit-config.yaml`)
To prevent non-compliant code from entering the repository, git pre-commit hooks enforce:
1. `ruff check --fix` and `ruff format`
2. `mypy` strict execution
3. Custom PII check script verifying no cleartext PII field names (e.g. `raw_aadhaar`, `unhashed_phone`) are added to persistent models.

---

## 3. Inter-Layer Data Validation Schemas (Pydantic v2)

All domain payloads inherit from a unified `StrictBaseModel` to enforce Zero-Trust security rules.

### 3.1 Base Configuration (`StrictBaseModel`)

```python
from pydantic import BaseModel, ConfigDict

class StrictBaseModel(BaseModel):
    """
    Base model for all inter-layer payloads.
    - extra="forbid": Rejects payload pollution / unexpected injected keys.
    - frozen=True: Guarantees immutability as data moves between layers.
    - validate_assignment=True: Validates mutations if model is unfrozen.
    - str_strip_whitespace=True: Auto-strips leading/trailing whitespace.
    """
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_assignment=True,
        str_strip_whitespace=True,
        use_enum_values=True,
    )
```

---

### 3.2 Standardized Enums (`src/models/enums.py`)

```python
from enum import Enum

class ChannelType(str, Enum):
    WHATSAPP = "whatsapp"
    IVR = "ivr"
    USSD = "ussd"

class PayloadType(str, Enum):
    AUDIO = "audio"
    TEXT = "text"

class StructureLevel(str, Enum):
    FREE_TEXT = "free_text"
    MENU_SELECTION = "menu_selection"

class ApplicationIntent(str, Enum):
    APPLY_SUBSIDY = "apply_subsidy"
    CHECK_STATUS = "check_status"
    GRIEVANCE_REDIRECTION = "grievance_redirection"
    UNKNOWN = "unknown"

class EligibilityStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"

class GovernanceDecision(str, Enum):
    AUTOMATED_PAYOUT = "AUTOMATED_PAYOUT"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    AUTO_REJECT = "AUTO_REJECT"
```

---

### 3.3 Layer 1 $\rightarrow$ Layer 2 Carrier Ingress Schemas (`src/models/ingress.py`)

Channel-specific connectors receive raw carrier payloads. Raw PII (e.g., phone number) is isolated at Layer 1/2 and MUST be tokenized before passing into Layer 3.

#### WhatsApp Ingress Payload
```python
from datetime import datetime
from typing import Optional
from pydantic import Field, HttpUrl
from src.models.base import StrictBaseModel
from src.models.enums import PayloadType

class WhatsAppIngressPayload(StrictBaseModel):
    wa_id: str = Field(..., description="Carrier WhatsApp ID / Phone Number")
    message_id: str = Field(..., description="Meta unique message ID")
    payload_type: PayloadType
    media_url: Optional[HttpUrl] = Field(None, description="Signed URL for .ogg audio file")
    text_body: Optional[str] = Field(None, max_length=1000, description="Raw text message")
    timestamp: datetime
```

#### IVR Telephony Ingress Payload
```python
class IVRIngressPayload(StrictBaseModel):
    call_sid: str = Field(..., description="Telephony Provider Call Session ID")
    caller_ani: str = Field(..., description="Originating ANI phone number")
    audio_wav_url: HttpUrl = Field(..., description="Signed URL for .wav recording")
    duration_seconds: int = Field(..., ge=1, le=600)
    timestamp: datetime
```

#### USSD Menu Ingress Payload
```python
class USSDIngressPayload(StrictBaseModel):
    session_id: str = Field(..., description="Telco network session ID")
    phone_number: str = Field(..., description="Originating MSISDN")
    service_code: str = Field(..., example="*147#")
    user_input: str = Field(..., max_length=50, description="Digit selection or menu string")
    timestamp: datetime
```

---

### 3.4 Layer 2 $\rightarrow$ Layer 3 Standardized Intake Payload (`src/models/intake.py`)

This is the **immutable contract payload** submitted to `PublicAgentIntakeApi`. Notice that cleartext PII (raw phone numbers) is stripped, and only `tokenized_citizen_id` (SHA-256 HMAC token) is present.

```python
from datetime import datetime
from typing import Optional
from pydantic import Field, field_validator
from src.models.base import StrictBaseModel
from src.models.enums import ChannelType, PayloadType, StructureLevel

class StandardizedIntakePayload(StrictBaseModel):
    """
    Normalized, PII-purged JSON payload passed from Layer 2 Connectors to Layer 3 Intake API.
    """
    channel_type: ChannelType
    payload_type: PayloadType
    structure_level: StructureLevel
    channel_session_id: str = Field(..., min_length=8, max_length=128)
    tokenized_citizen_id: str = Field(..., min_length=64, max_length=64, description="SHA-256 HMAC Token")
    raw_content: str = Field(..., max_length=5000, description="Audio metadata stream reference or raw text string")
    locale: str = Field("hi-IN", pattern=r"^[a-z]{2}-[A-Z]{2}$", description="BCP 47 language code")
    timestamp: datetime

    @field_validator("raw_content")
    @classmethod
    def validate_content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("raw_content cannot be empty or blank")
        return v
```

---

### 3.5 Layer 4 Intent & Governance Schemas (`src/models/governance.py`)

#### SLM Extracted Entity Payload
```python
from typing import Any, Dict
from pydantic import Field, field_validator
from src.models.base import StrictBaseModel
from src.models.enums import ApplicationIntent

class ExtractedEntityPayload(StrictBaseModel):
    intent: ApplicationIntent
    entities: Dict[str, Any] = Field(default_factory=dict, description="Parsed domain fields: district, crop, land_size")
    ai_confidence_score: float = Field(..., ge=0.0, le=1.0)
    is_adversarial_attempt: bool = Field(False, description="Flagged by prompt injection firewall")
    bypass_ai: bool = Field(False, description="True for USSD structured menu selections")

    @field_validator("ai_confidence_score")
    @classmethod
    def enforce_adversarial_zero_score(cls, v: float, info) -> float:
        # If adversarial attempt is detected, force confidence score to 0.0
        if info.data.get("is_adversarial_attempt", False):
            return 0.0
        return v
```

#### Governance Routing Decision Payload
```python
from typing import Optional
from pydantic import Field
from src.models.base import StrictBaseModel
from src.models.enums import EligibilityStatus, GovernanceDecision

class GovernanceRoutingPayload(StrictBaseModel):
    session_id: str
    payload_id: str
    ai_confidence_score: float = Field(..., ge=0.0, le=1.0)
    eligibility_status: EligibilityStatus
    governance_decision: GovernanceDecision
    disbursement_ref: Optional[str] = Field(None, description="Populated for AUTOMATED_PAYOUT")
    caseworker_id: Optional[str] = Field(None, description="Populated for HUMAN_REVIEW")
    rejection_reason: Optional[str] = Field(None, description="Populated for AUTO_REJECT")
```

---

## 4. API Exception Handling & Security Defense

To prevent schema details or stack traces from leaking to external callers, FastAPI exception handlers format validation errors into RFC 7807 problem details:

```python
# src/errors/handlers.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

async def validation_exception_handler(request: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "type": "https://api.agristack.gov.in/errors/invalid-payload",
            "title": "Invalid Payload Structure",
            "status": 422,
            "detail": "The submitted payload violated inter-layer schema validation constraints.",
            "invalid_params": [
                {"field": ".".join(str(loc) for loc in err["loc"]), "reason": err["msg"]}
                for err in exc.errors()
            ]
        }
    )
```

---

## 5. Physical File Scaffolding Plan

Execution of Step 1.2 requires establishing the following file structure:

```text
agristack-dbt-core/
├── pyproject.toml                  <-- Ruff, MyPy, pytest configuration
├── .pre-commit-config.yaml         <-- Git hooks config
├── src/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py             <-- Pydantic BaseSettings for env vars
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py                 <-- StrictBaseModel definition
│   │   ├── enums.py                <-- Channel, Payload, Intent & Governance Enums
│   │   ├── ingress.py              <-- WhatsApp, IVR, USSD carrier models
│   │   ├── intake.py               <-- StandardizedIntakePayload model
│   │   └── governance.py           <-- SLM Extraction & Governance models
│   └── errors/
│       ├── __init__.py
│       └── handlers.py             <-- RFC 7807 validation error handler
└── tests/
    ├── unit/
    │   ├── test_schemas.py         <-- Unit tests for Pydantic models
    │   └── test_linting.py         <-- Ruff & MyPy compliance assertions
    └── security/
        └── test_pii_tokenization.py <-- Assert no cleartext PII in intake payloads
```

---

## 6. Implementation Task Checklist

| Task | Component | Key Output Files | Verification Metric |
| :--- | :--- | :--- | :--- |
| **Task 1** | Code Quality Tooling | `pyproject.toml`, `.pre-commit-config.yaml` | `ruff check .` and `mypy src` pass with zero errors |
| **Task 2** | Base Models & Enums | `src/models/base.py`, `src/models/enums.py` | Models reject extra fields (`extra="forbid"`) |
| **Task 3** | Inter-Layer Schemas | `src/models/ingress.py`, `src/models/intake.py`, `src/models/governance.py` | Pydantic validation unit tests pass |
| **Task 4** | Exception Middleware | `src/errors/handlers.py` | HTTP 422 JSON response adheres to RFC 7807 |
| **Task 5** | Test Suite & PII Security Gate | `tests/unit/test_schemas.py`, `tests/security/test_pii_tokenization.py` | 100% test pass rate on schema constraints |

---

## 7. Next Steps & Phase Transition

Upon approval of this design document and completion of the implementation tasks:
- **Proceed to Phase 2 (Step 2.1 & 2.2):** Scaffold remaining 4-layer architecture directories (`src/intake/`, `src/connectors/`, `src/orchestrator/`, `src/services/`).
