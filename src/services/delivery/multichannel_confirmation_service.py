"""Adaptive Multichannel Confirmation Delivery Service (Step 3.5 / Step 12).

Formats and dispatches final transaction receipts, caseworker escalation tickets,
or conversational re-prompts back to citizens across WhatsApp, IVR Voice, USSD, and SMS.

See: decisions/step3.5_adaptive_multichannel_confirmation_delivery.md
See: roadmap.md (Phase 3 Step 3.5)
"""

import logging
from datetime import UTC, datetime
from typing import Any

from pydantic import HttpUrl

from src.config import (
    DEFAULT_SMS_GATEWAY,
    get_helpline_number,
    get_sms_gateway_id,
)
from src.connectors import IvrConnector, UssdConnector, WhatsAppConnector
from src.data_models.common import (
    ChannelType,
    DeliveryStatus,
)
from src.data_models.delivery import (
    MAX_USSD_CHARACTERS,
    ConfirmationRequestPayload,
    OutboundConfirmationPayload,
)
from src.services.ai.bhashini_service import BhashiniService

logger = logging.getLogger(__name__)


class MultichannelConfirmationService:
    """Outbound confirmation dispatch engine generating channel-adapted notifications.

    Translates governance outcomes, payment clearing IDs, and caseworker escalation
    tickets into channel-native formats (Rich WhatsApp Markdown cards, Bhashini TTS voice
    recordings, compact 160-character USSD strings, and transactional SMS).

    See: decisions/step3.5_adaptive_multichannel_confirmation_delivery.md
    """

    def __init__(
        self,
        bhashini_service: BhashiniService | None = None,
        whatsapp_connector: WhatsAppConnector | None = None,
        ivr_connector: IvrConnector | None = None,
        ussd_connector: UssdConnector | None = None,
        sms_gateway_id: str = DEFAULT_SMS_GATEWAY,
    ) -> None:
        """Initializes MultichannelConfirmationService with injected dependencies.

        Args:
            bhashini_service: Optional BhashiniService instance for TTS voice synthesis.
            whatsapp_connector: Optional WhatsApp connector instance.
            ivr_connector: Optional IVR voice connector instance.
            ussd_connector: Optional USSD signaling connector instance.
            sms_gateway_id: Configured SMS carrier gateway identifier.
        """
        self._bhashini_service = bhashini_service or BhashiniService()
        self._whatsapp_connector = whatsapp_connector or WhatsAppConnector()
        self._ivr_connector = ivr_connector or IvrConnector()
        self._ussd_connector = ussd_connector or UssdConnector()
        self._sms_gateway_id = sms_gateway_id

    @classmethod
    def from_env(cls) -> "MultichannelConfirmationService":
        """Factory method instantiating MultichannelConfirmationService from environment configs."""
        return cls(
            bhashini_service=BhashiniService(),
            whatsapp_connector=WhatsAppConnector.from_env(),
            ivr_connector=IvrConnector.from_env(),
            ussd_connector=UssdConnector.from_env(),
            sms_gateway_id=get_sms_gateway_id(),
        )

    def _format_whatsapp_message(self, request: ConfirmationRequestPayload) -> str:
        """Formats rich WhatsApp markdown card message."""
        if request.governance_action.is_approval:
            txn = request.disbursement_txn_id or "TXN-PENDING"
            return (
                "🌾 *AgriStack Sovereign Relief Confirmation*\n\n"
                "Your crop loss subsidy claim has been *APPROVED*.\n\n"
                f"• *Transaction ID:* `{txn}`\n"
                "• *Status:* Direct Benefit Transfer (DBT) clearing initiated.\n\n"
                "The funds will be credited directly to your Aadhaar-linked bank account."
            )
        if request.governance_action.is_review:
            case = request.escalation_case_id or "SPP-CASE-PENDING"
            return (
                "📋 *AgriStack Claim Staged for Review*\n\n"
                "Your application requires verification by a District Agricultural Officer.\n\n"
                f"• *Incident Case ID:* `{case}`\n"
                "• *Status:* Assigned to verification queue.\n\n"
                "You will receive an update once the officer review is completed."
            )
        if request.governance_action.is_rejection:
            reason = request.rejection_reason or "Policy exclusion or eligibility mismatch"
            helpline = get_helpline_number()
            return (
                "❌ *AgriStack Claim Determination*\n\n"
                "Your subsidy application could not be approved at this time.\n\n"
                f"• *Reason:* {reason}\n"
                f"• *Helpline:* Dial toll-free {helpline} to file an appeal or inquiry."
            )
        # REQUEST_MORE_INFO / Clarification
        entity = request.missing_entity or "required domain details"
        return (
            "ℹ️ *AgriStack Clarification Needed*\n\n"
            f"Please provide your *{entity}* to proceed with your claim.\n\n"
            "Reply directly to this message with the requested details."
        )

    def _format_spoken_voice_text(self, request: ConfirmationRequestPayload) -> str:
        """Formats vernacular text string for Bhashini Text-To-Speech (TTS) synthesis."""
        is_hindi = str(request.language_locale).startswith("hi")
        if request.governance_action.is_approval:
            txn = request.disbursement_txn_id or (
                "sankhya uplabdh nahi" if is_hindi else "unavailable"
            )
            return (
                f"Aapka fasal rahat aavedan swikrit ho gaya hai. Transaction sankhya hai {txn}."
                if is_hindi
                else f"Your crop loss subsidy claim is approved. Transaction reference is {txn}."
            )
        if request.governance_action.is_review:
            case = request.escalation_case_id or (
                "ticket uplabdh nahi" if is_hindi else "unavailable"
            )
            return (
                "Aapka aavedan krishi adhikari ke paas jaanch ke liye bhej diya gaya hai. "
                f"Ticket sankhya hai {case}."
                if is_hindi
                else (
                    "Your application is forwarded to the district officer for review. "
                    f"Ticket number is {case}."
                )
            )
        if request.governance_action.is_rejection:
            reason = request.rejection_reason or (
                "yogyata niyam" if is_hindi else "policy guidelines"
            )
            return (
                f"Aapka aavedan aswikrit kiya gaya hai. Karan hai: {reason}."
                if is_hindi
                else f"Your application could not be approved due to: {reason}."
            )
        # REQUEST_MORE_INFO
        entity = request.missing_entity or ("vivaran" if is_hindi else "details")
        return (
            f"Kripya apna {entity} batayein taaki aavedan aage badhaya ja sake."
            if is_hindi
            else f"Please provide your {entity} to complete your claim."
        )

    def _format_ussd_message(self, request: ConfirmationRequestPayload) -> str:
        """Formats compact USSD plain text string strictly under 160 characters."""
        if request.governance_action.is_approval:
            txn = request.disbursement_txn_id or "PENDING"
            msg = f"AgriStack: Claim Approved. Txn: {txn}. DBT initiated."
        elif request.governance_action.is_review:
            case = request.escalation_case_id or "PENDING"
            msg = f"AgriStack: Claim Under Review. Ticket: {case}. Officer review pending."
        elif request.governance_action.is_rejection:
            reason = (request.rejection_reason or "Ineligible")[:30]
            helpline = get_helpline_number()
            msg = f"AgriStack: Claim Rejected ({reason}). Help: {helpline}."
        else:
            entity = (request.missing_entity or "details")[:30]
            msg = f"AgriStack: Missing {entity}. Reply to update."

        # Enforce hard 160 character boundary
        return msg[:MAX_USSD_CHARACTERS]

    def _format_sms_message(self, request: ConfirmationRequestPayload) -> str:
        """Formats concise transactional SMS message."""
        if request.governance_action.is_approval:
            txn = request.disbursement_txn_id or "PENDING"
            return (
                f"AgriStack: Your subsidy claim is approved. Txn ID: {txn}. "
                "Benefit sent via DBT to linked account."
            )
        if request.governance_action.is_review:
            case = request.escalation_case_id or "PENDING"
            return (
                f"AgriStack: Your claim is under review. Incident Ticket: {case}. "
                "Updates will follow."
            )
        if request.governance_action.is_rejection:
            reason = request.rejection_reason or "Ineligible"
            helpline = get_helpline_number()
            return (
                f"AgriStack: Your subsidy claim was rejected ({reason}). "
                f"Call toll-free {helpline} for queries."
            )
        entity = request.missing_entity or "required details"
        return f"AgriStack: Clarification required for {entity}. Please submit details to proceed."

    async def prepare_confirmation(
        self, request: ConfirmationRequestPayload
    ) -> OutboundConfirmationPayload:
        """Prepares channel-adapted OutboundConfirmationPayload with synthesized audio if voice.

        Args:
            request: Validated ConfirmationRequestPayload specifying channel, action, and fields.

        Returns:
            Validated OutboundConfirmationPayload ready for channel transmission.
        """
        logger.info(
            "Preparing outbound confirmation for session=%s, channel=%s, action=%s, locale=%s",
            request.session_id,
            request.channel_type,
            request.governance_action,
            request.language_locale,
        )

        audio_playback_url: HttpUrl | None = None

        if request.channel_type == ChannelType.WHATSAPP:
            message = self._format_whatsapp_message(request)
        elif request.channel_type == ChannelType.IVR_VOICE:
            spoken_text = self._format_spoken_voice_text(request)
            raw_url = await self._bhashini_service.synthesize_speech(
                spoken_text, str(request.language_locale)
            )
            audio_playback_url = HttpUrl(raw_url)
            message = spoken_text
        elif request.channel_type == ChannelType.USSD:
            message = self._format_ussd_message(request)
        else:  # SMS
            message = self._format_sms_message(request)

        return OutboundConfirmationPayload(
            session_id=request.session_id,
            channel_type=request.channel_type,
            language_locale=request.language_locale,
            governance_action=request.governance_action,
            delivery_status=DeliveryStatus.DELIVERED,
            formatted_message=message,
            audio_playback_url=audio_playback_url,
            disbursement_txn_id=request.disbursement_txn_id,
            escalation_case_id=request.escalation_case_id,
            delivered_at=datetime.now(UTC),
        )

    async def dispatch_confirmation(self, request: ConfirmationRequestPayload) -> dict[str, Any]:
        """Prepares and dispatches confirmation through the appropriate edge connector.

        Args:
            request: Validated ConfirmationRequestPayload specifying channel and determination.

        Returns:
            Dict containing outbound confirmation payload and connector transmission acknowledgment.
        """
        payload = await self.prepare_confirmation(request)

        transmission_ack: dict[str, Any]
        if request.channel_type == ChannelType.WHATSAPP:
            transmission_ack = await self._whatsapp_connector.send_outbound_confirmation(payload)
        elif request.channel_type == ChannelType.IVR_VOICE:
            transmission_ack = await self._ivr_connector.send_outbound_confirmation(payload)
        elif request.channel_type == ChannelType.USSD:
            transmission_ack = await self._ussd_connector.send_outbound_confirmation(payload)
        else:  # SMS
            transmission_ack = {
                "sms_gateway": self._sms_gateway_id,
                "session_id": payload.session_id,
                "status": payload.delivery_status,
                "message": payload.formatted_message,
            }

        logger.info(
            "Dispatched confirmation for session=%s across channel=%s with status=%s",
            payload.session_id,
            payload.channel_type,
            payload.delivery_status,
        )
        return {
            "payload": payload,
            "transmission_ack": transmission_ack,
        }
