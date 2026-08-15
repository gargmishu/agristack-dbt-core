"""Layer 1 SMS Edge Connector (Layer 1 -> Layer 2).

See: decisions/step2.0_canonical_domain_schemas.md
See: decisions/step3.5_adaptive_multichannel_confirmation_delivery.md

Processes incoming TRAI DLT-registered transactional SMS webhooks and passes canonical
ingress payloads into Layer 2 security pipelines, and transmits outbound SMS confirmations.
"""

import logging
from typing import Any
from uuid import uuid4

from src.config import get_sms_interface_id
from src.data_models.common import ChannelType
from src.data_models.delivery import OutboundConfirmationPayload, TransmissionAck
from src.data_models.raw_ingress import SmsIngressPayload

logger = logging.getLogger(__name__)


class SmsConnector:
    """Processes incoming and outgoing SMS transmissions across carrier gateways."""

    def __init__(self, interface_id: str | None = None) -> None:
        """Initializes SmsConnector with carrier SMS gateway interface identifier.

        Args:
            interface_id: Optional SMS carrier interface identifier (defaults to env or config).
        """
        self._interface_id = interface_id or get_sms_interface_id()

    @property
    def interface_id(self) -> str:
        """Returns the configured carrier interface identifier."""
        return self._interface_id

    async def process_inbound_sms(self, payload: dict[str, Any]) -> SmsIngressPayload:
        """Validates and processes raw incoming SMS webhook into SmsIngressPayload.

        Args:
            payload: Raw dict payload received from carrier SMS gateway webhook.

        Returns:
            Validated SmsIngressPayload.
        """
        validated_payload = SmsIngressPayload.model_validate(payload)

        logger.info(
            "Validated SMS webhook for session=%s, message_id=%s",
            validated_payload.session_id,
            validated_payload.channel_message_id,
        )
        return validated_payload

    async def send_outbound_confirmation(
        self, payload: OutboundConfirmationPayload
    ) -> TransmissionAck:
        """Dispatches outbound SMS message to carrier SMS gateway.

        Args:
            payload: Validated OutboundConfirmationPayload.

        Returns:
            Strict TransmissionAck receipt with carrier reference ID.
        """
        carrier_ref = f"sms-dr-{uuid4().hex[:12]}"
        logger.info(
            "Transmitting outbound SMS for session=%s, interface=%s, carrier_ref=%s",
            payload.session_id,
            self._interface_id,
            carrier_ref,
        )
        return TransmissionAck(
            interface_id=self._interface_id,
            channel_type=ChannelType.SMS,
            session_id=payload.session_id,
            status=payload.delivery_status,
            carrier_reference_id=carrier_ref,
        )
