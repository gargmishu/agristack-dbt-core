"""Layer 4 GovernanceRouter decision matrix skeleton."""

from src.models.governance import ApplicationDecisionPayload


class GovernanceRouter:
    """Evaluates AI confidence score and eligibility status to determine routing action."""

    async def route_governance_decision(
        self, payload: ApplicationDecisionPayload
    ) -> ApplicationDecisionPayload:
        return payload
