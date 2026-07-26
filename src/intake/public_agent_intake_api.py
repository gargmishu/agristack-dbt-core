"""Layer 3 Public Agent Intake Gateway skeleton."""

from src.models.intake import StandardizedIntakePayload


class PublicAgentIntakeApi:
    """Public Agent Intake Gateway API normalizing events before submitting to Layer 4."""

    async def submit_intake(self, payload: StandardizedIntakePayload) -> StandardizedIntakePayload:
        return payload
