"""Layer 1 USSD Menu Edge Connector skeleton."""

from src.models.raw_ingress import UssdIngressPayload


class UssdConnector:
    """Processes USSD menu signaling codes and passes canonical ingress payload."""

    async def process_ussd_session(self, payload: UssdIngressPayload) -> UssdIngressPayload:
        return payload
