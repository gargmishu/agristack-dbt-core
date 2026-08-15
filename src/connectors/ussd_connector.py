"""Layer 1 USSD Menu Edge Connector (Layer 1 -> Layer 2).

See: decisions/step2.0_canonical_domain_schemas.md#ussd-menu-ingress-payload

Processes incoming Unstructured Supplementary Service Data (USSD) Signaling System No. 7 (SS7) /
Signaling Transport (SIGTRAN) carrier menu signaling payloads, validating shortcode patterns and
concatenated user digit selections.
"""

import logging
from typing import Any

from src.config import get_sigtran_interface_id
from src.data_models.delivery import OutboundConfirmationPayload
from src.data_models.raw_ingress import UssdIngressPayload

logger = logging.getLogger(__name__)


class UssdConnector:
    """Processes USSD menu signaling codes and passes canonical ingress payload."""

    def __init__(self, interface_id: str | None = None) -> None:
        """Initializes UssdConnector with SS7/SIGTRAN carrier interface identifier.

        Args:
            interface_id: Optional SS7/SIGTRAN interface identifier (defaults to env or config).
        """
        self._interface_id = interface_id or get_sigtran_interface_id()

    @property
    def interface_id(self) -> str:
        """Returns the configured SIGTRAN signaling interface identifier."""
        return self._interface_id

    async def process_ussd_session(self, payload: dict[str, Any]) -> UssdIngressPayload:
        """Validates and processes raw USSD menu payload into canonical UssdIngressPayload.

        Args:
            payload: Raw dict payload received from USSD SS7/SIGTRAN gateway.

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

    async def send_outbound_confirmation(
        self, payload: OutboundConfirmationPayload
    ) -> dict[str, Any]:
        """Pushes final USSD signaling response string back to carrier gateway.

        Args:
            payload: Validated OutboundConfirmationPayload (strictly <=160 chars).

        Returns:
            Simulated SS7/SIGTRAN USSD menu termination response.
        """
        logger.info(
            "Pushing outbound USSD string for session=%s, interface=%s, length=%d",
            payload.session_id,
            self._interface_id,
            len(payload.formatted_message),
        )
        return {
            "sigtran_interface": self._interface_id,
            "session_id": payload.session_id,
            "status": payload.delivery_status,
            "ussd_menu_response": payload.formatted_message,
        }
