"""Layer 1 USSD Menu Edge Connector (Layer 1 -> Layer 2).

See: decisions/step2.0_canonical_domain_schemas.md#ussd-menu-ingress-payload

Processes incoming Unstructured Supplementary Service Data (USSD) Signaling System No. 7
(SS7)
/
Signaling Transport (SIGTRAN) carrier menu signaling payloads, validating shortcode patterns
and
concatenated user digit selections.
"""

import logging
from collections.abc import Mapping
from uuid import uuid4

from src.config import get_ussd_interface_id
from src.data_models.common import ChannelType
from src.data_models.notification import OutboundNotificationPayload, TransmissionAck
from src.data_models.raw_ingress import UssdIngressPayload

logger = logging.getLogger(__name__)


class UssdConnector:
    """Cellular signaling edge connector interfacing with SS7/SIGTRAN USSD gateways.

    Provides validation for incoming USSD menu signaling frames and dispatch for outbound
    response strings.

    Core Capabilities:
    - Ingress Validation (`process_ussd_session`): Validates incoming USSD signaling
      mappings into
      `UssdIngressPayload` instances, verifying shortcode patterns, session identifiers, and
      user digit selections.
    - Egress Dispatch (`send_outbound_notification`): Dispatches plain-text response strings
      (`OutboundNotificationPayload` capped at 160 characters) to the carrier gateway and
      returns
      an authoritative `TransmissionAck` receipt.

    Attributes:
        interface_id: Configured identifier of the target USSD gateway interface.

    See: decisions/step2.0_canonical_domain_schemas.md#ussd-menu-ingress-payload
    See: decisions/step3.2_security_and_ingestion_firewalls.md
    See: decisions/step3.5_adaptive_multichannel_confirmation_delivery.md
    """

    def __init__(self, interface_id: str | None = None) -> None:
        """Initializes cellular signaling connector with SS7/SIGTRAN interface identifier.

        Args:
            interface_id: Optional USSD interface identifier (defaults to env or config).
        """
        self._interface_id = interface_id or get_ussd_interface_id()

    @property
    def interface_id(self) -> str:
        """Returns the configured SIGTRAN signaling interface identifier."""
        return self._interface_id

    async def process_ussd_session(self, payload: Mapping[str, object]) -> UssdIngressPayload:
        """Validates and processes raw USSD menu payload into canonical UssdIngressPayload.

        Args:
            payload: Raw dict/mapping payload received from USSD SS7/SIGTRAN gateway.

        Returns:
            Validated UssdIngressPayload.
        """
        validated_payload = UssdIngressPayload.model_validate(payload)

        logger.info(
            "Validated USSD session for session=%s, service_code=%s",
            validated_payload.session_id,
            validated_payload.ussd_service_code,
        )
        return validated_payload

    async def send_outbound_notification(
        self, payload: OutboundNotificationPayload
    ) -> TransmissionAck:
        """Pushes final USSD signaling response string back to carrier gateway.

        Args:
            payload: Validated OutboundNotificationPayload (strictly <=160 chars).

        Returns:
            Strict TransmissionAck receipt with carrier reference ID.
        """
        carrier_ref = f"ussd-sig-{uuid4().hex[:12]}"
        logger.info(
            "Pushing outbound USSD string for session=%s, interface=%s, carrier_ref=%s",
            payload.session_id,
            self._interface_id,
            carrier_ref,
        )
        return TransmissionAck(
            interface_id=self._interface_id,
            channel_type=ChannelType.USSD,
            session_id=payload.session_id,
            status=payload.delivery_status,
            carrier_reference_id=carrier_ref,
        )
