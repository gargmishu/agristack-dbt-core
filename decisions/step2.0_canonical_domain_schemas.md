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

class DomainEntityKey(str, Enum):
    DISTRICT = "district"
    TALUKA = "taluka"
    VILLAGE = "village"
    CROP_NAME = "crop_name"
    CROP_VARIETY = "crop_variety"
    LAND_SIZE_ACRES = "land_size_acres"
    SUBSIDY_SCHEME_ID = "subsidy_scheme_id"
    SURVEY_NUMBER = "survey_number"
    BANK_ACCOUNT_LAST4 = "bank_account_last4"
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
| **Session ID Bounds** | `channel_session_id` | **WhatsAppIngressPayload**, **IVRIngressPayload**, **USSDIngressPayload**, **StandardizedIntakePayload**, **GovernanceRoutingPayload**, **SessionTelemetryLog** | Must be a non‑blank string, `min_length=8, max_length=128`. **min=8:** entropy floor — 8 alphanumeric chars ≈ 48 bits, sufficient to prevent brute-force session guessing; all real carrier IDs are ≥8 chars. **max=128:** hard ceiling covering the widest known carrier format (Meta wmid: 64–100 chars, SIP Call-ID: 36–72 chars, USSD telco session: 8–20 chars) while rejecting oversized injected strings. |
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
    channel_message_id: str = Field(..., min_length=8, max_length=128, description="Carrier/Provider unique message ID (e.g. WhatsApp wmid, RCS message ID)")
    payload_type: PayloadType
    ingress_timestamp: datetime = Field(..., description="UTC timestamp when carrier received event")
    audio_recording_url: Optional[HttpUrl] = Field(None, description="Signed URL for .ogg audio file")
    text_body: Optional[str] = Field(None, max_length=1000, description="Raw text message")
```

##### WhatsApp Ingress Specific Validations:
1. **Provider Message ID Bounds:** `channel_message_id` must be a non-empty string, `min_length=8, max_length=128`.
   - **min=8:** entropy floor matching `channel_session_id`; all real carrier message IDs are ≥8 chars — shorter values indicate truncation or spoofing.
   - **max=128:** covers the longest known format (WhatsApp wmid: 50–100 chars, RCS UUID compound: 36–72 chars, SMS provider ID: 8–32 chars) while providing a hard ceiling against oversized injection.
   - **WhatsApp wmid format note:** WhatsApp message ids always begins with the `wamid.` prefix ("wa" = WhatsApp) followed by a base64-encoded payload issued by the WhatsApp Business Platform. A value that does not start with `wamid.` on a WhatsApp channel is anomalous and should be flagged.
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
1. **Call Duration Bounds:** `duration_seconds` must be an integer, `ge=1, le=600`.
   - **min=1 (ge=1):** A call with `duration_seconds=0` means the call connected but immediately dropped before any audio was captured — no usable recording exists. Negative values are physically impossible. Any call that produced a valid `audio_recording_url` must have at least 1 second of audio.
   - **max=600 (le=600, i.e., 10 minutes):** Chosen from three converging constraints:
     1. **Flow design ceiling:** The longest AgriStack IVR flow (subsidy application) was derived bottom-up from its component steps: opening greeting + language selection (~15 s) + 5 navigation menu levels at ~15 s each (~75 s) + 5 data-entry inputs at ~30 s each (system prompt → DTMF digits → readback → confirm = ~150 s) + summary readback (~20 s) + closing + reference number announcement (~15 s) = **~275 s ≈ 4.6 min**. 600s gives 2× headroom above that ceiling without being unbounded.
     2. **Audio file size:**  The file size formula is `sample_rate × bytes_per_sample × channels × duration`. At standard IVR encoding (8 kHz, 8-bit, mono) & 10min audio, it becomees `8,000 × 1 × 1 × 600 = 4.8 MB`. We are currently assuming that SLMs should be able to handle audio files upto this size w/o chunking.
     3. **Anti-resource-exhaustion:** A hard ceiling prevents stuck or adversarial calls from filling the audio storage bucket with arbitrarily large files.

---

#### USSD Menu Ingress Payload
```python
class USSDIngressPayload(StrictBaseModel):
    channel_session_id: str = Field(..., min_length=8, max_length=128, description="Telco network session ID")
    originating_phone_number: str = Field(..., description="Originating MSISDN phone number (E.164 standard)")
    ussd_service_code: str = Field(..., pattern=r"^\*\d+(\*\d+)*#$", description="USSD shortcode (e.g., *147#, *147*1*2#)")
    ussd_user_digit_selection: str = Field(..., min_length=1, max_length=64, description="Concatenated digit selections and data entries separated by *")
    ingress_timestamp: datetime = Field(..., description="UTC timestamp when telco received USSD code")
```

##### USSD Menu Specific Validations:
1. **Shortcode Pattern:** `ussd_service_code` must match the USSD shortcode regex `^\*\d+(\*\d+)*#$`.
   - **Rule:** Must start with `*`, end with `#`, contain only digits and `*` segment separators — no spaces, letters, or special characters.
   - **Segment structure:** One or more numeric segments separated by `*`. Each segment must contain at least one digit.
   - **Valid examples:**
     - `*147#` — single-segment base code
     - `*147*1#` — base code with one sub-menu selection
     - `*147*1*2#` — base code with two levels of sub-menu navigation
     - `*99*1234*9876543210#` — NUUP/IMPS style parameterised code (NPCI standard)
   - **Invalid examples (must be rejected):**
     - `147#` — missing leading `*`
     - `*147` — missing trailing `#`
     - `*147**2#` — empty segment between two `*` delimiters
     - `*ABC#` — non-numeric segment
     - `* 147#` — whitespace in code
2. **Digit Selection Bounds:** `ussd_user_digit_selection` must be a non-empty string of concatenated digit selections and data entries separated by `*` (minimum 1, maximum 64 characters).
   - **Formula:** `max_length = 2N + D×(L_d + 1) - 1`
     - `N` = number of navigation-only menu levels (each produces exactly 1 digit: the citizen presses `1`, `2`, etc.)
     - `D` = number of data-entry levels (citizen types a free numeric string, e.g., a loan ID or mobile number)
     - `L_d` = maximum digit length of each data-entry field
     - The `(N + D - 1)` term accounts for `*` separators between all segments; each segment contributes 1 separator except the last.
   - **How parameters are chosen:**
     - `N=5` — derived from the deepest AgriStack USSD flow (5 menu levels: scheme → state → district → sub-scheme → action). Increase if new flows add deeper navigation.
     - `D=5` — maximum number of free-input fields across any single USSD session (e.g., land parcel ID, mobile number, crop type code, season, amount). Increase if a flow requires more user inputs.
     - `L_d=10` — longest numeric data field expected (10-digit mobile number / MSISDN). If a 16-digit account number or Aadhaar-linked reference is ever required, update to `L_d=16`.
   - **Calculation:** `2(5) + 5×(10+1) - 1 = 10 + 55 - 1 = 64`.
   - **Recalculation rule:** If the USSD flow design changes (deeper menus or longer input fields), update `N`, `D`, or `L_d` and recompute. The `max_length` in the `Field(...)` definition must be updated in lockstep.

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
    unprocessed_input_content: str = Field(..., max_length=5000, description="Signed audio recording URL (for AUDIO) or raw text / DTMF digit string (for TEXT)")
    intake_timestamp: datetime = Field(..., description="UTC timestamp when Layer 2 normalized payload")
    language_locale: str = Field("hi-IN", pattern=r"^[a-z]{2}-[A-Z]{2}$", description="BCP 47 language code")
```

##### Standardized Intake Specific Validations:
1. **Zero-PII Token Format:** `tokenized_citizen_id` must be an exact 64-character hexadecimal SHA-256 HMAC string (`min_length=64, max_length=64`). Cleartext phone numbers or raw PII are strictly prohibited.
2. **Input Content Validation (`unprocessed_input_content`):**
   - **General:** Must be a non-empty string between 1 and 5000 characters (`min_length=1, max_length=5000`); validator must reject empty or whitespace-only strings.
   - **When `payload_type == AUDIO`:** Must validate as a valid HTTP/HTTPS URL (`HttpUrl`) pointing to a signed audio recording file.
   - **When `payload_type == TEXT`:** Must be raw user text (max 5000 chars) or a valid USSD DTMF string matching `^\d+(\*\d+)*$`.
3. **BCP 47 Locale Pattern:** `language_locale` must match BCP 47 language format regex `^[a-z]{2}-[A-Z]{2}$` (e.g., `"hi-IN"`). Defaults to `"hi-IN"`.
4. **Cross-Field Structure Level Compatibility Rules:** `structure_level` must be validated by `channel_type`, then `payload_type`:
   - **`WHATSAPP` channel:**
     - If `payload_type == TEXT`: May be `FREE_TEXT` (user-typed message) or `MENU_SELECTION` (button / interactive list selection).
     - If `payload_type == AUDIO`: Must strictly be `FREE_TEXT` (unstructured spoken voice note).
   - **`IVR_VOICE` channel:**
     - `payload_type` is always `AUDIO`: Must strictly be `FREE_TEXT` (unstructured spoken audio recording).
   - **`USSD` channel:**
     - `payload_type` is always `TEXT`: Must strictly be `DTMF_SELECTION` (concatenated keypad digit entries).
   - **`SMS` channel:**
     - `payload_type` is always `TEXT`: Must strictly be `FREE_TEXT` (free-form SMS text).

##### Architectural Design Decisions & Rationale:

1. **Choice of `tokenized_citizen_id` over `tokenized_phone`:**
   - **Design Intent:** `tokenized_citizen_id` represents a **stable, pseudonymous citizen identity token** — not a "tokenized phone". The schema is intentionally agnostic to the underlying PII source. Layer 2 is the only layer that knows what PII source was fed into the HMAC.
   - **Current Derivation (Phone-Sourced Channels):** Computed as `HMAC-SHA256(secret_key, phone_number)` for WhatsApp, IVR, and USSD channels where citizen identity is rooted in MSISDN.
   - **Aadhaar-Sourced Channels & Legal Constraint:** Raw Aadhaar numbers **must never** be directly HMAC'd. The **Aadhaar Act 2016 §29** prohibits storing or hashing raw Aadhaar numbers without UIDAI Authentication User Agency (AUA) registration. For Aadhaar-authenticated channels, Layer 2 must call UIDAI e-KYC/OTP API, obtain the **UIDAI Token UID** (an opaque, AUA-scoped pseudonym), and compute `HMAC-SHA256(secret_key, uidai_token_uid)`.
   - **Other Identity Sources (Voter ID, PAN):** May serve as HMAC input only where lawful purpose and explicit citizen consent exist under the DPDP Act.
2. **Choice & Purpose of `structure_level`:**
   - **Pipeline Routing:** Bypasses SLM entity extraction for `DTMF_SELECTION` (USSD) and `MENU_SELECTION` (WhatsApp buttons), routing directly to deterministic lookup tables while directing `FREE_TEXT` to the Ollama NLU/STT pipeline.
   - **Confidence Baseline:** Automatically assigns `ai_confidence_score = 1.0` for deterministic selections (`DTMF_SELECTION` / `MENU_SELECTION`), whereas `FREE_TEXT` requires dynamic SLM scoring and prompt-injection checks.
3. **Content Representation in `unprocessed_input_content`:**
   - **For `PayloadType.TEXT` (WhatsApp text, USSD, SMS):** Stores the raw text string or concatenated DTMF menu digits (e.g., `"1*2*10"`).
   - **For `PayloadType.AUDIO` (WhatsApp voice notes, IVR calls):** Stores the **signed audio recording URL** (`audio_recording_url` forwarded from Layer 1/2). 
     - *Generation & Ownership:* The signed URL is generated **automatically by the Layer 1/2 backend connector** using service account storage credentials when the audio arrives — the citizen/user does not perform any signing.
     - *Security & Efficiency:* A "signed URL" is a cryptographically signed, time-limited HTTPS link (e.g., valid for 15 minutes) pointing to a private object storage file (S3/GCS/Supabase). This maintains zero-trust security (public storage access is disabled) while keeping JSON payloads lightweight (~150-byte URL string vs. 4.8 MB Base64 payload).

---

### 4.3 Intent & Governance Schemas (`src/models/governance.py`)

Here we define the **Layer 3 $\rightarrow$ Layer 4** Schema:

#### SLM Extracted Entity Payload
```python
class ExtractedEntityPayload(StrictBaseModel):
    application_intent: ApplicationIntent
    ai_confidence_score: float = Field(..., ge=0.0, le=1.0)
    domain_entities: Dict[DomainEntityKey, Any] = Field(default_factory=dict, description="Parsed domain fields keyed by canonical DomainEntityKey")
    is_adversarial_attempt: bool = Field(False, description="Flagged by prompt injection firewall")
    is_structured_menu_bypass: bool = Field(False, description="True for USSD structured menu selections")
```

##### SLM Extracted Entity Specific Validations:
1. **Domain Entities Key Strictness:** `domain_entities` keys must strictly be valid members of `DomainEntityKey` enum (e.g. `district`, `crop_name`, `land_size_acres`). Any uncalibrated key names or hallucinations emitted by the SLM will trigger a Pydantic `ValidationError` and be rejected.
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
