from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.data_models.common import DisbursementStatus
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


def test_disbursement_callback_success_missing_bank_ref_fails() -> None:
    with pytest.raises(ValidationError) as exc:
        DisbursementCallbackPayload(
            disbursement_txn_id="TXN-2026-987654",
            bank_reference_id=None,
            disbursement_status=DisbursementStatus.SUCCESS,
            cleared_at=datetime.now(UTC),
        )
    assert "bank_reference_id (UTR) is required when" in str(exc.value)


def test_disbursement_callback_failed_missing_reason() -> None:
    with pytest.raises(ValidationError) as exc:
        DisbursementCallbackPayload(
            disbursement_txn_id="TXN-2026-987654",
            disbursement_status=DisbursementStatus.FAILED,
            cleared_at=datetime.now(UTC),
        )
    assert "failure_reason_code is required" in str(exc.value)
