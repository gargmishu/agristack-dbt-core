"""Standardized domain enumeration types for inter-layer payload validation."""

from enum import StrEnum


class ChannelType(StrEnum):
    """Originating messaging or telephony communication channel at Layer 1 perimeter.

    Identifies the transport network carrier interface (WhatsApp webhook, IVR voice stream,
    USSD signaling, SMS webhook). Governs channel-specific payload parsing, authentication
    rules,
    rate limits, and outbound notification formatting.

    See: decisions/step2.0_canonical_domain_schemas.md (Section 3.2)
    See: decisions/step3.5_adaptive_multichannel_confirmation_delivery.md
    """

    WHATSAPP = "whatsapp"
    IVR_VOICE = "ivr_voice"
    USSD = "ussd"
    SMS = "sms"

    @property
    def is_voice(self) -> bool:
        """Returns True if channel carries telephony voice audio."""
        return self == ChannelType.IVR_VOICE

    @property
    def is_text_only(self) -> bool:
        """Returns True if channel is restricted to plain text messaging (SMS or USSD)."""
        return self in (ChannelType.SMS, ChannelType.USSD)

    @property
    def is_rich_card(self) -> bool:
        """Returns True if channel supports rich markdown cards with formatting (WhatsApp)."""
        return self == ChannelType.WHATSAPP


class PayloadType(StrEnum):
    """Normalized payload content modality.

    Categorizes the sensory/data modality of incoming citizen inputs across the system.
    Determines whether voice pipelines (ASR via Bhashini) or direct text processing is
    invoked.

    Modality Types:
    - `AUDIO`: Telephony voice audio requiring ASR speech-to-text transcription.
    - `TEXT`: Plain or formatted textual messages.
    - `IMAGE`: Photographic uploads (e.g. crop health or identity document).
    - `DOCUMENT`: Structured digital document attachments (e.g. PDF certificates).

    See: decisions/step2.0_canonical_domain_schemas.md (Section 3.2)
    """

    AUDIO = "audio"
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"

    @property
    def is_audio(self) -> bool:
        """Returns True if content is audio modality."""
        return self == PayloadType.AUDIO

    @property
    def is_text(self) -> bool:
        """Returns True if content is text modality."""
        return self == PayloadType.TEXT


class StructureLevel(StrEnum):
    """Input structure complexity level of incoming citizen interaction or message.

    Distinguishes unstructured natural language (`FREE_TEXT`) from structured numeric/menu
    selections (`MENU_SELECTION`, `DTMF_SELECTION`). Enables Layer 3 intake routing to
    bypass
    SLM NLU extraction for structured inputs (saving ~800ms GPU inference latency and
    preventing
    AI hallucinations) while directing free-text to the SLM/NLU extraction pipeline.

    Complexity Levels:
    - `FREE_TEXT`: Unstructured regional language sentences requiring SLM NLU entity
      extraction.
    - `MENU_SELECTION`: Textual menu options (e.g. USSD `1*2*1`) routed via fast-path
      parsers.
    - `DTMF_SELECTION`: Dual-tone multi-frequency digits (e.g. IVR keypad `1#`) routed
      directly.

    See: decisions/step2.0_canonical_domain_schemas.md (Section 4.2)
    """

    FREE_TEXT = "free_text"
    MENU_SELECTION = "menu_selection"
    DTMF_SELECTION = "dtmf_selection"

    @property
    def is_structured(self) -> bool:
        """Returns True if input is a structured menu or DTMF selection."""
        return self in (StructureLevel.MENU_SELECTION, StructureLevel.DTMF_SELECTION)

    @property
    def is_free_text(self) -> bool:
        """Returns True if input is unstructured free-text."""
        return self == StructureLevel.FREE_TEXT


class ApplicationIntent(StrEnum):
    """Classified citizen intent driving workflow routing and state machine gates.

    Represents high-level business goals extracted from citizen interactions, determining
    the target domain handler and orchestration path across Layer 3 and Layer 4.

    Intent Categories:
    - `APPLY_SUBSIDY`: New claim registration for agricultural subsidy or scheme benefit.
    - `CHECK_STATUS`: Inquiry on existing claim or disbursement clearing status.
    - `SUBMIT_APPEAL`: Grievance submission appealing an earlier claim rejection.
    - `GRIEVANCE_REDIRECTION`: Redirection of grievance tickets to external departmental
      desks.
    - `UPDATE_CROP_DETAILS`: Modification of seasonal crop or acreage parameters.
    - `SCHEME_INQUIRY`: Informational queries regarding scheme guidelines and eligibility
      criteria.
    - `UNKNOWN`: Unclassified intent requiring clarification or re-prompting loops.

    See: decisions/step2.0_canonical_domain_schemas.md (Section 3.2)
    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 2.1)
    """

    APPLY_SUBSIDY = "apply_subsidy"
    CHECK_STATUS = "check_status"
    SUBMIT_APPEAL = "submit_appeal"
    GRIEVANCE_REDIRECTION = "grievance_redirection"
    UPDATE_CROP_DETAILS = "update_crop_details"
    SCHEME_INQUIRY = "scheme_inquiry"
    UNKNOWN = "unknown"


class EligibilityStatus(StrEnum):
    """Computed citizen scheme eligibility status from DPI registry cross-matching.

    Represents the authoritative entitlement determination obtained by cross-referencing
    sovereign registries (AgriStack land records, MOSIP/Aadhaar identity, OpenSPP social
    registry).

    Status Values:
    - `PENDING_VERIFICATION`: Registry lookup is in progress or awaiting external DPI
      response.
    - `ELIGIBLE`: Citizen satisfies all landholding, crop entitlement, and social registry
      criteria.
    - `INELIGIBLE`: Citizen fails explicit criteria (e.g. excess acreage, non-notified
      crop).
    - `REQUIRES_REVIEW`: Registry records exhibit discrepancies requiring human caseworker
      verification.

    See: decisions/step3.1_foundational_mock_boundaries.md
    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.1)
    """

    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class GovernanceAction(StrEnum):
    """Governance routing or adjudication action evaluated by Layer 4 or officer review.

    Defines the authoritative routing directive produced at Gate 3 of the orchestration
    pipeline.
    Actions are classified into three semantic groups:
    - Approvals (`AUTO_APPROVE`, `AUTOMATED_PAYOUT`, `MANUAL_APPROVE`): Require valid
      `disbursement_txn_id`
      and initial status `PENDING`.
    - Reviews (`ROUTE_FOR_MANUAL_REVIEW`, `HUMAN_REVIEW`, `REQUEST_MORE_INFO`): Require
      valid
      `escalation_case_id` and caseworker staging.
    - Rejections (`AUTO_REJECT`, `MANUAL_REJECT`): Require valid `rejection_reason_code` and
      explanation.

    See: decisions/step2.0_canonical_domain_schemas.md#governance-outcome-payload
    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.1 & 4.1)
    """

    AUTOMATED_PAYOUT = "AUTOMATED_PAYOUT"
    AUTO_APPROVE = "AUTO_APPROVE"
    AUTO_REJECT = "AUTO_REJECT"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    ROUTE_FOR_MANUAL_REVIEW = "ROUTE_FOR_MANUAL_REVIEW"
    REQUEST_MORE_INFO = "REQUEST_MORE_INFO"
    MANUAL_APPROVE = "MANUAL_APPROVE"
    MANUAL_REJECT = "MANUAL_REJECT"

    @property
    def is_approval(self) -> bool:
        """Returns True if action represents an automated or manual approval."""
        return self in APPROVE_GOVERNANCE_ACTIONS

    @property
    def is_review(self) -> bool:
        """Returns True if action represents an officer or human escalation review."""
        return self in REVIEW_GOVERNANCE_ACTIONS

    @property
    def is_rejection(self) -> bool:
        """Returns True if action represents an automated or manual rejection."""
        return self in REJECT_GOVERNANCE_ACTIONS


APPROVE_GOVERNANCE_ACTIONS: frozenset[GovernanceAction] = frozenset(
    {
        GovernanceAction.AUTO_APPROVE,
        GovernanceAction.AUTOMATED_PAYOUT,
        GovernanceAction.MANUAL_APPROVE,
    }
)

REVIEW_GOVERNANCE_ACTIONS: frozenset[GovernanceAction] = frozenset(
    {
        GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
        GovernanceAction.HUMAN_REVIEW,
    }
)

REJECT_GOVERNANCE_ACTIONS: frozenset[GovernanceAction] = frozenset(
    {
        GovernanceAction.AUTO_REJECT,
        GovernanceAction.MANUAL_REJECT,
    }
)


class SessionStatus(StrEnum):
    """Lifecycle state of parent citizen communication session.

    Tracks active interaction progress across synchronous (IVR, USSD) and asynchronous
    (WhatsApp, SMS) channel sessions.

    Lifecycle States:
    - `ACTIVE`: Citizen is actively interacting with the conversational flow.
    - `PENDING`: Waiting for external asynchronous callbacks or human adjudication.
    - `COMPLETED`: Session successfully reached a terminal outcome.
    - `ABANDONED`: Citizen explicitly dropped or disconnected the session.
    - `TIMEOUT`: Session expired due to inactivity or telephony timeout.

    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 2.1)
    """

    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"
    TIMEOUT = "TIMEOUT"


class ApplicationStatus(StrEnum):
    """Formal status of citizen claim application in governance ledger.

    Represents the persistent state of a claim record throughout its lifecycle from
    initial intake to final clearing or appeal.

    Ledger States:
    - `DRAFT`: Incomplete intake session capturing partial parameters.
    - `SUBMITTED`: Validated intake payload submitted to Layer 4 orchestrator.
    - `UNDER_REVIEW`: Claim staged in caseworker queue for officer adjudication.
    - `INFO_REQUESTED`: Caseworker or orchestrator requested additional citizen information.
    - `APPROVED`: Claim approved for benefit disbursement payout.
    - `REJECTED`: Claim formally rejected with documented determination code.
    - `APPEALED`: Citizen filed an appeal against a rejection determination.

    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 2.1)
    """

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    INFO_REQUESTED = "INFO_REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPEALED = "APPEALED"


class DisbursementStatus(StrEnum):
    """Financial clearing status of benefit disbursement payment.

    Enforces a monotonic forward-only clearing lifecycle:
    `PENDING` (queued internally upon claim approval) -> `INITIATED` (dispatched to
    NPCI/PFMS
    bank rail)
    -> `SUCCESS` / `FAILED` / `RETURNED` (terminal callback receipt).
    Backward transitions (e.g. `INITIATED` -> `PENDING`) are strictly forbidden to prevent
    duplicate payouts and financial double-dipping.

    Clearing States:
    - `PENDING`: Initial state upon approval; queued for clearing dispatch.
    - `INITIATED`: Wire instruction transmitted to sovereign payment rail (NPCI APBS /
      PFMS).
    - `SUCCESS`: Authoritative credit confirmation received via bank callback.
    - `FAILED`: Terminal payment rail clearing failure (e.g. invalid account or IFSC).
    - `RETURNED`: Post-credit reversal or clearing return from beneficiary bank.

    See: decisions/step2.0_canonical_domain_schemas.md (Section 4.5)
    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 4.4)
    """

    PENDING = "PENDING"
    INITIATED = "INITIATED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    RETURNED = "RETURNED"


class DomainEntityKey(StrEnum):
    """Canonical domain parameter keys extracted by Small Language Models (SLM).

    Standardizes schema keys extracted from citizen conversations into typed domain
    attributes:
    - Geographic boundaries: `district`, `taluka`, `village`
    - Agricultural parameters: `crop_name`, `crop_variety`, `land_size_acres`,
      `survey_number`
    - Financial & scheme metadata: `subsidy_scheme_id`, `bank_account_last4`

    See: decisions/step2.0_canonical_domain_schemas.md#slm-extracted-entity-payload
    """

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
    """Classification categories for detected adversarial prompt injection attacks.

    Identifies specific attack vectors neutralized by Layer 2 `AdversarialPromptFirewall`:
    - `SYSTEM_OVERRIDE`: Attempts to bypass instructions via system prompts or escape
      keywords.
    - `ROLE_USURPATION`: Attempts to instruct the AI to adopt an unauthorized administrative
      persona.
    - `DELIMITER_HIJACKING`: Exploitation of special markdown, JSON, or template delimiters.
    - `DATABASE_INJECTION`: SQL / NoSQL / SPARQL query syntax injection vectors.
    - `PAYOUT_MANIPULATION`: Unauthorized manipulation of subsidy amounts, bank accounts, or
      approval flags.

    See: decisions/step3.2_security_and_ingestion_firewalls.md
    """

    SYSTEM_OVERRIDE = "SYSTEM_OVERRIDE"
    ROLE_USURPATION = "ROLE_USURPATION"
    DELIMITER_HIJACKING = "DELIMITER_HIJACKING"
    DATABASE_INJECTION = "DATABASE_INJECTION"
    PAYOUT_MANIPULATION = "PAYOUT_MANIPULATION"


class LanguageLocale(StrEnum):
    """Supported BCP 47 Indic language locales for Bhashini multi-lingual engagement.

    Covers the 11 national and regional languages supported across Indian agricultural
    belts:
    Hindi (`hi-IN`), English (`en-IN`), Marathi (`mr-IN`), Telugu (`te-IN`), Tamil
    (`ta-IN`),
    Gujarati (`gu-IN`), Kannada (`kn-IN`), Bengali (`bn-IN`), Punjabi (`pa-IN`), Odia
    (`or-IN`),
    and Malayalam (`ml-IN`).

    See: decisions/step2.0_canonical_domain_schemas.md
    """

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

    @property
    def is_hindi(self) -> bool:
        """Returns True if this locale is Hindi."""
        return self == LanguageLocale.HINDI


class RejectionReasonCode(StrEnum):
    """Canonical justification codes for automated or manual claim determination rejections.

    Provides standardized, auditable reasons for claim denials:
    - Ineligibility: `INELIGIBLE_LAND_SIZE`, `INELIGIBLE_CROP_TYPE`, `POLICY_EXCLUSION`
    - Integrity & fraud: `DUPLICATE_CLAIM_ACTIVE_SEASON`, `ADVERSARIAL_ATTEMPT`
    - Registry discrepancies: `LAND_RECORD_NOT_FOUND`, `IDENTITY_NOT_VERIFIED`,
      `INSUFFICIENT_DOCUMENTATION`
    - General: `OTHER`

    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.1)
    """

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
    """Canonical classification codes for staging claims into caseworker review queues.

    Categorizes the trigger condition requiring human-in-the-loop adjudication:
    - AI uncertainty: `LOW_AI_CONFIDENCE` (60%-94%), `MISSING_MANDATORY_ENTITIES`
    - Security & anomaly flags: `ADVERSARIAL_ATTEMPT_FLAGGED`, `DOUBLE_DIP_SUSPECTED`
    - Registry mismatches: `LAND_RECORD_MISMATCH`, `IDENTITY_VERIFICATION_FAILED`
    - Administrative: `POLICY_REVIEW_REQUIRED`, `CITIZEN_CLARIFICATION_RECEIVED`

    See: decisions/step2.2_governance_flows_and_state_transitions.md (Section 3.2)
    """

    LOW_AI_CONFIDENCE = "LOW_AI_CONFIDENCE"
    ADVERSARIAL_ATTEMPT_FLAGGED = "ADVERSARIAL_ATTEMPT_FLAGGED"
    MISSING_MANDATORY_ENTITIES = "MISSING_MANDATORY_ENTITIES"
    LAND_RECORD_MISMATCH = "LAND_RECORD_MISMATCH"
    IDENTITY_VERIFICATION_FAILED = "IDENTITY_VERIFICATION_FAILED"
    DOUBLE_DIP_SUSPECTED = "DOUBLE_DIP_SUSPECTED"
    POLICY_REVIEW_REQUIRED = "POLICY_REVIEW_REQUIRED"
    CITIZEN_CLARIFICATION_RECEIVED = "CITIZEN_CLARIFICATION_RECEIVED"


class DisbursementFailureCode(StrEnum):
    """Standardized failure reason codes for national payment clearing rails (NPCI APBS / PFMS).

    Captures bank-level and clearing-house rejection codes during direct benefit transfer:
    - Banking failures: `ACCOUNT_BLOCKED`, `INVALID_IFSC`, `ACCOUNT_INACTIVE`
    - Identity & mapping: `NAME_MISMATCH`, `AADHAAR_DELINKED`,
      `ERR_INSUFFICIENT_BANK_ACCOUNT_MAPPING`
    - Network: `NETWORK_TIMEOUT`

    See: decisions/step2.0_canonical_domain_schemas.md (Section 4.5)
    """

    ACCOUNT_BLOCKED = "ACCOUNT_BLOCKED"
    INVALID_IFSC = "INVALID_IFSC"
    NAME_MISMATCH = "NAME_MISMATCH"
    ERR_INSUFFICIENT_BANK_ACCOUNT_MAPPING = "ERR_INSUFFICIENT_BANK_ACCOUNT_MAPPING"
    ACCOUNT_INACTIVE = "ACCOUNT_INACTIVE"
    AADHAAR_DELINKED = "AADHAAR_DELINKED"
    NETWORK_TIMEOUT = "NETWORK_TIMEOUT"


class NotificationDeliveryStatus(StrEnum):
    """Lifecycle status of outbound multichannel notification dispatch (Step 12).

    Tracks receipt delivery state across communication carriers:
    - `PENDING`: Notification generated and queued for carrier wire transmission.
    - `SENT`: Successfully dispatched to carrier gateway API or SIP voice trunk.
    - `DELIVERED`: Authoritative delivery receipt confirmed by carrier handset callback.
    - `FAILED`: Carrier transmission failure, invalid route, or delivery timeout.

    See: decisions/step3.5_adaptive_multichannel_confirmation_delivery.md
    """

    PENDING = "PENDING"
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
