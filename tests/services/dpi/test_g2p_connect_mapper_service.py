"""Unit tests for G2pConnectMapperService."""

from datetime import UTC, datetime
from typing import Final

import pytest

from src.data_models.common import (
    DisbursementFailureCode,
    DisbursementStatus,
    EligibilityStatus,
    GovernanceAction,
    RejectionReasonCode,
)
from src.data_models.disbursement import (
    G2pConnectAction,
    G2pConnectHeader,
    G2pConnectOnDisbursePayload,
    G2pConnectOnSearchPayload,
)
from src.data_models.governance import GovernanceOutcomePayload
from src.services.dpi import G2pConnectMapperService

_TEST_SIGNING_KEY: Final[str] = "g2p-connect-test-hmac-key-2026"
_VALID_CITIZEN_TOKEN: Final[str] = "b" * 64


def test_mapper_fails_fast_on_empty_signing_key() -> None:
    """Verifies G2pConnectMapperService rejects empty or whitespace signing keys."""
    with pytest.raises(ValueError, match="signing_key cannot be empty"):
        G2pConnectMapperService(signing_key="   ")


def test_build_registry_search_envelope_signs_and_enforces_zero_pii() -> None:
    """Verifies registry search envelope construction and Zero-PII guard on land_record_id."""
    mapper = G2pConnectMapperService(signing_key=_TEST_SIGNING_KEY)
    envelope = mapper.build_registry_search_envelope(
        session_id="sess-pilot-g2p-001",
        tokenized_citizen_id=_VALID_CITIZEN_TOKEN,
        land_record_id="SURVEY-101-A",
        crop_season="KHARIF-2026",
    )
    assert envelope.header.action == G2pConnectAction.SEARCH
    assert envelope.tokenized_citizen_id == _VALID_CITIZEN_TOKEN
    assert mapper.verify_envelope_signature(
        header=envelope.header,
        transaction_id=envelope.transaction_id,
        subject_reference=f"{_VALID_CITIZEN_TOKEN}:SURVEY-101-A:KHARIF-2026",
        candidate_signature=envelope.signature,
    )

    with pytest.raises(ValueError, match="Zero-PII violation"):
        mapper.build_registry_search_envelope(
            session_id="sess-pilot-g2p-002",
            tokenized_citizen_id=_VALID_CITIZEN_TOKEN,
            land_record_id="+919876543210",
        )


def test_verify_on_search_callback_verifies_signature_and_zero_pii() -> None:
    """Verifies on-search callback signature verification and Zero-PII enforcement."""
    mapper = G2pConnectMapperService(signing_key=_TEST_SIGNING_KEY)
    now = datetime.now(UTC)
    header = G2pConnectHeader(
        message_id="g2p-onsearch-2026-0001",
        message_timestamp=now,
        action=G2pConnectAction.ON_SEARCH,
        sender_id="farmer-registry.agristack.gov.in",
        receiver_id="agristack-dbt-core.gov.in",
    )
    valid_signature = mapper._compute_envelope_signature(
        header=header,
        transaction_id="sess-pilot-g2p-001",
        subject_reference=f"{_VALID_CITIZEN_TOKEN}:SURVEY-101-A:KHARIF-2026:{EligibilityStatus.ELIGIBLE}",
    )
    valid_callback = G2pConnectOnSearchPayload(
        signature=valid_signature,
        header=header,
        transaction_id="sess-pilot-g2p-001",
        tokenized_citizen_id=_VALID_CITIZEN_TOKEN,
        land_record_id="SURVEY-101-A",
        crop_season="KHARIF-2026",
        eligibility_status=EligibilityStatus.ELIGIBLE,
        verified_at=now,
    )
    verified = mapper.verify_on_search_callback(valid_callback)
    assert verified.transaction_id == "sess-pilot-g2p-001"
    assert verified.eligibility_status == EligibilityStatus.ELIGIBLE

    tampered_callback = G2pConnectOnSearchPayload(
        signature="0" * 64,
        header=header,
        transaction_id="sess-pilot-g2p-001",
        tokenized_citizen_id=_VALID_CITIZEN_TOKEN,
        land_record_id="SURVEY-101-A",
        crop_season="KHARIF-2026",
        eligibility_status=EligibilityStatus.ELIGIBLE,
        verified_at=now,
    )
    with pytest.raises(ValueError, match="Invalid G2P Connect on-search envelope signature"):
        mapper.verify_on_search_callback(tampered_callback)

    pii_callback = G2pConnectOnSearchPayload(
        signature=valid_signature,
        header=header,
        transaction_id="sess-pilot-g2p-001",
        tokenized_citizen_id=_VALID_CITIZEN_TOKEN,
        land_record_id="+919876543210",
        crop_season="KHARIF-2026",
        eligibility_status=EligibilityStatus.ELIGIBLE,
        verified_at=now,
    )
    with pytest.raises(ValueError, match="Zero-PII violation"):
        mapper.verify_on_search_callback(pii_callback)


def test_build_disbursement_envelope_maps_approved_outcome() -> None:
    """Verifies approved GovernanceOutcomePayload maps to signed G2P Connect disburse envelope."""
    mapper = G2pConnectMapperService(signing_key=_TEST_SIGNING_KEY)
    approved_outcome = GovernanceOutcomePayload(
        session_id="sess-pilot-g2p-003",
        payload_id="pay-pilot-g2p-003",
        ai_confidence_score=0.94,
        eligibility_status=EligibilityStatus.ELIGIBLE,
        governance_action=GovernanceAction.AUTOMATED_PAYOUT,
        evaluated_at=datetime.now(UTC),
        disbursement_txn_id="TXN-G2P-2026-0003",
        disbursement_status=DisbursementStatus.PENDING,
    )
    envelope = mapper.build_disbursement_envelope(
        outcome=approved_outcome,
        tokenized_citizen_id=_VALID_CITIZEN_TOKEN,
        crop_season="KHARIF-2026",
    )
    assert envelope.header.action == G2pConnectAction.DISBURSE
    assert envelope.transaction_id == "TXN-G2P-2026-0003"
    assert envelope.disbursement_instruction.payee_fa_token == _VALID_CITIZEN_TOKEN
    assert mapper.verify_envelope_signature(
        header=envelope.header,
        transaction_id="TXN-G2P-2026-0003",
        subject_reference=f"{_VALID_CITIZEN_TOKEN}:KHARIF-2026",
        candidate_signature=envelope.signature,
    )


def test_build_disbursement_envelope_rejects_rejected_outcome() -> None:
    """Verifies rejected outcomes cannot produce a G2P Connect disbursement envelope."""
    mapper = G2pConnectMapperService(signing_key=_TEST_SIGNING_KEY)
    rejected_outcome = GovernanceOutcomePayload(
        session_id="sess-pilot-g2p-004",
        payload_id="pay-pilot-g2p-004",
        ai_confidence_score=0.91,
        eligibility_status=EligibilityStatus.INELIGIBLE,
        governance_action=GovernanceAction.AUTO_REJECT,
        evaluated_at=datetime.now(UTC),
        rejection_reason=RejectionReasonCode.LAND_RECORD_NOT_FOUND,
    )
    with pytest.raises(ValueError, match="non-approved action"):
        mapper.build_disbursement_envelope(
            outcome=rejected_outcome,
            tokenized_citizen_id=_VALID_CITIZEN_TOKEN,
        )


def test_parse_on_disburse_callback_verifies_signature_and_rejects_tampering() -> None:
    """Verifies on-disburse callback parsing and timing-safe signature verification."""
    mapper = G2pConnectMapperService(signing_key=_TEST_SIGNING_KEY)
    now = datetime.now(UTC)
    callback_header = G2pConnectHeader(
        message_id="g2p-ondisb-2026-0005",
        message_timestamp=now,
        action=G2pConnectAction.ON_DISBURSE,
        sender_id="payment-bridge.openg2p.gov.in",
        receiver_id="agristack-dbt-core.gov.in",
    )
    valid_signature = mapper._compute_envelope_signature(
        header=callback_header,
        transaction_id="TXN-G2P-2026-0005",
        subject_reference=f"NPCI-UTR-2026-554433:{DisbursementStatus.FAILED}",
    )
    callback_envelope = G2pConnectOnDisbursePayload(
        signature=valid_signature,
        header=callback_header,
        transaction_id="TXN-G2P-2026-0005",
        bank_reference_id="NPCI-UTR-2026-554433",
        disbursement_status=DisbursementStatus.FAILED,
        failure_reason_code=DisbursementFailureCode.ACCOUNT_BLOCKED,
        cleared_at=now,
    )
    parsed_callback = mapper.parse_on_disburse_callback(callback_envelope)
    assert parsed_callback.disbursement_txn_id == "TXN-G2P-2026-0005"
    assert parsed_callback.disbursement_status == DisbursementStatus.FAILED
    assert parsed_callback.failure_reason_code == DisbursementFailureCode.ACCOUNT_BLOCKED

    tampered_envelope = G2pConnectOnDisbursePayload(
        signature="0" * 64,
        header=callback_header,
        transaction_id="TXN-G2P-2026-0005",
        bank_reference_id="NPCI-UTR-2026-554433",
        disbursement_status=DisbursementStatus.SUCCESS,
        cleared_at=now,
    )
    with pytest.raises(ValueError, match="Invalid G2P Connect on-disburse envelope signature"):
        mapper.parse_on_disburse_callback(tampered_envelope)
