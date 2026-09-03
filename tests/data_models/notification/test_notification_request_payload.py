"""Unit tests for NotificationRequestPayload domain schema."""

import pytest
from pydantic import ValidationError

from src.data_models.common import (
    ChannelType,
    DomainEntityKey,
    GovernanceAction,
    LanguageLocale,
    RejectionReasonCode,
)
from src.data_models.notification import NotificationRequestPayload


def test_notification_request_valid() -> None:
    request = NotificationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.WHATSAPP,
        governance_action=GovernanceAction.AUTO_APPROVE,
        language_locale=LanguageLocale.ENGLISH,
        disbursement_txn_id="TXN-2026-981245",
    )
    assert request.session_id == "sess_12345678"
    assert request.channel_type == ChannelType.WHATSAPP
    assert request.governance_action == GovernanceAction.AUTO_APPROVE
    assert request.language_locale == LanguageLocale.ENGLISH
    assert request.disbursement_txn_id == "TXN-2026-981245"
    assert request.escalation_case_id is None


def test_notification_request_manual_review() -> None:
    request = NotificationRequestPayload(
        session_id="sess_87654321",
        channel_type=ChannelType.IVR_VOICE,
        governance_action=GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
        language_locale=LanguageLocale.HINDI,
        escalation_case_id="SPP-CASE-2026-100200",
    )
    assert request.escalation_case_id == "SPP-CASE-2026-100200"
    assert request.language_locale == LanguageLocale.HINDI


def test_notification_request_auto_reject_valid() -> None:
    request = NotificationRequestPayload(
        session_id="sess_87654321",
        channel_type=ChannelType.SMS,
        governance_action=GovernanceAction.AUTO_REJECT,
        rejection_reason=RejectionReasonCode.IDENTITY_NOT_VERIFIED,
    )
    assert request.rejection_reason == RejectionReasonCode.IDENTITY_NOT_VERIFIED


def test_notification_request_reprompt_valid() -> None:
    request = NotificationRequestPayload(
        session_id="sess_87654321",
        channel_type=ChannelType.WHATSAPP,
        governance_action=GovernanceAction.REQUEST_MORE_INFO,
        missing_entity=DomainEntityKey.CROP_NAME,
    )
    assert request.missing_entity == DomainEntityKey.CROP_NAME


def test_notification_request_invalid_session_id() -> None:
    with pytest.raises(ValidationError):
        NotificationRequestPayload(
            session_id="short",  # Min length 8
            channel_type=ChannelType.USSD,
            governance_action=GovernanceAction.AUTO_APPROVE,
            disbursement_txn_id="TXN-2026-981245",
        )


def test_notification_request_missing_txn_id_on_approval() -> None:
    with pytest.raises(ValidationError, match="disbursement_txn_id is required"):
        NotificationRequestPayload(
            session_id="sess_12345678",
            channel_type=ChannelType.WHATSAPP,
            governance_action=GovernanceAction.AUTO_APPROVE,
            disbursement_txn_id=None,
        )


def test_notification_request_missing_case_id_on_review() -> None:
    with pytest.raises(ValidationError, match="escalation_case_id is required"):
        NotificationRequestPayload(
            session_id="sess_12345678",
            channel_type=ChannelType.WHATSAPP,
            governance_action=GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
            escalation_case_id=None,
        )


def test_notification_request_missing_reason_on_rejection() -> None:
    with pytest.raises(ValidationError, match="rejection_reason is required"):
        NotificationRequestPayload(
            session_id="sess_12345678",
            channel_type=ChannelType.WHATSAPP,
            governance_action=GovernanceAction.AUTO_REJECT,
            rejection_reason=None,
        )


def test_notification_request_invalid_rejection_reason_enum() -> None:
    with pytest.raises(ValidationError):
        NotificationRequestPayload(
            session_id="sess_12345678",
            channel_type=ChannelType.WHATSAPP,
            governance_action=GovernanceAction.AUTO_REJECT,
            rejection_reason="UNRECOGNIZED_REASON_STRING",  # type: ignore[arg-type]
        )


def test_notification_request_missing_entity_on_reprompt() -> None:
    with pytest.raises(ValidationError, match="missing_entity is required"):
        NotificationRequestPayload(
            session_id="sess_12345678",
            channel_type=ChannelType.WHATSAPP,
            governance_action=GovernanceAction.REQUEST_MORE_INFO,
            missing_entity=None,
        )


def test_notification_request_invalid_missing_entity_enum() -> None:
    with pytest.raises(ValidationError):
        NotificationRequestPayload(
            session_id="sess_12345678",
            channel_type=ChannelType.WHATSAPP,
            governance_action=GovernanceAction.REQUEST_MORE_INFO,
            missing_entity="INVALID_ENTITY_KEY",  # type: ignore[arg-type]
        )
