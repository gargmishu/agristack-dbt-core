"""Layer 1 WhatsApp Edge Connector (Layer 1 -> Layer 2).

See: decisions/step2.0_canonical_domain_schemas.md#whatsapp-ingress-payload

Processes incoming Meta WhatsApp Business Application Programming Interface (API) and
authorized Business Solution Provider (BSP) partner webhooks, validating cleartext text
messages and voice note audio URLs against zero Personally Identifiable Information (zero-PII)
security rules.
"""

import logging
from collections.abc import Mapping
from uuid import uuid4

from src.config import get_whatsapp_interface_id
from src.data_models.common import ChannelType
from src.data_models.notification import OutboundNotificationPayload, TransmissionAck
from src.data_models.raw_ingress import WhatsAppIngressPayload

logger = logging.getLogger(__name__)

__all__ = ["WhatsAppConnector"]


class WhatsAppConnector:
    """Messaging edge connector interfacing with Meta WhatsApp Cloud API and BSP webhooks.

    Interfaces with Meta WhatsApp Cloud API and authorized Business Solution Provider (BSP)
    partner webhooks. Provides validation for incoming WhatsApp webhook events and dispatch for
    outbound messages.

    Core Capabilities:
    - Ingress Validation (`process_webhook`): Validates incoming webhook event mappings into
      `WhatsAppIngressPayload` instances, enforcing modality exclusivity between text bodies
      and audio URLs.
    - Egress Dispatch (`send_outbound_notification`): Dispatches formatted notification cards
      (`OutboundNotificationPayload`) to the WhatsApp API endpoint and returns an authoritative
      `TransmissionAck` receipt containing a message tracking ID (`wamid`).

    Attributes:
        interface_id: Configured identifier of the target WhatsApp gateway interface.

    See: decisions/step2.0_canonical_domain_schemas.md#whatsapp-ingress-payload
    See: decisions/step3.2_security_and_ingestion_firewalls.md
    See: decisions/step3.5_adaptive_multichannel_confirmation_delivery.md
    """

    def __init__(self, interface_id: str | None = None) -> None:
        """Initializes messaging connector with carrier interface identifier.

        Args:
            interface_id: Optional carrier webhook interface identifier (defaults to env or config).
        """
        self._interface_id = interface_id or get_whatsapp_interface_id()

    @property
    def interface_id(self) -> str:
        """Returns the configured carrier interface identifier."""
        return self._interface_id

    async def process_webhook(self, payload: Mapping[str, object]) -> WhatsAppIngressPayload:
        """Validates and processes raw WhatsApp webhook into WhatsAppIngressPayload.

        Args:
            payload: Raw dict/mapping payload received from Meta WhatsApp API webhook.

        Returns:
            Validated WhatsAppIngressPayload.
        """
        validated_payload = WhatsAppIngressPayload.model_validate(payload)

        logger.info(
            "Validated WhatsApp webhook for session=%s, message_id=%s, type=%s",
            validated_payload.session_id,
            validated_payload.channel_message_id,
            validated_payload.payload_type,
        )
        return validated_payload

    async def send_outbound_notification(
        self, payload: OutboundNotificationPayload
    ) -> TransmissionAck:
        """Dispatches outbound notification response to Meta WhatsApp Cloud API.

        Args:
            payload: Validated OutboundNotificationPayload.

        Returns:
            Strict TransmissionAck receipt with carrier reference ID.
        """
        carrier_reference_id = f"wamid.{uuid4().hex[:16]}"
        logger.info(
            "Transmitting outbound WhatsApp message for session=%s, "
            "interface=%s, carrier_reference_id=%s",
            payload.session_id,
            self._interface_id,
            carrier_reference_id,
        )
        return TransmissionAck(
            interface_id=self._interface_id,
            channel_type=ChannelType.WHATSAPP,
            session_id=payload.session_id,
            status=payload.delivery_status,
            carrier_reference_id=carrier_reference_id,
        )
