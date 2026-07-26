from pydantic import Field, model_validator

from src.models.base import StrictBaseModel
from src.models.enums import DisbursementStatus
from src.models.validators import DisbursementTxnId, UtcTimestamp


class DisbursementCallbackPayload(StrictBaseModel):
    """Asynchronous payment status callback from PFMS / NPCI / OpenSPP payment rails."""

    disbursement_txn_id: DisbursementTxnId
    disbursement_status: DisbursementStatus = Field(
        ..., description="Updated financial clearing state: SUCCESS, FAILED, RETURNED"
    )
    cleared_at_timestamp: UtcTimestamp
    failure_reason_code: str | None = Field(
        None, max_length=256, description="Populated if status is FAILED or RETURNED"
    )

    @model_validator(mode="after")
    def validate_disbursement_callback_fields(self) -> "DisbursementCallbackPayload":
        """Enforces failure reason population rules based on clearing status."""
        terminal_failures = {
            DisbursementStatus.FAILED.value,
            DisbursementStatus.RETURNED.value,
        }
        status_str = str(self.disbursement_status)

        if status_str in terminal_failures and (
            not self.failure_reason_code or not self.failure_reason_code.strip()
        ):
            raise ValueError(
                f"failure_reason_code is required for disbursement status {status_str}"
            )

        if status_str == DisbursementStatus.SUCCESS.value and self.failure_reason_code is not None:
            raise ValueError("failure_reason_code must be None when disbursement status is SUCCESS")

        return self
