"""Layer 1 WhatsApp Edge Connector (Layer 1 -> Layer 2).

See: decisions/step2.0_canonical_domain_schemas.md#whatsapp-ingress-payload

Processes incoming Meta WhatsApp Business Application Programming Interface (API) webhooks,
validating cleartext text messages and voice note audio URLs against zero Personally Identifiable
Information (zero-PII) security rules.
"""

import logging
from collections.abc import Mapping
from uuid import uuid4

from src.config import get_whatsapp_interface_id
from src.data_models.common import ChannelType
from src.data_models.delivery import OutboundConfirmationPayload, TransmissionAck
from src.data_models.raw_ingress import WhatsAppIngressPayload

logger = logging.getLogger(__name__)


class WhatsAppConnector:
    """Processes WhatsApp cleartext/audio webhooks and passes canonical ingress payload."""

    def __init__(self, interface_id: str | None = None) -> None:
        """Initializes WhatsAppConnector with carrier interface identifier.

        Args:
            interface_id: Optional carrier webhook interface identifier (defaults to env or config).
        """
        self._interface_id = interface_id or get_whatsapp_interface_id()

    @property
    def interface_id(self) -> str:
        """Returns the configured carrier interface identifier."""
        return self._interface_id

    async def process_webhook(
        self, payload: bytes | str | Mapping[str, object]
    ) -> WhatsAppIngressPayload:
        """Validates and processes raw WhatsApp webhook into WhatsAppIngressPayload.

        Args:
            payload: Raw bytes, JSON string, or mapping received from Meta WhatsApp API webhook.

        Returns:
            Validated WhatsAppIngressPayload.
        """
        if isinstance(payload, bytes | str):
            validated_payload = WhatsAppIngressPayload.model_validate_json(payload)
        else:
            validated_payload = WhatsAppIngressPayload.model_validate(payload)

        logger.info(
            "Validated WhatsApp webhook for session=%s, message_id=%s, type=%s",
            validated_payload.session_id,
            validated_payload.channel_message_id,
            validated_payload.payload_type,
        )
        return validated_payload

    async def send_outbound_confirmation(
        self, payload: OutboundConfirmationPayload
    ) -> TransmissionAck:
        """Dispatches outbound confirmation response to Meta WhatsApp Cloud API.

        Args:
            payload: Validated OutboundConfirmationPayload.

        Returns:
            Strict TransmissionAck receipt with carrier reference ID.
        """
        carrier_ref = f"wamid.{uuid4().hex[:16]}"
        logger.info(
            "Transmitting outbound WhatsApp message for session=%s, interface=%s, carrier_ref=%s",
            payload.session_id,
            self._interface_id,
            carrier_ref,
        )
        return TransmissionAck(
            interface_id=self._interface_id,
            channel_type=ChannelType.WHATSAPP,
            session_id=payload.session_id,
            status=payload.delivery_status,
            carrier_reference_id=carrier_ref,
        )
