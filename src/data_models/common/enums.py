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
    """Input structure complexity level of incoming citizen payload."""

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
    FINALIZED = "FINALIZED"
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
