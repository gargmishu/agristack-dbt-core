"""Unit tests for NotificationDispatchResult data model."""

from datetime import UTC, datetime

from src.data_models.common import (
    ChannelType,
    GovernanceAction,
    LanguageLocale,
    NotificationDeliveryStatus,
)
from src.data_models.notification import (
    NotificationDispatchResult,
    OutboundNotificationPayload,
    TransmissionAck,
)


def test_notification_dispatch_result_valid() -> None:
    payload = OutboundNotificationPayload(
        session_id="sess_12345678",
        channel_type=ChannelType.WHATSAPP,
        language_locale=LanguageLocale.ENGLISH,
        governance_action=GovernanceAction.AUTO_APPROVE,
        delivery_status=NotificationDeliveryStatus.DELIVERED,
        formatted_message="Claim Approved",
        disbursement_txn_id="TXN-2026-981245",
        delivered_at=datetime.now(UTC),
    )
    ack = TransmissionAck(
        interface_id="WHATSAPP_GATEWAY_DEFAULT",
        channel_type=ChannelType.WHATSAPP,
        session_id="sess_12345678",
        status=NotificationDeliveryStatus.DELIVERED,
        carrier_reference_id="wamid.12345",
    )
    result = NotificationDispatchResult(
        payload=payload,
        transmission_ack=ack,
    )
    assert result.payload.session_id == "sess_12345678"
    assert result.transmission_ack.interface_id == "WHATSAPP_GATEWAY_DEFAULT"
    assert result.transmission_ack.carrier_reference_id == "wamid.12345"
