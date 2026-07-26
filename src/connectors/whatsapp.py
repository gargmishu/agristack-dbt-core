"""Layer 1 WhatsApp Edge Connector skeleton."""

from src.models.raw_ingress import WhatsAppIngressPayload


class WhatsAppConnector:
    """Processes WhatsApp cleartext/audio webhooks and passes canonical ingress payload."""

    async def process_webhook(self, payload: WhatsAppIngressPayload) -> WhatsAppIngressPayload:
        return payload
