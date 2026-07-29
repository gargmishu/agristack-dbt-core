"""Layer 1 WhatsApp Edge Connector (Layer 1 -> Layer 2).

Processes incoming Meta WhatsApp Business API webhooks, validating cleartext
text messages and voice note audio URLs against zero-PII security rules.
"""

import logging
from typing import Any

from src.models.raw_ingress import WhatsAppIngressPayload

logger = logging.getLogger(__name__)


class WhatsAppConnector:
    """Processes WhatsApp cleartext/audio webhooks and passes canonical ingress payload."""

    async def process_webhook(self, payload: WhatsAppIngressPayload | dict[str, Any]) -> WhatsAppIngressPayload:
        """Validates and processes raw WhatsApp webhook payload into canonical WhatsAppIngressPayload.

        Args:
            payload: Raw dict or pre-parsed WhatsAppIngressPayload instance.

        Returns:
            Validated WhatsAppIngressPayload.
        """
        if isinstance(payload, dict):
            validated_payload = WhatsAppIngressPayload.model_validate(payload)
        else:
            validated_payload = payload

        logger.info(
            "Processed WhatsApp webhook for session=%s, message_id=%s, type=%s",
            validated_payload.session_id,
            validated_payload.channel_message_id,
            validated_payload.payload_type,
        )
        return validated_payload
