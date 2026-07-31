"""Layer 1 WhatsApp Edge Connector (Layer 1 -> Layer 2).

See: decisions/step2.0_canonical_domain_schemas.md#whatsapp-ingress-payload

Processes incoming Meta WhatsApp Business Application Programming Interface (API) webhooks,
validating cleartext text messages and voice note audio URLs against zero Personally Identifiable
Information (zero-PII) security rules.
"""

import logging
from typing import Any

from src.data_models.raw_ingress import WhatsAppIngressPayload

logger = logging.getLogger(__name__)


class WhatsAppConnector:
    """Processes WhatsApp cleartext/audio webhooks and passes canonical ingress payload."""

    async def process_webhook(self, payload: dict[str, Any]) -> WhatsAppIngressPayload:
        """Validates and processes raw WhatsApp webhook payload into canonical WhatsAppIngressPayload.

        Args:
            payload: Raw dict payload received from Meta WhatsApp API webhook.

        Returns:
            Validated WhatsAppIngressPayload.
        """
        validated_payload = WhatsAppIngressPayload.model_validate(payload)

        logger.info(
            "Processed WhatsApp webhook for session=%s, message_id=%s, type=%s",
            validated_payload.session_id,
            validated_payload.channel_message_id,
            validated_payload.payload_type,
        )
        return validated_payload
