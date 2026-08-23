"""Adaptive Multichannel Notification Delivery Service (Step 3.5 / Step 12).

Formats and dispatches final transaction receipts, caseworker escalation tickets,
or conversational re-prompts back to citizens across WhatsApp, IVR Voice, USSD, and SMS.

See: decisions/step3.5_adaptive_multichannel_confirmation_delivery.md
See: roadmap.md (Phase 3 Step 3.5)
"""

import logging
from datetime import UTC, datetime
from typing import Final

from pydantic import HttpUrl

from src.config import get_helpline_number
from src.connectors import (
    IvrConnector,
    SmsConnector,
    UssdConnector,
    WhatsAppConnector,
)
from src.data_models.common import (
    ChannelType,
    DomainEntityKey,
    NotificationDeliveryStatus,
)
from src.data_models.notification import (
    MAX_USSD_CHARACTERS,
    NotificationDispatchResult,
    NotificationRequestPayload,
    OutboundNotificationPayload,
    TransmissionAck,
)
from src.services.ai.bhashini_service import BhashiniService

logger = logging.getLogger(__name__)

_HINDI_ENTITY_LABELS: Final[dict[DomainEntityKey, str]] = {
    DomainEntityKey.DISTRICT: "zila",
    DomainEntityKey.TALUKA: "taluka ya tehsil",
    DomainEntityKey.VILLAGE: "gaon",
    DomainEntityKey.CROP_NAME: "fasal ka naam",
    DomainEntityKey.CROP_VARIETY: "fasal ki kism",
    DomainEntityKey.LAND_SIZE_ACRES: "zameen ka aakar (acres)",
    DomainEntityKey.SUBSIDY_SCHEME_ID: "yojana ID",
    DomainEntityKey.SURVEY_NUMBER: "khasra sankhya",
    DomainEntityKey.BANK_ACCOUNT_LAST4: "bank khate ke aakhiri 4 ank",
}


class MultichannelNotificationService:
    """Outbound notification engine adapting messages and coordinating multi-channel delivery.

    Renders channel-specific message formats and dispatches them to configured carrier
    connectors:
    - WhatsApp: Renders structured Markdown cards with status badges and reference keys.
    - IVR Voice: Formats phonetic vernacular text and coordinates TTS audio synthesis.
    - USSD & SMS: Generates plain-text strings constrained to 160 characters.

    Operations:
    - `prepare_and_dispatch`: Constructs an `OutboundNotificationPayload` and dispatches it
      via
      the target connector, returning a `NotificationDispatchResult`.

    See: decisions/step3.5_adaptive_multichannel_confirmation_delivery.md
    """

    def __init__(
        self,
        bhashini_service: BhashiniService | None = None,
        whatsapp_connector: WhatsAppConnector | None = None,
        ivr_connector: IvrConnector | None = None,
        ussd_connector: UssdConnector | None = None,
        sms_connector: SmsConnector | None = None,
    ) -> None:
        """Initializes multi-channel notification delivery service with injected dependencies.

        Args:
            bhashini_service: Optional speech synthesis service instance.
            whatsapp_connector: Optional messaging connector instance.
            ivr_connector: Optional telephony voice connector instance.
            ussd_connector: Optional signaling connector instance.
            sms_connector: Optional carrier SMS connector instance.
        """
        self._bhashini_service = bhashini_service or BhashiniService()
        self._whatsapp_connector = whatsapp_connector or WhatsAppConnector()
        self._ivr_connector = ivr_connector or IvrConnector()
        self._ussd_connector = ussd_connector or UssdConnector()
        self._sms_connector = sms_connector or SmsConnector()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    async def prepare_notification(
        self, request: NotificationRequestPayload
    ) -> OutboundNotificationPayload:
        """Prepares channel-adapted OutboundNotificationPayload with synthesized audio if voice.

        Args:
            request: Validated NotificationRequestPayload specifying channel, action, and
            fields.

        Returns:
            Validated OutboundNotificationPayload ready for channel transmission.
        """
        logger.info(
            "Preparing outbound notification for session=%s, channel=%s, action=%s, locale=%s",
            request.session_id,
            request.channel_type,
            request.governance_action,
            request.language_locale,
        )

        audio_playback_url: HttpUrl | None = None

        if request.channel_type == ChannelType.WHATSAPP:
            message = self._format_rich_card(request)
        elif request.channel_type == ChannelType.IVR_VOICE:
            spoken_text = self._format_spoken_voice_text(request)
            raw_url = await self._bhashini_service.synthesize_speech(
                spoken_text, str(request.language_locale)
            )
            audio_playback_url = HttpUrl(raw_url)
            message = spoken_text
        else:  # SMS and USSD (both use compact plain text <=160 chars)
            message = self._format_plain_text(request)

        return OutboundNotificationPayload(
            session_id=request.session_id,
            channel_type=request.channel_type,
            language_locale=request.language_locale,
            governance_action=request.governance_action,
            delivery_status=NotificationDeliveryStatus.DELIVERED,
            formatted_message=message,
            audio_playback_url=audio_playback_url,
            disbursement_txn_id=request.disbursement_txn_id,
            escalation_case_id=request.escalation_case_id,
            delivered_at=datetime.now(UTC),
        )

    async def dispatch_notification(
        self, request: NotificationRequestPayload
    ) -> NotificationDispatchResult:
        """Prepares and dispatches notification through the appropriate edge connector.

        Args:
            request: Validated NotificationRequestPayload specifying channel and
            determination.

        Returns:
            NotificationDispatchResult with payload and carrier TransmissionAck receipt.
        """
        payload = await self.prepare_notification(request)

        transmission_ack: TransmissionAck
        if request.channel_type == ChannelType.WHATSAPP:
            transmission_ack = await self._whatsapp_connector.send_outbound_notification(payload)
        elif request.channel_type == ChannelType.IVR_VOICE:
            transmission_ack = await self._ivr_connector.send_outbound_notification(payload)
        elif request.channel_type == ChannelType.USSD:
            transmission_ack = await self._ussd_connector.send_outbound_notification(payload)
        else:  # SMS
            transmission_ack = await self._sms_connector.send_outbound_notification(payload)

        logger.info(
            "Dispatched notification for session=%s across channel=%s with status=%s",
            payload.session_id,
            payload.channel_type,
            payload.delivery_status,
        )
        return NotificationDispatchResult(
            payload=payload,
            transmission_ack=transmission_ack,
        )

    # -------------------------------------------------------------------------
    # Private Channel Formatters & Label Helpers
    # -------------------------------------------------------------------------

    def _format_rich_card(self, request: NotificationRequestPayload) -> str:
        """Formats rich WhatsApp markdown card message.

        Args:
            request: Notification request containing action and outcome details.

        Returns:
            Formatted Markdown card string for WhatsApp channel.
        """
        if request.governance_action.is_approval:
            return (
                "🌾 *AgriStack Sovereign Relief Confirmation*\n\n"
                "Your crop loss subsidy claim has been *APPROVED*.\n\n"
                f"• *Transaction ID:* `{request.disbursement_txn_id}`\n"
                "• *Status:* Direct Benefit Transfer (DBT) clearing initiated.\n\n"
                "The funds will be credited directly to your Aadhaar-linked bank account."
            )
        if request.governance_action.is_review:
            return (
                "📋 *AgriStack Claim Staged for Review*\n\n"
                "Your application requires verification by a District Agricultural Officer.\n\n"
                f"• *Incident Case ID:* `{request.escalation_case_id}`\n"
                "• *Status:* Assigned to verification queue.\n\n"
                "You will receive an update once the officer review is completed."
            )
        if request.governance_action.is_rejection:
            helpline = get_helpline_number()
            return (
                "❌ *AgriStack Claim Determination*\n\n"
                "Your subsidy application could not be approved at this time.\n\n"
                f"• *Reason:* {request.rejection_reason}\n"
                f"• *Helpline:* Dial toll-free {helpline} to file an appeal or inquiry."
            )
        # REQUEST_MORE_INFO / Clarification
        entity_label = self._format_entity_label(request.missing_entity, is_hindi=False)
        return (
            "ℹ️ *AgriStack Clarification Needed*\n\n"
            f"Please provide your *{entity_label}* to proceed with your claim.\n\n"
            "Reply directly to this message with the requested details."
        )

    def _format_spoken_voice_text(self, request: NotificationRequestPayload) -> str:
        """Formats vernacular text string for Bhashini Text-To-Speech (TTS) synthesis.

        Args:
            request: Notification request containing action and locale details.

        Returns:
            Phonetically formatted vernacular text string for voice synthesis.
        """
        is_hindi = request.language_locale.is_hindi
        if request.governance_action.is_approval:
            return (
                f"Aapka fasal rahat aavedan swikrit ho gaya hai. "
                f"Transaction sankhya hai {request.disbursement_txn_id}."
                if is_hindi
                else f"Your crop loss subsidy claim is approved. "
                f"Transaction reference is {request.disbursement_txn_id}."
            )
        if request.governance_action.is_review:
            return (
                "Aapka aavedan krishi adhikari ke paas jaanch ke liye bhej diya gaya hai. "
                f"Ticket sankhya hai {request.escalation_case_id}."
                if is_hindi
                else "Your application is forwarded to the district officer for review. "
                f"Ticket number is {request.escalation_case_id}."
            )
        if request.governance_action.is_rejection:
            return (
                f"Aapka aavedan aswikrit kiya gaya hai. Karan hai: {request.rejection_reason}."
                if is_hindi
                else f"Your application could not be approved due to: {request.rejection_reason}."
            )
        # REQUEST_MORE_INFO
        entity_label = self._format_entity_label(request.missing_entity, is_hindi=is_hindi)
        return (
            f"Kripya apna {entity_label} batayein taaki aavedan aage badhaya ja sake."
            if is_hindi
            else f"Please provide your {entity_label} to complete your claim."
        )

    def _format_plain_text(self, request: NotificationRequestPayload) -> str:
        """Formats compact plain text string strictly under 160 characters for SMS and USSD.

        Args:
            request: Notification request containing action and outcome details.

        Returns:
            Concise text string strictly bounded to maximum 160 characters.
        """
        if request.governance_action.is_approval:
            msg = f"AgriStack: Claim Approved. Txn: {request.disbursement_txn_id}. DBT initiated."
        elif request.governance_action.is_review:
            msg = (
                f"AgriStack: Claim Under Review. Ticket: {request.escalation_case_id}. "
                "Officer review pending."
            )
        elif request.governance_action.is_rejection:
            helpline = get_helpline_number()
            msg = f"AgriStack: Claim Rejected ({request.rejection_reason}). Help: {helpline}."
        else:
            entity_label = self._format_entity_label(request.missing_entity, is_hindi=False)
            msg = f"AgriStack: Missing {entity_label}. Reply to update."

        # Enforce hard 160 character boundary
        return msg[:MAX_USSD_CHARACTERS]

    @staticmethod
    def _format_entity_label(entity: DomainEntityKey | None, is_hindi: bool = False) -> str:
        """Returns human-readable, channel-adapted label for a DomainEntityKey.

        Args:
            entity: Domain entity key to format, or None.
            is_hindi: Whether to format the label in Hindi vernacular.

        Returns:
            Channel-adapted human-readable string label.
        """
        if entity is None:
            return "kripya vivaran" if is_hindi else "required details"
        if is_hindi:
            return _HINDI_ENTITY_LABELS.get(entity, entity.value.replace("_", " "))
        return entity.value.replace("_", " ")
