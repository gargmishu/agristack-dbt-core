import pytest

from src.data_models.common import ApplicationIntent, DomainEntityKey
from src.data_models.governance import ExtractedEntityPayload
from src.orchestrator.state_machine import StateMachine


@pytest.mark.asyncio
async def test_state_machine_execution_loop() -> None:
    state_machine = StateMachine()
    payload = ExtractedEntityPayload(
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        ai_confidence_score=0.92,
        domain_entities={DomainEntityKey.DISTRICT: "Karnal"},
    )

    result = await state_machine.execute_state_transition(payload)
    assert result.application_intent == ApplicationIntent.APPLY_SUBSIDY


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("intent", "confidence", "is_bypass"),
    [
        (ApplicationIntent.CHECK_STATUS, 0.95, False),
        (ApplicationIntent.APPLY_SUBSIDY, 1.0, True),
        (ApplicationIntent.SUBMIT_APPEAL, 0.88, False),
        (ApplicationIntent.GRIEVANCE_REDIRECTION, 0.90, False),
    ],
)
async def test_state_machine_intents(
    intent: ApplicationIntent, confidence: float, is_bypass: bool
) -> None:
    state_machine = StateMachine()
    payload = ExtractedEntityPayload(
        application_intent=intent,
        ai_confidence_score=confidence,
        domain_entities={DomainEntityKey.DISTRICT: "Pune"},
        is_structured_menu_bypass=is_bypass,
    )
    result = await state_machine.execute_state_transition(payload)
    assert result.application_intent == intent
    assert result.is_structured_menu_bypass == is_bypass
