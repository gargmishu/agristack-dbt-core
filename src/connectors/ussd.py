"""Layer 1 USSD Menu Edge Connector skeleton."""

from src.models.ingress import USSDIngressPayload


class USSDConnector:
    """Processes USSD menu signaling codes and passes canonical ingress payload."""

    async def process_ussd_session(self, payload: USSDIngressPayload) -> USSDIngressPayload:
        return payload
