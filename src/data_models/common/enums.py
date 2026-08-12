"""Standardized domain enumeration types for inter-layer payload validation."""

from enum import StrEnum


class ChannelType(StrEnum):
    """Originating messaging or telephony communication channel at Layer 1 perimeter."""

    WHATSAPP = "whatsapp"
    IVR_VOICE = "ivr_voice"
    USSD = "ussd"
    SMS = "sms"


class PayloadType(StrEnum):
    """Normalized payload content modality."""

    AUDIO = "audio"
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"


class StructureLevel(StrEnum):
    """Input structure complexity level of incoming citizen interaction or message."""

    FREE_TEXT = "free_text"
    MENU_SELECTION = "menu_selection"
    DTMF_SELECTION = "dtmf_selection"


class ApplicationIntent(StrEnum):
    """Classified citizen intent driving workflow routing."""

    APPLY_SUBSIDY = "apply_subsidy"
    CHECK_STATUS = "check_status"
    SUBMIT_APPEAL = "submit_appeal"
    GRIEVANCE_REDIRECTION = "grievance_redirection"
    UPDATE_CROP_DETAILS = "update_crop_details"
    SCHEME_INQUIRY = "scheme_inquiry"
    UNKNOWN = "unknown"


class EligibilityStatus(StrEnum):
    """Computed citizen scheme eligibility status from DPI registry cross-matching."""

    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class GovernanceAction(StrEnum):
    """Governance routing or adjudication action evaluated by Layer 4 or officer review."""

    AUTOMATED_PAYOUT = "AUTOMATED_PAYOUT"
    AUTO_APPROVE = "AUTO_APPROVE"
    AUTO_REJECT = "AUTO_REJECT"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    ROUTE_FOR_MANUAL_REVIEW = "ROUTE_FOR_MANUAL_REVIEW"
    REQUEST_MORE_INFO = "REQUEST_MORE_INFO"
    MANUAL_APPROVE = "MANUAL_APPROVE"
    MANUAL_REJECT = "MANUAL_REJECT"


class SessionStatus(StrEnum):
    """Lifecycle state of parent citizen communication session."""

    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    TIMEOUT = "TIMEOUT"


class ApplicationStatus(StrEnum):
    """Formal status of citizen claim application in governance ledger."""

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    INFO_REQUESTED = "INFO_REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPEALED = "APPEALED"


class DisbursementStatus(StrEnum):
    """Financial clearing status of benefit disbursement payment.

    Monotonic forward-only lifecycle: PENDING (queued internally) -> INITIATED
    (dispatched to NPCI/PFMS bank rail via step_10) -> SUCCESS / FAILED / RETURNED
    (terminal callback). Backward transitions (e.g. INITIATED -> PENDING) are strictly
    forbidden to prevent double-dipping and duplicate payouts.
    """

    PENDING = "PENDING"
    INITIATED = "INITIATED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETURNED = "RETURNED"


class DomainEntityKey(StrEnum):
    """Canonical domain parameter keys extracted by Small Language Models (SLM)."""

    DISTRICT = "district"
    TALUKA = "taluka"
    VILLAGE = "village"
    CROP_NAME = "crop_name"
    CROP_VARIETY = "crop_variety"
    LAND_SIZE_ACRES = "land_size_acres"
    SUBSIDY_SCHEME_ID = "subsidy_scheme_id"
    SURVEY_NUMBER = "survey_number"
    BANK_ACCOUNT_LAST4 = "bank_account_last4"


class ThreatCategory(StrEnum):
    """Classification categories for detected adversarial prompt injection attacks."""

    SYSTEM_OVERRIDE = "SYSTEM_OVERRIDE"
    ROLE_USURPATION = "ROLE_USURPATION"
    DELIMITER_HIJACKING = "DELIMITER_HIJACKING"
    DATABASE_INJECTION = "DATABASE_INJECTION"
    PAYOUT_MANIPULATION = "PAYOUT_MANIPULATION"


class LanguageLocale(StrEnum):
    """Supported BCP 47 Indic language locales for Bhashini multi-lingual engagement."""

    HINDI = "hi-IN"
    ENGLISH = "en-IN"
    MARATHI = "mr-IN"
    TELUGU = "te-IN"
    TAMIL = "ta-IN"
    GUJARATI = "gu-IN"
    KANNADA = "kn-IN"
    BENGALI = "bn-IN"
    PUNJABI = "pa-IN"
    ODIA = "or-IN"
    MALAYALAM = "ml-IN"


class RejectionReasonCode(StrEnum):
    """Canonical justification codes for automated or manual claim determination rejections."""

    INELIGIBLE_LAND_SIZE = "INELIGIBLE_LAND_SIZE"
    INELIGIBLE_CROP_TYPE = "INELIGIBLE_CROP_TYPE"
    DUPLICATE_CLAIM_ACTIVE_SEASON = "DUPLICATE_CLAIM_ACTIVE_SEASON"
    LAND_RECORD_NOT_FOUND = "LAND_RECORD_NOT_FOUND"
    IDENTITY_NOT_VERIFIED = "IDENTITY_NOT_VERIFIED"
    INSUFFICIENT_DOCUMENTATION = "INSUFFICIENT_DOCUMENTATION"
    POLICY_EXCLUSION = "POLICY_EXCLUSION"
    ADVERSARIAL_ATTEMPT = "ADVERSARIAL_ATTEMPT"
    OTHER = "OTHER"


class EscalationReasonCode(StrEnum):
    """Canonical classification codes for staging claims into caseworker review queues."""

    LOW_AI_CONFIDENCE = "LOW_AI_CONFIDENCE"
    ADVERSARIAL_ATTEMPT_FLAGGED = "ADVERSARIAL_ATTEMPT_FLAGGED"
    MISSING_MANDATORY_ENTITIES = "MISSING_MANDATORY_ENTITIES"
    LAND_RECORD_MISMATCH = "LAND_RECORD_MISMATCH"
    IDENTITY_VERIFICATION_FAILED = "IDENTITY_VERIFICATION_FAILED"
    DOUBLE_DIP_SUSPECTED = "DOUBLE_DIP_SUSPECTED"
    POLICY_REVIEW_REQUIRED = "POLICY_REVIEW_REQUIRED"
    CITIZEN_CLARIFICATION_RECEIVED = "CITIZEN_CLARIFICATION_RECEIVED"


class DisbursementFailureCode(StrEnum):
    """Standardized failure reason codes for national payment clearing rails (NPCI APBS / PFMS)."""

    ACCOUNT_BLOCKED = "ACCOUNT_BLOCKED"
    INVALID_IFSC = "INVALID_IFSC"
    NAME_MISMATCH = "NAME_MISMATCH"
    ERR_INSUFFICIENT_BANK_ACCOUNT_MAPPING = "ERR_INSUFFICIENT_BANK_ACCOUNT_MAPPING"
    ACCOUNT_INACTIVE = "ACCOUNT_INACTIVE"
    AADHAAR_DELINKED = "AADHAAR_DELINKED"
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"
