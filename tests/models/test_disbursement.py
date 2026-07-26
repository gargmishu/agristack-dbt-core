from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.models.disbursement import DisbursementCallbackPayload
from src.models.enums import DisbursementStatus


def test_disbursement_callback_success() -> None:
    payload = DisbursementCallbackPayload(
        disbursement_txn_id="TXN-2026-987654",
        disbursement_status=DisbursementStatus.SUCCESS,
        cleared_at_timestamp=datetime.now(UTC),
    )
    assert payload.disbursement_status == DisbursementStatus.SUCCESS
    assert payload.failure_reason_code is None


def test_disbursement_callback_failed_missing_reason() -> None:
    with pytest.raises(ValidationError) as exc:
        DisbursementCallbackPayload(
            disbursement_txn_id="TXN-2026-987654",
            disbursement_status=DisbursementStatus.FAILED,
            cleared_at_timestamp=datetime.now(UTC),
        )
    assert "failure_reason_code is required" in str(exc.value)
