from pydantic import Field, model_validator

from src.models.common import (
    DisbursementStatus,
    DisbursementTxnId,
    StrictBaseModel,
    UtcTimestamp,
)


class DisbursementCallbackPayload(StrictBaseModel):
    """Asynchronous payment status callback from PFMS / NPCI / OpenSPP payment rails."""

    disbursement_txn_id: DisbursementTxnId
    disbursement_status: DisbursementStatus = Field(
        ..., description="Updated financial clearing state: SUCCESS, FAILED, RETURNED"
    )
    cleared_at: UtcTimestamp
    failure_reason_code: str | None = Field(
        None, max_length=256, description="Populated if status is FAILED or RETURNED"
    )

    @model_validator(mode="after")
    def validate_disbursement_callback_fields(self) -> "DisbursementCallbackPayload":
        """Enforces failure reason population rules based on clearing status."""
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

        if (
            self.disbursement_status == DisbursementStatus.SUCCESS
            and self.failure_reason_code is not None
        ):
            raise ValueError("failure_reason_code must be None when disbursement status is SUCCESS")

        return self
