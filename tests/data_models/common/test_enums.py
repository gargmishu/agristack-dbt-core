from src.data_models.common.enums import (
    ApplicationIntent,
    ChannelType,
    DisbursementStatus,
    GovernanceDecision,
    PayloadType,
)


def test_enums_string_representations() -> None:
    assert str(ChannelType.WHATSAPP) == "whatsapp"
    assert str(PayloadType.TEXT) == "text"
    assert str(ApplicationIntent.APPLY_SUBSIDY) == "apply_subsidy"
    assert str(GovernanceDecision.AUTO_APPROVE) == "AUTO_APPROVE"
    assert str(DisbursementStatus.SUCCESS) == "SUCCESS"
