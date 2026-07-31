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
