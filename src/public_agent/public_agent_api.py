"""Layer 3 Public Agent Gateway API skeleton."""

from src.models.public_agent import StandardizedPublicAgentPayload


class PublicAgentApi:
    """Public Agent Gateway API normalizing events before submitting to Layer 4."""

    async def submit_payload(
        self, payload: StandardizedPublicAgentPayload
    ) -> StandardizedPublicAgentPayload:
        return payload
