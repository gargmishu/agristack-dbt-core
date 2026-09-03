from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.data_models.common import DisbursementFailureCode, DisbursementStatus
from src.data_models.disbursement import DisbursementCallbackPayload


def test_disbursement_callback_success() -> None:
    payload = DisbursementCallbackPayload(
        disbursement_txn_id="TXN-2026-987654",
        bank_reference_id="NPCI-UTR-2026-88776655",
        disbursement_status=DisbursementStatus.SUCCESS,
        cleared_at=datetime.now(UTC),
    )
    assert payload.disbursement_status == DisbursementStatus.SUCCESS
    assert payload.bank_reference_id == "NPCI-UTR-2026-88776655"
    assert payload.failure_reason_code is None


def test_disbursement_callback_failed() -> None:
    payload = DisbursementCallbackPayload(
        disbursement_txn_id="TXN-2026-987654",
        bank_reference_id="NPCI-UTR-2026-88776655",
        disbursement_status=DisbursementStatus.FAILED,
        failure_reason_code=DisbursementFailureCode.INVALID_IFSC,
        cleared_at=datetime.now(UTC),
    )
    assert payload.disbursement_status == DisbursementStatus.FAILED
    assert payload.bank_reference_id == "NPCI-UTR-2026-88776655"
    assert payload.failure_reason_code == DisbursementFailureCode.INVALID_IFSC


def test_disbursement_callback_missing_bank_reference_id_fails() -> None:
    with pytest.raises(ValidationError, match="Field required"):
        DisbursementCallbackPayload(  # type: ignore[call-arg]
            disbursement_txn_id="TXN-2026-987654",
            disbursement_status=DisbursementStatus.SUCCESS,
            cleared_at=datetime.now(UTC),
        )


def test_disbursement_callback_failed_missing_reason() -> None:
    with pytest.raises(ValidationError, match="failure_reason_code is required"):
        DisbursementCallbackPayload(
            disbursement_txn_id="TXN-2026-987654",
            bank_reference_id="NPCI-UTR-2026-88776655",
            disbursement_status=DisbursementStatus.FAILED,
            cleared_at=datetime.now(UTC),
        )


def test_disbursement_callback_success_with_failure_reason_fails() -> None:
    with pytest.raises(ValidationError, match="failure_reason_code must be None"):
        DisbursementCallbackPayload(
            disbursement_txn_id="TXN-2026-987654",
            bank_reference_id="NPCI-UTR-2026-88776655",
            disbursement_status=DisbursementStatus.SUCCESS,
            failure_reason_code=DisbursementFailureCode.INVALID_IFSC,
            cleared_at=datetime.now(UTC),
        )
