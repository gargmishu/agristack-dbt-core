"""Asynchronous payment rail clearing status callback schema."""

from pydantic import Field, model_validator

from src.data_models.common import (
    DisbursementStatus,
    DisbursementTxnId,
    StrictBaseModel,
    UtcTimestamp,
)


class DisbursementCallbackPayload(StrictBaseModel):
    """Asynchronous payment status callback from PFMS / NPCI / OpenSPP payment rails.

    See: decisions/step2.0_canonical_domain_schemas.md (Section 4.5)
    """

    disbursement_txn_id: DisbursementTxnId = Field(
        ...,
        description="Unique idempotency transaction ID matching Layer 4 approval key",
    )
    disbursement_status: DisbursementStatus = Field(
        ..., description="Updated financial clearing state: SUCCESS, FAILED, RETURNED"
    )
    cleared_at: UtcTimestamp = Field(
        ...,
        description="UTC timestamp when sovereign payment rail cleared or errored transaction",
    )
    failure_reason_code: str | None = Field(
        None, max_length=256, description="Populated if status is FAILED or RETURNED"
    )

    @model_validator(mode="after")
    def validate_terminal_failure_reason(self) -> "DisbursementCallbackPayload":
        """Enforces mandatory failure justification when financial clearing fails or returns.

        Why require failure_reason_code?
        When APBS or PFMS bank clearing fails (e.g., INVALID_IFSC or ACCOUNT_BLOCKED), the system
        must capture explicit error codes to trigger citizen re-notification and automated
        conversational correction loops without human caseworker intervention.
        """
        terminal_failures = {
            DisbursementStatus.FAILED,
            DisbursementStatus.RETURNED,
        }
        if self.disbursement_status in terminal_failures and (
            not self.failure_reason_code or not self.failure_reason_code.strip()
        ):
            raise ValueError(
                "failure_reason_code is required for disbursement status "
                f"{self.disbursement_status}"
            )
        return self

    @model_validator(mode="after")
    def validate_success_reason_exclusion(self) -> "DisbursementCallbackPayload":
        """Enforces that failure codes remain absent upon successful financial clearing.

        Why forbid failure_reason_code on SUCCESS?
        To uphold strict financial invariants, an approved and cleared payout must never carry
        error telemetry. Rejecting contradictory states prevents downstream audit confusion.
        """
        if (
            self.disbursement_status == DisbursementStatus.SUCCESS
            and self.failure_reason_code is not None
        ):
            raise ValueError("failure_reason_code must be None when disbursement status is SUCCESS")
        return self
