"""Layer 4 StateMachine orchestrator skeleton."""

from src.models.governance import ExtractedEntityPayload


class StateMachine:
    """Deterministic execution loop governing workflow transitions across evaluation gates."""

    async def execute_state_transition(
        self, payload: ExtractedEntityPayload
    ) -> ExtractedEntityPayload:
        return payload
