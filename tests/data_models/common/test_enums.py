import pytest

from src.data_models.common.enums import (
    ApplicationIntent,
    ApplicationStatus,
    ChannelType,
    DisbursementStatus,
    DomainEntityKey,
    EligibilityStatus,
    GovernanceAction,
    LanguageLocale,
    PayloadType,
    SessionStatus,
    StructureLevel,
    ThreatCategory,
)


@pytest.mark.parametrize(
    ("enum_member", "expected_value"),
    [
        (ChannelType.WHATSAPP, "whatsapp"),
        (ChannelType.IVR_VOICE, "ivr_voice"),
        (ChannelType.USSD, "ussd"),
        (ChannelType.SMS, "sms"),
        (PayloadType.AUDIO, "audio"),
        (PayloadType.TEXT, "text"),
        (PayloadType.IMAGE, "image"),
        (PayloadType.DOCUMENT, "document"),
        (StructureLevel.FREE_TEXT, "free_text"),
        (StructureLevel.MENU_SELECTION, "menu_selection"),
        (StructureLevel.DTMF_SELECTION, "dtmf_selection"),
        (ApplicationIntent.APPLY_SUBSIDY, "apply_subsidy"),
        (ApplicationIntent.CHECK_STATUS, "check_status"),
        (ApplicationIntent.SUBMIT_APPEAL, "submit_appeal"),
        (ApplicationIntent.GRIEVANCE_REDIRECTION, "grievance_redirection"),
        (ApplicationIntent.UPDATE_CROP_DETAILS, "update_crop_details"),
        (ApplicationIntent.SCHEME_INQUIRY, "scheme_inquiry"),
        (ApplicationIntent.UNKNOWN, "unknown"),
        (EligibilityStatus.PENDING_VERIFICATION, "PENDING_VERIFICATION"),
        (EligibilityStatus.ELIGIBLE, "ELIGIBLE"),
        (EligibilityStatus.INELIGIBLE, "INELIGIBLE"),
        (EligibilityStatus.REQUIRES_REVIEW, "REQUIRES_REVIEW"),
        (GovernanceAction.AUTOMATED_PAYOUT, "AUTOMATED_PAYOUT"),
        (GovernanceAction.AUTO_APPROVE, "AUTO_APPROVE"),
        (GovernanceAction.AUTO_REJECT, "AUTO_REJECT"),
        (GovernanceAction.HUMAN_REVIEW, "HUMAN_REVIEW"),
        (GovernanceAction.ROUTE_FOR_MANUAL_REVIEW, "ROUTE_FOR_MANUAL_REVIEW"),
        (GovernanceAction.REQUEST_MORE_INFO, "REQUEST_MORE_INFO"),
        (GovernanceAction.MANUAL_APPROVE, "MANUAL_APPROVE"),
        (GovernanceAction.MANUAL_REJECT, "MANUAL_REJECT"),
        (SessionStatus.ACTIVE, "ACTIVE"),
        (SessionStatus.PENDING, "PENDING"),
        (SessionStatus.COMPLETED, "COMPLETED"),
        (SessionStatus.ABANDONED, "ABANDONED"),
        (SessionStatus.TIMEOUT, "TIMEOUT"),
        (ApplicationStatus.DRAFT, "DRAFT"),
        (ApplicationStatus.SUBMITTED, "SUBMITTED"),
        (ApplicationStatus.UNDER_REVIEW, "UNDER_REVIEW"),
        (ApplicationStatus.INFO_REQUESTED, "INFO_REQUESTED"),
        (ApplicationStatus.APPROVED, "APPROVED"),
        (ApplicationStatus.REJECTED, "REJECTED"),
        (ApplicationStatus.APPEALED, "APPEALED"),
        (DisbursementStatus.PENDING, "PENDING"),
        (DisbursementStatus.INITIATED, "INITIATED"),
        (DisbursementStatus.SUCCESS, "SUCCESS"),
        (DisbursementStatus.FAILED, "FAILED"),
        (DisbursementStatus.RETURNED, "RETURNED"),
        (DomainEntityKey.DISTRICT, "district"),
        (DomainEntityKey.TALUKA, "taluka"),
        (DomainEntityKey.VILLAGE, "village"),
        (DomainEntityKey.CROP_NAME, "crop_name"),
        (DomainEntityKey.CROP_VARIETY, "crop_variety"),
        (DomainEntityKey.LAND_SIZE_ACRES, "land_size_acres"),
        (DomainEntityKey.SUBSIDY_SCHEME_ID, "subsidy_scheme_id"),
        (DomainEntityKey.SURVEY_NUMBER, "survey_number"),
        (DomainEntityKey.BANK_ACCOUNT_LAST4, "bank_account_last4"),
        (ThreatCategory.SYSTEM_OVERRIDE, "SYSTEM_OVERRIDE"),
        (ThreatCategory.ROLE_USURPATION, "ROLE_USURPATION"),
        (ThreatCategory.DELIMITER_HIJACKING, "DELIMITER_HIJACKING"),
        (ThreatCategory.DATABASE_INJECTION, "DATABASE_INJECTION"),
        (ThreatCategory.PAYOUT_MANIPULATION, "PAYOUT_MANIPULATION"),
    ],
)
def test_enum_members_match_expected_values(enum_member: str, expected_value: str) -> None:
    assert enum_member == expected_value


def test_governance_action_classification_properties() -> None:
    for action in (
        GovernanceAction.AUTO_APPROVE,
        GovernanceAction.AUTOMATED_PAYOUT,
        GovernanceAction.MANUAL_APPROVE,
    ):
        assert action.is_approval is True
        assert action.is_review is False
        assert action.is_rejection is False

    for action in (
        GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
        GovernanceAction.HUMAN_REVIEW,
    ):
        assert action.is_approval is False
        assert action.is_review is True
        assert action.is_rejection is False

    for action in (
        GovernanceAction.AUTO_REJECT,
        GovernanceAction.MANUAL_REJECT,
    ):
        assert action.is_approval is False
        assert action.is_review is False
        assert action.is_rejection is True

    assert GovernanceAction.REQUEST_MORE_INFO.is_approval is False
    assert GovernanceAction.REQUEST_MORE_INFO.is_review is False
    assert GovernanceAction.REQUEST_MORE_INFO.is_rejection is False


def test_channel_type_properties() -> None:
    assert ChannelType.IVR_VOICE.is_voice is True
    assert ChannelType.WHATSAPP.is_voice is False
    assert ChannelType.SMS.is_voice is False
    assert ChannelType.USSD.is_voice is False

    assert ChannelType.SMS.is_text_only is True
    assert ChannelType.USSD.is_text_only is True
    assert ChannelType.WHATSAPP.is_text_only is False
    assert ChannelType.IVR_VOICE.is_text_only is False

    assert ChannelType.WHATSAPP.is_rich_card is True
    assert ChannelType.SMS.is_rich_card is False


def test_payload_type_properties() -> None:
    assert PayloadType.AUDIO.is_audio is True
    assert PayloadType.TEXT.is_audio is False
    assert PayloadType.TEXT.is_text is True
    assert PayloadType.AUDIO.is_text is False


def test_structure_level_properties() -> None:
    assert StructureLevel.DTMF_SELECTION.is_structured is True
    assert StructureLevel.MENU_SELECTION.is_structured is True
    assert StructureLevel.FREE_TEXT.is_structured is False
    assert StructureLevel.FREE_TEXT.is_free_text is True
    assert StructureLevel.DTMF_SELECTION.is_free_text is False


def test_language_locale_properties() -> None:
    assert LanguageLocale.HINDI.is_hindi is True
    assert LanguageLocale.ENGLISH.is_hindi is False
    assert LanguageLocale.TAMIL.is_hindi is False
