# Canonical Domain Contracts & Data Schema Design

**Framework Step:** Phase 2 · Step 2.0: Define Canonical Domain Contracts & Standardized Schemas  
**Target Architecture:** FastAPI + Pydantic v2  
**Related Documents:**
- [roadmap.md](../roadmap.md)
- [runtime_strictness_linting.md](./runtime_strictness_linting.md)
- [tech_stack_evaluation.md](./tech_stack_evaluation.md)
- [flowchart.md](../design-specs/step3-guardrails/flowchart.md)
- [database_schema_design.md](./database_schema_design.md)
- [zero_trust_tokenization.md](./zero_trust_tokenization.md)

---

## 1. Executive Summary

This document defines the implementation specifications for **Step 2.0 of the Master Roadmap**. To satisfy Zero-Trust security and prevent AI hallucination or malformed payload injection, all data passing between system layers (Layer 1 Connectors $\rightarrow$ Layer 2 Gateways $\rightarrow$ Layer 3 Public Agent Intake $\rightarrow$ Layer 4 Orchestrator Brain) must be strictly validated at runtime using standardized enums (`src/models/enums.py`) and **Pydantic v2** models with extra-field prohibition (`extra="forbid"`), immutable assignment, and explicit type checking.

---

## 2. Framework Selection & Alternatives Evaluated

To establish zero-trust inter-layer payload validation, four runtime validation approaches were evaluated:

| Concern | Chosen Tool | Alternatives Evaluated | Primary Decision Drivers |
| :--- | :--- | :--- | :--- |
| **Runtime Data Validation** | **Pydantic v2** | Marshmallow, Cerberus/JSONSchema, Attrs+Cattrs | Rust core engine (`pydantic-core`), native FastAPI integration, `ConfigDict(extra="forbid")` guardrails. |

### Decision Rationale: **Pydantic v2**
- **Alternatives Evaluated:**
  1. *Marshmallow:* Requires duplicating schema classes and dataclasses; runs significantly slower in pure Python.
  2. *Cerberus / JSONSchema:* Validates raw dicts against JSON schema dicts, but lacks IDE autocompletion, type hint integration, and automatic Python object instantiation.
  3. *Attrs + Cattrs:* Strong object model, but requires separate serialization layers (`cattrs`) and lacks native FastAPI integration.
- **Decision Rationale:** **Pydantic v2** features a core engine written in Rust (`pydantic-core`), delivering 5x–20x performance improvements over v1. It integrates directly with FastAPI for automatic OpenAPI generation, supports `ConfigDict(extra="forbid")` for zero-trust payload injection defense, and handles string stripping and enum coercion natively.

---

## 3. Base Configuration (`StrictBaseModel`)

All domain payloads inherit from a unified `StrictBaseModel` to enforce Zero-Trust security rules:

```python
from pydantic import BaseModel, ConfigDict

class StrictBaseModel(BaseModel):
    """
    Base model for all inter-layer payloads.
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
```

---

## 3. Standardized Enums (`src/models/enums.py`)

Standardized enums establish a single source of truth across all architectural layers, eliminating "magic strings", securing SLM entity extraction against uncalibrated outputs, and providing 1:1 mapping with database `ENUM` types:

```python
from enum import Enum

class ChannelType(str, Enum):
    WHATSAPP = "whatsapp"
    IVR_VOICE = "ivr_voice"
    USSD = "ussd"
    SMS = "sms"

class PayloadType(str, Enum):
    AUDIO = "audio"
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"

class StructureLevel(str, Enum):
    FREE_TEXT = "free_text"
    MENU_SELECTION = "menu_selection"
    DTMF_SELECTION = "dtmf_selection"

class ApplicationIntent(str, Enum):
    APPLY_SUBSIDY = "apply_subsidy"
    CHECK_STATUS = "check_status"
    SUBMIT_APPEAL = "submit_appeal"
    GRIEVANCE_REDIRECTION = "grievance_redirection"
    UPDATE_CROP_DETAILS = "update_crop_details"
    SCHEME_INQUIRY = "scheme_inquiry"
    UNKNOWN = "unknown"

class EligibilityStatus(str, Enum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"

class GovernanceDecision(str, Enum):
    AUTOMATED_PAYOUT = "AUTOMATED_PAYOUT"
    AUTO_APPROVE = "AUTO_APPROVE"
    AUTO_REJECT = "AUTO_REJECT"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    ROUTE_FOR_MANUAL_REVIEW = "ROUTE_FOR_MANUAL_REVIEW"
    REQUEST_MORE_INFO = "REQUEST_MORE_INFO"
    MANUAL_APPROVE = "MANUAL_APPROVE"
    MANUAL_REJECT = "MANUAL_REJECT"

class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    TIMEOUT = "TIMEOUT"

class ApplicationStatus(str, Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    FINALIZED = "FINALIZED"
    REJECTED = "REJECTED"
    APPEALED = "APPEALED"

class DisbursementStatus(str, Enum):
    PENDING = "PENDING"
    INITIATED = "INITIATED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETURNED = "RETURNED"
```

---

## 4. Inter-Layer Data Validation Schemas

### 4.1 Layer 1 $\rightarrow$ Layer 2 Carrier Ingress Schemas (`src/models/ingress.py`)

Channel-specific connectors receive raw carrier payloads. Raw PII (e.g., phone number) is isolated at Layer 1/2 and MUST be tokenized before passing into Layer 3.

#### WhatsApp Ingress Payload
```python
from datetime import datetime
from typing import Optional
from pydantic import Field, HttpUrl
from src.models.base import StrictBaseModel
from src.models.enums import PayloadType

class WhatsAppIngressPayload(StrictBaseModel):
    whatsapp_sender_id: str = Field(..., description="Carrier WhatsApp user ID / phone number (E.164 standard)")
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

### 4.2 Layer 2 $\rightarrow$ Layer 3 Standardized Intake Payload (`src/models/intake.py`)

This is the **immutable contract payload** submitted to `PublicAgentIntakeApi`. Cleartext PII (raw phone numbers) is stripped, and only `tokenized_citizen_id` (SHA-256 HMAC token) is present.

```python
from datetime import datetime
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

### 4.3 Layer 4 Intent & Governance Schemas (`src/models/governance.py`)

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
    disbursement_ref: Optional[str] = Field(None, description="Populated for AUTO_APPROVE / MANUAL_APPROVE")
    caseworker_id: Optional[str] = Field(None, description="Populated for ROUTE_FOR_MANUAL_REVIEW")
    rejection_reason: Optional[str] = Field(None, description="Populated for AUTO_REJECT / MANUAL_REJECT")
```

---

## 5. API Exception Handling & Security Defense

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

## 6. Physical File Implementation Plan

Step 2.0 establishes the following file structure:

```text
agristack-dbt-core/
└── src/
    ├── models/
    │   ├── __init__.py
    │   ├── base.py                 <-- StrictBaseModel definition
    │   ├── enums.py                <-- Channel, Payload, Intent & Governance Enums
    │   ├── ingress.py              <-- WhatsApp, IVR, USSD carrier models
    │   ├── intake.py               <-- StandardizedIntakePayload model
    │   └── governance.py           <-- SLM Extraction & Governance models
    └── errors/
        ├── __init__.py
        └── handlers.py             <-- RFC 7807 validation error handler
```

---

## 7. Glossary of Acronyms & Technical Terms

| Acronym / Term | Full Name / Expansion | Technical Context & Definition in This Project |
| :--- | :--- | :--- |
| **DPI** | **Digital Public Infrastructure** | Sovereign digital core systems enabling public service delivery at national scale. |
| **PII** | **Personally Identifiable Information** | Sensitive citizen identity data. Zero-Trust rules strictly forbid unencrypted cleartext PII in persistent storage. |
| **SLM** | **Small Language Model** | Local, lightweight language models (e.g. LLaMA-3-8B) deployed on private infrastructure for sovereign entity extraction. |
| **RFC** | **Request for Comments** | Official internet engineering standards (e.g. RFC 7807 for standardized HTTP API problem details). |
| **HMAC** | **Hash-based Message Authentication Code** | Cryptographic hashing using SHA-256 to tokenize sensitive PII. |
