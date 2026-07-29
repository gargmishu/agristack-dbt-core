"""Layer 3 Public Agent Gateway API skeleton."""

from src.data_models.public_agent import PublicAgentStandardizedIntakePayload


class PublicAgentApi:
    """Public Agent Gateway API normalizing events before submitting to Layer 4."""

    async def submit_payload(
        self, payload: PublicAgentStandardizedIntakePayload
    ) -> PublicAgentStandardizedIntakePayload:
        return payload
