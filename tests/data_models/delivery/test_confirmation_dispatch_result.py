"""Unit tests for ConfirmationDispatchResult data model."""

from datetime import UTC, datetime

from src.data_models.common import (
    ChannelType,
    DeliveryStatus,
    GovernanceAction,
    LanguageLocale,
)
from src.data_models.delivery import (
    ConfirmationDispatchResult,
    OutboundConfirmationPayload,
    TransmissionAck,
)


def test_confirmation_dispatch_result_valid() -> None:
    payload = OutboundConfirmationPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.WHATSAPP,
        language_locale=LanguageLocale.ENGLISH,
        governance_action=GovernanceAction.AUTO_APPROVE,
        delivery_status=DeliveryStatus.DELIVERED,
        formatted_message="Claim Approved",
        disbursement_txn_id="TXN-2026-981245",
        delivered_at=datetime.now(UTC),
    )
    ack = TransmissionAck(
        interface_id="WHATSAPP_GATEWAY_DEFAULT",
        channel_type=ChannelType.WHATSAPP,
        session_id="sess_12345678",
        status=DeliveryStatus.DELIVERED,
        message_id="wamid.12345",
        message="Claim Approved",
    )
    result = ConfirmationDispatchResult(
        payload=payload,
        transmission_ack=ack,
    )
    assert result.payload.session_id == "sess_12345678"
    assert result.transmission_ack.interface_id == "WHATSAPP_GATEWAY_DEFAULT"
    assert result.transmission_ack.message_id == "wamid.12345"
