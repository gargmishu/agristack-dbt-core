# Canonical Domain Contracts & Data Schema Design

**Framework Step:** Phase 2 · Step 2.0: Define Canonical Domain Contracts & Standardized Schemas  
**Target Architecture:** FastAPI + Pydantic v2  
**Related Documents:**
- [roadmap.md](../roadmap.md)
- [step1.2_runtime_strictness_linting.md](./step1.2_runtime_strictness_linting.md)
- [step1.1_tech_stack_evaluation.md](./step1.1_tech_stack_evaluation.md)
- [flowchart.md](../design-specs/step3-guardrails/flowchart.md)
- [step0.4_database_schema_design.md](./step0.4_database_schema_design.md)
- [step0.3_zero_trust_tokenization.md](./step0.3_zero_trust_tokenization.md)

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

### 4.0 Shared & Reusable Validation Rules

To maintain consistency and avoid duplicate validation logic across services, the following validation rules are **shared across multiple domain payloads**:

| Shared Validation Rule | Target Field(s) | Shared Across Payloads | Validation Constraint Specification |
| :--- | :--- | :--- | :--- |
| **Extra Field Guardrail** | *All JSON Fields* | **All Payloads** | Enforced via `StrictBaseModel(extra="forbid")`. Rejects unexpected or injected keys. |
| **Auto Whitespace Trimming** | *All String Fields* | **All Payloads** | Enforced via `StrictBaseModel(str_strip_whitespace=True)`. Auto-trims leading/trailing spaces. |
| **Strict Enum Coercion** | *All Enum Fields* | **All Payloads** | Enforced via `StrictBaseModel(use_enum_values=True)`. Validates string against declared `Enum`. |
| **Payload Immutability** | *All Models* | **All Payloads** | Enforced via `StrictBaseModel(frozen=True)`. Attributes cannot be modified post-instantiation. |
| **Session ID Bounds** | `channel_session_id` | **WhatsAppIngressPayload**, **IVRIngressPayload**, **USSDIngressPayload**, **StandardizedIntakePayload**, **GovernanceRoutingPayload**, **SessionTelemetryLog** | Must be a non‑blank string length 8‑128 characters (`min_length=8, max_length=128`). |
| **E.164 Phone Format** | `originating_phone_number` | **WhatsAppIngressPayload**, **IVRIngressPayload**, **USSDIngressPayload** | Must match international E.164 format, e.g., `+919876543210`. |
| **UTC Timestamp Freshness** | `ingress_timestamp`, `intake_timestamp` (and any logging timestamps) | **WhatsAppIngressPayload**, **IVRIngressPayload**, **USSDIngressPayload**, **StandardizedIntakePayload**, **SessionTelemetryLog** | Must be valid ISO‑8601 UTC datetime; reject timestamps >5 s in the future (clock‑skew allowance). |
| **Audio URL Validation** | `audio_recording_url` | **WhatsAppIngressPayload**, **IVRIngressPayload** | Must be a valid HTTP/HTTPS URL (`HttpUrl`) pointing to a signed audio file. |
| **AI Score Bounds** | `ai_confidence_score` | **ExtractedEntityPayload**, **GovernanceRoutingPayload** | Float strictly constrained between `0.0` and `1.0` inclusive (`ge=0.0, le=1.0`). |

---

### 4.1 Carrier Ingress Payloads (`src/models/ingress.py`)

Connectors for each channel (WhatsApp, IVR, USSD) receive raw carrier payloads. Raw PII (e.g., phone number) is isolated at Layer 1 and Layer 2 and MUST be tokenized before passing into Layer 3. Here we define the **Layer 1 $\rightarrow$ Layer 2** Schema:

#### WhatsApp Ingress Payload
```python
class WhatsAppIngressPayload(StrictBaseModel):
    channel_session_id: str = Field(..., min_length=8, max_length=128, description="Conversational channel session ID")
    originating_phone_number: str = Field(..., description="Carrier messaging user ID / phone number (E.164 standard)")
    channel_message_id: str = Field(..., description="Carrier/Provider unique message ID (e.g. Meta wmid, RCS message ID)")
    payload_type: PayloadType
    ingress_timestamp: datetime = Field(..., description="UTC timestamp when carrier received event")
    audio_recording_url: Optional[HttpUrl] = Field(None, description="Signed URL for .ogg audio file")
    text_body: Optional[str] = Field(None, max_length=1000, description="Raw text message")
```

##### WhatsApp Ingress Specific Validations:
1. **Provider Message ID:** `channel_message_id` must be a non-empty string.
2. **Mutual Exclusivity & Content Completeness (Audio vs. Text):**
   - If `payload_type == AUDIO`: `audio_recording_url` **must** be a valid HTTP/HTTPS URL pointing to an `.ogg` file; `text_body` **must** be `None`.
   - If `payload_type == TEXT`: `text_body` **must** be a non-empty string (1–1000 chars); `audio_recording_url` **must** be `None`.

---

#### IVR Telephony Ingress Payload
```python
class IVRIngressPayload(StrictBaseModel):
    channel_session_id: str = Field(..., min_length=8, max_length=128, description="Telephony Provider Call Session ID")
    originating_phone_number: str = Field(..., description="Originating ANI phone number (E.164 standard)")
    audio_recording_url: HttpUrl = Field(..., description="Signed URL for .wav recording")
    duration_seconds: int = Field(..., ge=1, le=600)
    ingress_timestamp: datetime = Field(..., description="UTC timestamp when call arrived at SIP trunk")
```

##### IVR Telephony Specific Validations:
1. **Call Duration Bounds:** `duration_seconds` must be an integer strictly bounded between `1` and `600` seconds (10 minutes max); must reject 0 or negative values.

---

#### USSD Menu Ingress Payload
```python
class USSDIngressPayload(StrictBaseModel):
    channel_session_id: str = Field(..., min_length=8, max_length=128, description="Telco network session ID")
    originating_phone_number: str = Field(..., description="Originating MSISDN phone number (E.164 standard)")
    ussd_service_code: str = Field(..., example="*147#")
    ussd_user_digit_selection: str = Field(..., max_length=50, description="Digit selection or menu string")
    ingress_timestamp: datetime = Field(..., description="UTC timestamp when telco received USSD code")
```

##### USSD Menu Specific Validations:
1. **Shortcode Pattern:** `ussd_service_code` must match valid USSD shortcode pattern (e.g., `^\*\d+#$`).
2. **Digit Selection Bounds:** `ussd_user_digit_selection` must be a non-empty string of menu choices or digit entries (maximum 50 characters).

---

### 4.2 Public Agent Intake Payload (`src/models/intake.py`)

This is the **immutable contract payload** submitted to `PublicAgentIntakeApi`. Cleartext PII (raw phone numbers) is stripped, and only `tokenized_citizen_id` (SHA-256 HMAC token) is present. Here we define the **Layer 2 $\rightarrow$ Layer 3** Schema:

```python
class StandardizedIntakePayload(StrictBaseModel):
    """
    Normalized, PII-purged JSON payload passed from Layer 2 Connectors to Layer 3 Intake API.
    """
    channel_session_id: str = Field(..., min_length=8, max_length=128, description="Unified channel session ID")
    tokenized_citizen_id: str = Field(..., min_length=64, max_length=64, description="SHA-256 HMAC Token")
    channel_type: ChannelType
    payload_type: PayloadType
    structure_level: StructureLevel
    unprocessed_input_content: str = Field(..., max_length=5000, description="Audio metadata stream reference or raw text string")
    intake_timestamp: datetime = Field(..., description="UTC timestamp when Layer 2 normalized payload")
    language_locale: str = Field("hi-IN", pattern=r"^[a-z]{2}-[A-Z]{2}$", description="BCP 47 language code")
```

##### Standardized Intake Specific Validations:
1. **Zero-PII Token Validation:** `tokenized_citizen_id` must be an exact 64-character hexadecimal SHA-256 HMAC string. Cleartext phone numbers (or any raw PII) are strictly prohibited and rejected.
   - **Design intent:** `tokenized_citizen_id` is a **stable, pseudonymous citizen identity token** — it is not a "tokenized phone". The schema is intentionally agnostic to the underlying PII source. Layer 2 is the only layer that knows what was fed into the HMAC.
   - **Current derivation (phone-sourced channels):** `HMAC-SHA256(secret_key, phone_number)` — used for WhatsApp, IVR, and USSD channels where the citizen is identified by their MSISDN.
   - **Future derivation (Aadhaar-sourced channels):** Raw Aadhaar numbers **must never** be directly HMAC'd. The **Aadhaar Act 2016 §29** prohibits any entity from storing or hashing raw Aadhaar numbers without being a UIDAI-registered Authentication User Agency (AUA). For Aadhaar-authenticated channels, Layer 2 must call UIDAI's e-KYC/OTP API, receive the **UIDAI Token UID** (an opaque, AUA-scoped pseudonym), and compute `HMAC-SHA256(secret_key, uidai_token_uid)`. The raw Aadhaar number is never persisted or passed downstream.
   - **Other future sources (Voter ID, PAN):** May be used as HMAC input only where lawful purpose and explicit citizen consent under the DPDP Act exist.
2. **Non-Empty Input Content:** `unprocessed_input_content` must be a string between 1 and 5000 characters; validator must reject empty or whitespace-only strings.
3. **BCP 47 Locale Pattern:** `language_locale` must match BCP 47 language format regex `^[a-z]{2}-[A-Z]{2}$` (e.g., `"hi-IN"`). Defaults to `"hi-IN"`.

---

### 4.3 Intent & Governance Schemas (`src/models/governance.py`)

Here we define the **Layer 3 $\rightarrow$ Layer 4** Schema:

#### SLM Extracted Entity Payload
```python
class ExtractedEntityPayload(StrictBaseModel):
    application_intent: ApplicationIntent
    ai_confidence_score: float = Field(..., ge=0.0, le=1.0)
    domain_entities: Dict[str, Any] = Field(default_factory=dict, description="Parsed domain fields: district, crop, land_size")
    is_adversarial_attempt: bool = Field(False, description="Flagged by prompt injection firewall")
    is_structured_menu_bypass: bool = Field(False, description="True for USSD structured menu selections")
```

##### SLM Extracted Entity Specific Validations:
1. **Domain Entities Structure:** `domain_entities` must be a dictionary containing parsed domain entity keys (e.g., `district`, `crop`, `land_size`).
2. **Adversarial Zeroing Enforcement Rule:** If `is_adversarial_attempt == True`, `ai_confidence_score` **must** be automatically coerced to `0.0` regardless of the original score.

---

#### Governance Routing Decision Payload
```python
class GovernanceRoutingPayload(StrictBaseModel):
    channel_session_id: str = Field(..., min_length=8, max_length=128, description="Unified channel session ID")
    payload_id: str = Field(..., description="Foreign key referencing extraction payload (session_extraction_details.payload_id)")
    ai_confidence_score: float = Field(..., ge=0.0, le=1.0)
    eligibility_status: EligibilityStatus
    governance_decision: GovernanceDecision
    disbursement_txn_id: Optional[str] = Field(None, description="Populated for AUTO_APPROVE / MANUAL_APPROVE")
    assigned_caseworker_id: Optional[str] = Field(None, description="Populated for ROUTE_FOR_MANUAL_REVIEW")
    rejection_reason: Optional[str] = Field(None, description="Populated for AUTO_REJECT / MANUAL_REJECT")
```

##### Governance Routing Decision Specific Validations:
1. **Payload UUID Foreign Key:** `payload_id` must be a valid UUID string referencing `session_extraction_details.payload_id`.
2. **Conditional Field Population Rules:**
   - If `governance_decision` is `AUTO_APPROVE`, `MANUAL_APPROVE`, or `AUTOMATED_PAYOUT`: `disbursement_txn_id` **must** be populated; `rejection_reason` **must** be `None`.
   - If `governance_decision` is `AUTO_REJECT` or `MANUAL_REJECT`: `rejection_reason` **must** be populated; `disbursement_txn_id` **must** be `None`.
   - If `governance_decision` is `ROUTE_FOR_MANUAL_REVIEW` or `HUMAN_REVIEW`: `assigned_caseworker_id` **must** be populated.

---

## 5. API Exception Handling & Security Defense

To prevent schema details or stack traces from leaking to external callers, FastAPI exception handlers format validation errors into RFC 7807 problem details:

```python
# src/errors/handlers.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

async def validation_exception_handler(incoming_request: Request, validation_error: ValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "type": "https://api.agristack.gov.in/errors/invalid-payload",
            "title": "Invalid Payload Structure",
            "status": 422,
            "detail": "The submitted payload violated inter-layer schema validation constraints.",
            "invalid_params": [
                {
                    "field": ".".join(str(location_segment) for location_segment in error_detail["loc"]),
                    "reason": error_detail["msg"],
                }
                for error_detail in validation_error.errors()
            ],
        },
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
