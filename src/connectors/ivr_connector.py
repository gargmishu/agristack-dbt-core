"""Layer 1 IVR Telephony Edge Connector (Layer 1 -> Layer 2).

See: decisions/step2.0_canonical_domain_schemas.md#ivr-telephony-ingress-payload

Processes incoming Session Initiation Protocol (SIP) trunk telephony gateway streams,
validating 16kHz Pulse-Code Modulation (PCM) uncompressed audio recording URLs and caller
Automatic Number Identification (ANI) phone numbers.
"""

import logging
from typing import Any

from src.data_models.raw_ingress import IvrIngressPayload

logger = logging.getLogger(__name__)


class IvrConnector:
    """Processes IVR voice SIP gateway streams and passes canonical ingress payload."""

    async def process_call_session(self, payload: dict[str, Any]) -> IvrIngressPayload:
        """Validates and processes raw IVR telephony payload into canonical IvrIngressPayload.

        Args:
            payload: Raw dict payload received from SIP telephony gateway.

        Returns:
            Validated IvrIngressPayload.
        """
        validated_payload = IvrIngressPayload.model_validate(payload)

        logger.info(
            "Validated IVR call session for session=%s, duration=%ss",
            validated_payload.session_id,
            validated_payload.duration_seconds,
        )
        return validated_payload
