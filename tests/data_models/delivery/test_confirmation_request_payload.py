"""Unit tests for ConfirmationRequestPayload domain schema."""

import pytest
from pydantic import ValidationError

from src.data_models.common import (
    ChannelType,
    GovernanceAction,
    LanguageLocale,
)
from src.data_models.delivery import ConfirmationRequestPayload


def test_confirmation_request_valid() -> None:
    req = ConfirmationRequestPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.WHATSAPP,
        governance_action=GovernanceAction.AUTO_APPROVE,
        language_locale=LanguageLocale.ENGLISH,
        disbursement_txn_id="TXN-2026-981245",
    )
    assert req.session_id == "sess_12345678"
    assert req.channel_type == ChannelType.WHATSAPP
    assert req.governance_action == GovernanceAction.AUTO_APPROVE
    assert req.language_locale == LanguageLocale.ENGLISH
    assert req.disbursement_txn_id == "TXN-2026-981245"
    assert req.escalation_case_id is None


def test_confirmation_request_manual_review() -> None:
    req = ConfirmationRequestPayload(
        session_id="sess_87654321",
        channel_type=ChannelType.IVR_VOICE,
        governance_action=GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
        language_locale=LanguageLocale.HINDI,
        escalation_case_id="SPP-CASE-2026-100200",
    )
    assert req.escalation_case_id == "SPP-CASE-2026-100200"
    assert req.language_locale == LanguageLocale.HINDI


def test_confirmation_request_invalid_session_id() -> None:
    with pytest.raises(ValidationError):
        ConfirmationRequestPayload(
            session_id="invalid",  # Must match regex ^sess_[a-zA-Z0-9]{8,64}$
            channel_type=ChannelType.USSD,
            governance_action=GovernanceAction.AUTO_APPROVE,
        )
