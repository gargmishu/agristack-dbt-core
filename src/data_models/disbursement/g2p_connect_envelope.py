"""G2P Connect (Digital Convergence Initiative) v1.0.0 interoperability envelope schemas.

Defines standards-compliant request and callback envelopes for federated agricultural
registry verification (`search` / `on-search`) and social benefit disbursement clearing
(`disburse` / `on-disburse`) across OpenG2P, OpenSPP, and PFMS payment bridges.

Why G2P Connect envelopes with HmacCitizenToken?
Standard G2P Connect specifications support tokenized Financial Addresses (FA) and
registry query parameters. By binding `payee_fa_token` and `tokenized_citizen_id` to
`HmacCitizenToken` (64-character SHA-256 HMAC hex digest) and setting
`is_message_encrypted=False` only for Zero-PII pseudonymized tokens, AgriStack DBT Core
achieves plug-and-play DPG Indicator 6/8 interoperability while preserving strict
Zero-PII storage and wire invariants.

See: decisions/step2.0_canonical_domain_schemas.md (Section 4.5)
See: decisions/step2.3_governance_flows_and_state_transitions.md (Section 4.4)
See: docs/dpg_standard_compliance.md (Indicator 8: Adherence to Standards & Best Practices)
"""

from enum import StrEnum

from pydantic import Field, model_validator

from src.data_models.common import (
    APPROVE_GOVERNANCE_ACTIONS,
    ChannelMessageId,
    CropSeason,
    DisbursementFailureCode,
    DisbursementStatus,
    DisbursementTxnId,
    ExtractionPayloadId,
    GovernanceAction,
    HmacCitizenToken,
    SessionId,
    StrictBaseModel,
    UtcTimestamp,
)

__all__ = [
    "G2pConnectAction",
    "G2pConnectDisbursementEnvelope",
    "G2pConnectDisbursementInstruction",
    "G2pConnectHeader",
    "G2pConnectOnDisbursePayload",
    "G2pConnectRegistrySearchEnvelope",
]


class G2pConnectAction(StrEnum):
    """Standard G2P Connect (DCI) asynchronous RPC action verbs.

    See: decisions/step2.0_canonical_domain_schemas.md (Section 4.5)
    """

    SEARCH = "search"
    ON_SEARCH = "on-search"
    DISBURSE = "disburse"
    ON_DISBURSE = "on-disburse"


class G2pConnectHeader(StrictBaseModel):
    """Canonical G2P Connect v1.0.0 message routing and telemetry header.

    Invariants:
    - `version` must follow semantic versioning (`X.Y.Z`).
    - `sender_id` and `receiver_id` must identify distinct DPI participants.

    See: decisions/step2.0_canonical_domain_schemas.md (Section 4.5)
    """

    version: str = Field(
        default="1.0.0",
        min_length=5,
        max_length=16,
        pattern=r"^\d+\.\d+\.\d+$",
        description="G2P Connect / DCI protocol semantic version (e.g. 1.0.0)",
    )
    message_id: ChannelMessageId
    message_timestamp: UtcTimestamp
    action: G2pConnectAction
    sender_id: str = Field(
        ...,
        min_length=3,
        max_length=128,
        description="Originating DPI participant domain identifier",
    )
    receiver_id: str = Field(
        ...,
        min_length=3,
        max_length=128,
        description="Target DPI registry or payment bridge identifier (e.g. openg2p-bridge.gov.in)",
    )
    total_count: int = Field(
        default=1,
        ge=1,
        le=1000,
        description="Total instruction records encapsulated within the message body",
    )
    is_message_encrypted: bool = Field(
        default=False,
        description="Payload encryption flag; False when carrying Zero-PII SHA-256 HMAC tokens",
    )

    @model_validator(mode="after")
    def validate_distinct_participants(self) -> "G2pConnectHeader":
        """Prevents loopback routing by ensuring sender and receiver identifiers differ."""
        if self.sender_id.lower() == self.receiver_id.lower():
            raise ValueError("sender_id and receiver_id must identify distinct DPI participants")
        return self


class G2pConnectDisbursementInstruction(StrictBaseModel):
    """Single benefit disbursement instruction inside a G2P Connect `disburse` envelope.

    Invariants:
    - `payee_fa_token` is strictly a 64-character SHA-256 HMAC token (`HmacCitizenToken`).
    - `governance_action` must belong to `APPROVE_GOVERNANCE_ACTIONS`.

    See: decisions/step2.3_governance_flows_and_state_transitions.md (Section 4.1)
    """

    reference_id: DisbursementTxnId
    session_id: SessionId
    payload_id: ExtractionPayloadId
    payee_fa_token: HmacCitizenToken
    scheme_code: CropSeason
    governance_action: GovernanceAction
    instructed_at: UtcTimestamp

    @model_validator(mode="after")
    def validate_approved_governance_action(self) -> "G2pConnectDisbursementInstruction":
        """Enforces that only approved governance verdicts generate disbursement instructions."""
        if self.governance_action not in APPROVE_GOVERNANCE_ACTIONS:
            raise ValueError(
                "G2P Connect disbursement instruction requires an approved governance action; "
                f"received {self.governance_action}"
            )
        return self


class G2pConnectDisbursementEnvelope(StrictBaseModel):
    """Signed G2P Connect v1.0.0 `disburse` request envelope for OpenG2P / PFMS clearing rails.

    See: decisions/step2.0_canonical_domain_schemas.md (Section 4.5)
    """

    signature: str = Field(
        ...,
        min_length=64,
        max_length=256,
        description="HMAC-SHA256 integrity signature over canonical header and instruction",
    )
    header: G2pConnectHeader
    transaction_id: DisbursementTxnId
    disbursement_instruction: G2pConnectDisbursementInstruction

    @model_validator(mode="after")
    def validate_disburse_envelope_alignment(self) -> "G2pConnectDisbursementEnvelope":
        """Enforces `disburse` header action and correlation key alignment."""
        if self.header.action != G2pConnectAction.DISBURSE:
            raise ValueError(
                "G2pConnectDisbursementEnvelope requires header.action='disburse'; "
                f"received '{self.header.action}'"
            )
        if self.transaction_id != self.disbursement_instruction.reference_id:
            raise ValueError(
                "transaction_id must match disbursement_instruction.reference_id for "
                "idempotent G2P Connect reconciliation"
            )
        return self


class G2pConnectOnDisbursePayload(StrictBaseModel):
    """Signed G2P Connect v1.0.0 `on-disburse` asynchronous clearing status callback envelope.

    See: decisions/step2.3_governance_flows_and_state_transitions.md (Section 4.4)
    """

    signature: str = Field(
        ...,
        min_length=64,
        max_length=256,
        description="HMAC-SHA256 integrity signature from OpenG2P / PFMS payment hub",
    )
    header: G2pConnectHeader
    transaction_id: DisbursementTxnId
    bank_reference_id: str = Field(
        ...,
        min_length=5,
        max_length=64,
        description="External banking UTR or clearing reference generated by payment rail",
    )
    disbursement_status: DisbursementStatus
    cleared_at: UtcTimestamp
    failure_reason_code: DisbursementFailureCode | None = Field(
        default=None,
        description="Populated when disbursement_status is FAILED or RETURNED",
    )

    @model_validator(mode="after")
    def validate_on_disburse_header_action(self) -> "G2pConnectOnDisbursePayload":
        """Enforces that callback envelope carries `on-disburse` header action."""
        if self.header.action != G2pConnectAction.ON_DISBURSE:
            raise ValueError(
                "G2pConnectOnDisbursePayload requires header.action='on-disburse'; "
                f"received '{self.header.action}'"
            )
        return self


class G2pConnectRegistrySearchEnvelope(StrictBaseModel):
    """Signed G2P Connect v1.0.0 `search` envelope for Federated Farmer Registry verification.

    See: decisions/step2.0_canonical_domain_schemas.md (Section 4.3)
    """

    signature: str = Field(
        ...,
        min_length=64,
        max_length=256,
        description="HMAC-SHA256 integrity signature over canonical search header and criteria",
    )
    header: G2pConnectHeader
    transaction_id: SessionId
    tokenized_citizen_id: HmacCitizenToken
    land_record_id: str = Field(
        ...,
        min_length=3,
        max_length=64,
        description="Cadastral survey or land parcel identifier",
    )
    crop_season: CropSeason
    registry_type: str = Field(
        default="ns:org:RegistryType:Agriculture",
        min_length=3,
        max_length=128,
        description="G2P Connect / DCI registry namespace URI",
    )

    @model_validator(mode="after")
    def validate_search_header_action(self) -> "G2pConnectRegistrySearchEnvelope":
        """Enforces that registry verification envelope carries `search` header action."""
        if self.header.action != G2pConnectAction.SEARCH:
            raise ValueError(
                "G2pConnectRegistrySearchEnvelope requires header.action='search'; "
                f"received '{self.header.action}'"
            )
        return self
