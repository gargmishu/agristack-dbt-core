from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from src.data_models.caseworker import CaseworkerReviewOutcomePayload
from src.data_models.common import GovernanceAction, RejectionReasonCode


def test_caseworker_review_outcome_valid_approve() -> None:
    payload = CaseworkerReviewOutcomePayload(
        escalation_case_id="SPP-CASE-2026-981245",
        reviewer_id="OFFICER-991",
        governance_action=GovernanceAction.MANUAL_APPROVE,
        review_notes="Verified land record document manually",
        approved_amount=5000.0,  # noqa: PLR2004
        reviewed_at=datetime.now(UTC),
    )
    assert payload.governance_action == GovernanceAction.MANUAL_APPROVE
    assert payload.approved_amount == 5000.0  # noqa: PLR2004


def test_caseworker_review_outcome_valid_request_more_info() -> None:
    payload = CaseworkerReviewOutcomePayload(
        escalation_case_id="SPP-CASE-2026-981245",
        reviewer_id="OFFICER-991",
        governance_action=GovernanceAction.REQUEST_MORE_INFO,
        review_notes="Please upload a clearer scan of the land deed document",
        reviewed_at=datetime.now(UTC),
    )
    assert payload.governance_action == GovernanceAction.REQUEST_MORE_INFO
    assert payload.approved_amount is None
    assert payload.rejection_reason is None


def test_caseworker_review_outcome_invalid_type() -> None:
    with pytest.raises(ValidationError) as exception_info:
        CaseworkerReviewOutcomePayload(
            escalation_case_id="SPP-CASE-2026-981245",
            reviewer_id="OFFICER-991",
            governance_action=GovernanceAction.AUTO_APPROVE,  # Automated action not permitted
            review_notes="Notes",
            approved_amount=5000.0,  # noqa: PLR2004
            reviewed_at=datetime.now(UTC),
        )
    assert "must be MANUAL_APPROVE, MANUAL_REJECT, or REQUEST_MORE_INFO" in str(
        exception_info.value
    )


def test_caseworker_review_outcome_empty_review_notes() -> None:
    with pytest.raises(ValidationError) as exception_info:
        CaseworkerReviewOutcomePayload(
            escalation_case_id="SPP-CASE-2026-981245",
            reviewer_id="OFFICER-991",
            governance_action=GovernanceAction.MANUAL_APPROVE,
            review_notes="      ",  # 6 spaces
            approved_amount=5000.0,  # noqa: PLR2004
            reviewed_at=datetime.now(UTC),
        )
    assert "String should have at least 5 characters" in str(exception_info.value)


def test_caseworker_review_outcome_valid_reject() -> None:
    payload = CaseworkerReviewOutcomePayload(
        escalation_case_id="SPP-CASE-2026-981245",
        reviewer_id="OFFICER-991",
        governance_action=GovernanceAction.MANUAL_REJECT,
        review_notes="Ineligible under current land parcel rules",
        rejection_reason=RejectionReasonCode.INELIGIBLE_LAND_SIZE,
        reviewed_at=datetime.now(UTC),
    )
    assert payload.governance_action == GovernanceAction.MANUAL_REJECT
    assert payload.rejection_reason == RejectionReasonCode.INELIGIBLE_LAND_SIZE
    assert payload.approved_amount is None


def test_caseworker_review_outcome_approve_missing_amount() -> None:
    with pytest.raises(ValidationError, match="approved_amount > 0.0 is required"):
        CaseworkerReviewOutcomePayload(
            escalation_case_id="SPP-CASE-2026-981245",
            reviewer_id="OFFICER-991",
            governance_action=GovernanceAction.MANUAL_APPROVE,
            review_notes="Approved after manual re-verification of land deed",
            approved_amount=None,
            reviewed_at=datetime.now(UTC),
        )

    with pytest.raises(ValidationError, match="approved_amount > 0.0 is required"):
        CaseworkerReviewOutcomePayload(
            escalation_case_id="SPP-CASE-2026-981245",
            reviewer_id="OFFICER-991",
            governance_action=GovernanceAction.MANUAL_APPROVE,
            review_notes="Approved after manual re-verification of land deed",
            approved_amount=0.0,
            reviewed_at=datetime.now(UTC),
        )


def test_caseworker_review_outcome_approve_with_rejection_reason_fails() -> None:
    with pytest.raises(ValidationError) as exception_info:
        CaseworkerReviewOutcomePayload(
            escalation_case_id="SPP-CASE-2026-981245",
            reviewer_id="OFFICER-991",
            governance_action=GovernanceAction.MANUAL_APPROVE,
            review_notes="Approved after manual re-verification of land deed",
            approved_amount=5000.0,  # noqa: PLR2004
            rejection_reason=RejectionReasonCode.LAND_RECORD_NOT_FOUND,
            reviewed_at=datetime.now(UTC),
        )
    assert "rejection_reason must be None for MANUAL_APPROVE" in str(exception_info.value)


def test_caseworker_review_outcome_reject_missing_rejection_reason() -> None:
    with pytest.raises(ValidationError, match="rejection_reason is required for MANUAL_REJECT"):
        CaseworkerReviewOutcomePayload(
            escalation_case_id="SPP-CASE-2026-981245",
            reviewer_id="OFFICER-991",
            governance_action=GovernanceAction.MANUAL_REJECT,
            review_notes="Rejected due to invalid cadastral survey match",
            rejection_reason=None,
            reviewed_at=datetime.now(UTC),
        )


def test_caseworker_review_outcome_reject_with_approved_amount_fails() -> None:
    with pytest.raises(ValidationError) as exception_info:
        CaseworkerReviewOutcomePayload(
            escalation_case_id="SPP-CASE-2026-981245",
            reviewer_id="OFFICER-991",
            governance_action=GovernanceAction.MANUAL_REJECT,
            review_notes="Rejected due to invalid cadastral survey match",
            approved_amount=5000.0,  # noqa: PLR2004
            rejection_reason=RejectionReasonCode.LAND_RECORD_NOT_FOUND,
            reviewed_at=datetime.now(UTC),
        )
    assert "approved_amount must be None for MANUAL_REJECT" in str(exception_info.value)


def test_caseworker_review_outcome_request_info_with_terminal_fields_fails() -> None:
    with pytest.raises(ValidationError) as exception_info:
        CaseworkerReviewOutcomePayload(
            escalation_case_id="SPP-CASE-2026-981245",
            reviewer_id="OFFICER-991",
            governance_action=GovernanceAction.REQUEST_MORE_INFO,
            review_notes="Please upload a higher resolution photograph of the passbook",
            approved_amount=1000.0,  # noqa: PLR2004
            reviewed_at=datetime.now(UTC),
        )
    assert "approved_amount must be None for REQUEST_MORE_INFO" in str(exception_info.value)

    with pytest.raises(
        ValidationError,
        match="rejection_reason must be None for REQUEST_MORE_INFO",
    ):
        CaseworkerReviewOutcomePayload(
            escalation_case_id="SPP-CASE-2026-981245",
            reviewer_id="OFFICER-991",
            governance_action=GovernanceAction.REQUEST_MORE_INFO,
            review_notes="Please upload a higher resolution photograph of the passbook",
            rejection_reason=RejectionReasonCode.LAND_RECORD_NOT_FOUND,
            reviewed_at=datetime.now(UTC),
        )
