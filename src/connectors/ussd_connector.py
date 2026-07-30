"""Layer 1 USSD Menu Edge Connector (Layer 1 -> Layer 2).

See: decisions/step2.0_canonical_domain_schemas.md#ussd-menu-ingress-payload

Processes incoming Unstructured Supplementary Service Data (USSD) Signaling System No. 7 (SS7) /
Signaling Transport (SIGTRAN) carrier menu signaling payloads, validating shortcode patterns and
concatenated user digit selections.
"""

import logging
from typing import Any

from src.data_models.raw_ingress import UssdIngressPayload

logger = logging.getLogger(__name__)


class UssdConnector:
    """Processes USSD menu signaling codes and passes canonical ingress payload."""

    async def process_ussd_session(self, payload: UssdIngressPayload | dict[str, Any]) -> UssdIngressPayload:
        """Validates and processes raw USSD menu payload into canonical UssdIngressPayload.

        Args:
            payload: Raw dict or pre-parsed UssdIngressPayload instance.

        Returns:
            Validated UssdIngressPayload.
        """
        if isinstance(payload, dict):
            validated_payload = UssdIngressPayload.model_validate(payload)
        else:
            validated_payload = payload

        logger.info(
            "Processed USSD session for session=%s, service_code=%s, selections=%s",
            validated_payload.session_id,
            validated_payload.ussd_service_code,
            validated_payload.ussd_user_digit_selection,
        )
        return validated_payload
