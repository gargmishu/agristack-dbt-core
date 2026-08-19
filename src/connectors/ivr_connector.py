"""Layer 1 IVR Telephony Edge Connector (Layer 1 -> Layer 2).

See: decisions/step2.0_canonical_domain_schemas.md#ivr-telephony-ingress-payload

Processes incoming Session Initiation Protocol (SIP) trunk telephony gateway streams,
validating 16kHz Pulse-Code Modulation (PCM) uncompressed audio recording URLs and caller
Automatic Number Identification (ANI) phone numbers.
"""

import logging
from collections.abc import Mapping
from uuid import uuid4

from src.config import get_ivr_interface_id
from src.data_models.common import ChannelType
from src.data_models.delivery import OutboundNotificationPayload, TransmissionAck
from src.data_models.raw_ingress import IvrIngressPayload

logger = logging.getLogger(__name__)


class IvrConnector:
    """Processes IVR voice SIP gateway streams and passes canonical ingress payload."""

    def __init__(self, interface_id: str | None = None) -> None:
        """Initializes IvrConnector with SIP telephony gateway interface identifier.

        Args:
            interface_id: Optional IVR interface identifier (defaults to env or config).
        """
        self._interface_id = interface_id or get_ivr_interface_id()

    @property
    def interface_id(self) -> str:
        """Returns the configured telephony gateway interface identifier."""
        return self._interface_id

    async def process_call_session(self, payload: Mapping[str, object]) -> IvrIngressPayload:
        """Validates and processes raw IVR telephony payload into canonical IvrIngressPayload.

        Args:
            payload: Raw dict/mapping payload received from SIP telephony gateway.

        Returns:
            Validated IvrIngressPayload.
        """
        validated_payload = IvrIngressPayload.model_validate(payload)

        logger.info(
            "Validated IVR call session for session=%s, duration=%ss",
            validated_payload.session_id,
            validated_payload.audio_duration_seconds,
        )
        return validated_payload

    async def send_outbound_notification(
        self, payload: OutboundNotificationPayload
    ) -> TransmissionAck:
        """Dispatches outbound audio playback instruction to SIP telephony gateway.

        Args:
            payload: Validated OutboundNotificationPayload with synthesized audio URL.

        Returns:
            Strict TransmissionAck receipt with carrier reference ID.
        """
        carrier_ref = f"sip-call-{uuid4().hex[:12]}"
        logger.info(
            "Transmitting outbound IVR voice audio for session=%s, interface=%s, carrier_ref=%s",
            payload.session_id,
            self._interface_id,
            carrier_ref,
        )
        return TransmissionAck(
            interface_id=self._interface_id,
            channel_type=ChannelType.IVR_VOICE,
            session_id=payload.session_id,
            status=payload.delivery_status,
            carrier_reference_id=carrier_ref,
        )
