from enum import StrEnum


class ChannelType(StrEnum):
    WHATSAPP = "whatsapp"
    IVR_VOICE = "ivr_voice"
    USSD = "ussd"
    SMS = "sms"


class PayloadType(StrEnum):
    AUDIO = "audio"
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"


class StructureLevel(StrEnum):
    FREE_TEXT = "free_text"
    MENU_SELECTION = "menu_selection"
    DTMF_SELECTION = "dtmf_selection"


class ApplicationIntent(StrEnum):
    APPLY_SUBSIDY = "apply_subsidy"
    CHECK_STATUS = "check_status"
    SUBMIT_APPEAL = "submit_appeal"
    GRIEVANCE_REDIRECTION = "grievance_redirection"
    UPDATE_CROP_DETAILS = "update_crop_details"
    SCHEME_INQUIRY = "scheme_inquiry"
    UNKNOWN = "unknown"


class EligibilityStatus(StrEnum):
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class GovernanceDecision(StrEnum):
    AUTOMATED_PAYOUT = "AUTOMATED_PAYOUT"
    AUTO_APPROVE = "AUTO_APPROVE"
    AUTO_REJECT = "AUTO_REJECT"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    ROUTE_FOR_MANUAL_REVIEW = "ROUTE_FOR_MANUAL_REVIEW"
    REQUEST_MORE_INFO = "REQUEST_MORE_INFO"
    MANUAL_APPROVE = "MANUAL_APPROVE"
    MANUAL_REJECT = "MANUAL_REJECT"


class SessionStatus(StrEnum):
    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    TIMEOUT = "TIMEOUT"


class ApplicationStatus(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    FINALIZED = "FINALIZED"
    REJECTED = "REJECTED"
    APPEALED = "APPEALED"


class DisbursementStatus(StrEnum):
    PENDING = "PENDING"
    INITIATED = "INITIATED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETURNED = "RETURNED"


class DomainEntityKey(StrEnum):
    DISTRICT = "district"
    TALUKA = "taluka"
    VILLAGE = "village"
    CROP_NAME = "crop_name"
    CROP_VARIETY = "crop_variety"
    LAND_SIZE_ACRES = "land_size_acres"
    SUBSIDY_SCHEME_ID = "subsidy_scheme_id"
    SURVEY_NUMBER = "survey_number"
    BANK_ACCOUNT_LAST4 = "bank_account_last4"
