"""Unit tests for G2P Connect (DCI) v1.0.0 interoperability envelope schemas."""

from datetime import UTC, datetime
from typing import Final

import pytest
from pydantic import ValidationError

from src.data_models.common import (
    APPROVE_GOVERNANCE_ACTIONS,
    REJECT_GOVERNANCE_ACTIONS,
    REVIEW_GOVERNANCE_ACTIONS,
    DisbursementFailureCode,
    DisbursementStatus,
    EligibilityStatus,
    GovernanceAction,
)
from src.data_models.disbursement import (
    G2pConnectAction,
    G2pConnectDisbursementEnvelope,
    G2pConnectDisbursementInstruction,
    G2pConnectHeader,
    G2pConnectOnDisbursePayload,
    G2pConnectOnSearchPayload,
    G2pConnectRegistrySearchEnvelope,
)

_VALID_CITIZEN_TOKEN: Final[str] = "a" * 64
_VALID_SIGNATURE: Final[str] = "f" * 64


@pytest.mark.parametrize("action", list(G2pConnectAction))
def test_g2p_connect_header_accepts_all_actions(action: G2pConnectAction) -> None:
    """Verifies G2pConnectHeader accepts all standardized G2P Connect actions."""
    header = G2pConnectHeader(
        message_id="g2p-msg-2026-0001",
        message_timestamp=datetime.now(UTC),
        action=action,
        sender_id="agristack-dbt-core.gov.in",
        receiver_id="openg2p-bridge.gov.in",
    )
    assert header.action == action
    assert header.version == "1.0.0"
    assert header.is_message_encrypted is False


def test_g2p_connect_header_rejects_identical_sender_and_receiver() -> None:
    """Verifies loopback routing is rejected when sender_id equals receiver_id."""
    with pytest.raises(ValidationError, match="distinct DPI participants"):
        G2pConnectHeader(
            message_id="g2p-msg-2026-0001",
            message_timestamp=datetime.now(UTC),
            action=G2pConnectAction.DISBURSE,
            sender_id="agristack-dbt-core.gov.in",
            receiver_id="AGRISTACK-DBT-CORE.GOV.IN",
        )


@pytest.mark.parametrize("approve_action", sorted(APPROVE_GOVERNANCE_ACTIONS))
def test_disbursement_instruction_accepts_approved_actions(
    approve_action: GovernanceAction,
) -> None:
    """Verifies G2pConnectDisbursementInstruction accepts all approve governance actions."""
    instruction = G2pConnectDisbursementInstruction(
        reference_id="TXN-2026-100001",
        session_id="sess-2026-100001",
        payload_id="pay-2026-100001",
        payee_fa_token=_VALID_CITIZEN_TOKEN,
        scheme_code="KHARIF-2026",
        governance_action=approve_action,
        instructed_at=datetime.now(UTC),
    )
    assert instruction.governance_action == approve_action
    assert instruction.payee_fa_token == _VALID_CITIZEN_TOKEN


@pytest.mark.parametrize(
    "non_approve_action",
    sorted(REJECT_GOVERNANCE_ACTIONS | REVIEW_GOVERNANCE_ACTIONS),
)
def test_disbursement_instruction_rejects_non_approved_actions(
    non_approve_action: GovernanceAction,
) -> None:
    """Verifies non-approved governance actions cannot generate disbursement instructions."""
    with pytest.raises(ValidationError, match="requires an approved governance action"):
        G2pConnectDisbursementInstruction(
            reference_id="TXN-2026-100001",
            session_id="sess-2026-100001",
            payload_id="pay-2026-100001",
            payee_fa_token=_VALID_CITIZEN_TOKEN,
            scheme_code="KHARIF-2026",
            governance_action=non_approve_action,
            instructed_at=datetime.now(UTC),
        )


def test_disbursement_envelope_validates_action_and_transaction_alignment() -> None:
    """Verifies G2pConnectDisbursementEnvelope enforces header action and reference match."""
    now = datetime.now(UTC)
    instruction = G2pConnectDisbursementInstruction(
        reference_id="TXN-2026-100001",
        session_id="sess-2026-100001",
        payload_id="pay-2026-100001",
        payee_fa_token=_VALID_CITIZEN_TOKEN,
        scheme_code="KHARIF-2026",
        governance_action=GovernanceAction.AUTOMATED_PAYOUT,
        instructed_at=now,
    )
    valid_header = G2pConnectHeader(
        message_id="g2p-disb-2026-0001",
        message_timestamp=now,
        action=G2pConnectAction.DISBURSE,
        sender_id="agristack-dbt-core.gov.in",
        receiver_id="payment-bridge.openg2p.gov.in",
    )
    envelope = G2pConnectDisbursementEnvelope(
        signature=_VALID_SIGNATURE,
        header=valid_header,
        transaction_id="TXN-2026-100001",
        disbursement_instruction=instruction,
    )
    assert envelope.transaction_id == "TXN-2026-100001"

    with pytest.raises(ValidationError, match="must match disbursement_instruction.reference_id"):
        G2pConnectDisbursementEnvelope(
            signature=_VALID_SIGNATURE,
            header=valid_header,
            transaction_id="TXN-2026-MISMATCH",
            disbursement_instruction=instruction,
        )


def test_on_disburse_payload_and_registry_search_envelope_enforce_actions() -> None:
    """Verifies on-disburse and registry search envelopes reject mismatched header actions."""
    now = datetime.now(UTC)
    search_header = G2pConnectHeader(
        message_id="g2p-search-2026-0001",
        message_timestamp=now,
        action=G2pConnectAction.SEARCH,
        sender_id="agristack-dbt-core.gov.in",
        receiver_id="farmer-registry.agristack.gov.in",
    )
    search_envelope = G2pConnectRegistrySearchEnvelope(
        signature=_VALID_SIGNATURE,
        header=search_header,
        transaction_id="sess-2026-100001",
        tokenized_citizen_id=_VALID_CITIZEN_TOKEN,
        land_record_id="SURVEY-101-A",
        crop_season="KHARIF-2026",
    )
    assert search_envelope.header.action == G2pConnectAction.SEARCH

    with pytest.raises(ValidationError, match="requires header.action='on-disburse'"):
        G2pConnectOnDisbursePayload(
            signature=_VALID_SIGNATURE,
            header=search_header,
            transaction_id="TXN-2026-100001",
            bank_reference_id="NPCI-UTR-2026-998877",
            disbursement_status=DisbursementStatus.FAILED,
            failure_reason_code=DisbursementFailureCode.INVALID_IFSC,
            cleared_at=now,
        )


def test_on_search_payload_enforces_action_and_zero_pii_token() -> None:
    """Verifies G2pConnectOnSearchPayload accepts on-search and rejects mismatched actions."""
    now = datetime.now(UTC)
    on_search_header = G2pConnectHeader(
        message_id="g2p-onsearch-2026-0001",
        message_timestamp=now,
        action=G2pConnectAction.ON_SEARCH,
        sender_id="farmer-registry.agristack.gov.in",
        receiver_id="agristack-dbt-core.gov.in",
    )
    on_search_payload = G2pConnectOnSearchPayload(
        signature=_VALID_SIGNATURE,
        header=on_search_header,
        transaction_id="sess-2026-100001",
        tokenized_citizen_id=_VALID_CITIZEN_TOKEN,
        land_record_id="SURVEY-101-A",
        crop_season="KHARIF-2026",
        eligibility_status=EligibilityStatus.ELIGIBLE,
        verified_at=now,
    )
    assert on_search_payload.header.action == G2pConnectAction.ON_SEARCH
    assert on_search_payload.eligibility_status == EligibilityStatus.ELIGIBLE

    mismatched_header = G2pConnectHeader(
        message_id="g2p-onsearch-2026-0002",
        message_timestamp=now,
        action=G2pConnectAction.SEARCH,
        sender_id="farmer-registry.agristack.gov.in",
        receiver_id="agristack-dbt-core.gov.in",
    )
    with pytest.raises(ValidationError, match="requires header.action='on-search'"):
        G2pConnectOnSearchPayload(
            signature=_VALID_SIGNATURE,
            header=mismatched_header,
            transaction_id="sess-2026-100001",
            tokenized_citizen_id=_VALID_CITIZEN_TOKEN,
            land_record_id="SURVEY-101-A",
            crop_season="KHARIF-2026",
            eligibility_status=EligibilityStatus.ELIGIBLE,
            verified_at=now,
        )
