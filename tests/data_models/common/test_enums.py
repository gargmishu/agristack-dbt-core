from src.data_models.common.enums import (
    ApplicationIntent,
    ChannelType,
    DisbursementStatus,
    GovernanceAction,
    PayloadType,
    ThreatCategory,
)


def test_enums_string_representations() -> None:
    assert str(ChannelType.WHATSAPP) == "whatsapp"
    assert str(PayloadType.TEXT) == "text"
    assert str(ApplicationIntent.APPLY_SUBSIDY) == "apply_subsidy"
    assert str(GovernanceAction.AUTO_APPROVE) == "AUTO_APPROVE"
    assert str(DisbursementStatus.SUCCESS) == "SUCCESS"
    assert str(ThreatCategory.DATABASE_INJECTION) == "DATABASE_INJECTION"
    assert str(ThreatCategory.SYSTEM_OVERRIDE) == "SYSTEM_OVERRIDE"
