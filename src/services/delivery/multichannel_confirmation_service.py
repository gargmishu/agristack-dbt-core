"""Adaptive Multichannel Confirmation Delivery Service (Step 3.5 / Step 12).

Formats and dispatches final transaction receipts, caseworker escalation tickets,
or conversational re-prompts back to citizens across WhatsApp, IVR Voice, USSD, and SMS.

See: decisions/step3.5_adaptive_multichannel_confirmation_delivery.md
See: roadmap.md (Phase 3 Step 3.5)
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic import HttpUrl

from src.data_models.common import (
    ChannelType,
    DeliveryStatus,
    GovernanceAction,
    LanguageLocale,
)
from src.data_models.delivery import (
    MAX_USSD_CHARACTERS,
    OutboundConfirmationPayload,
)
from src.services.ai.bhashini_service import BhashiniService

logger = logging.getLogger(__name__)

APPROVE_ACTIONS = {
    GovernanceAction.AUTO_APPROVE,
    GovernanceAction.AUTOMATED_PAYOUT,
    GovernanceAction.MANUAL_APPROVE,
}
REVIEW_ACTIONS = {
    GovernanceAction.ROUTE_FOR_MANUAL_REVIEW,
    GovernanceAction.HUMAN_REVIEW,
}
REJECT_ACTIONS = {
    GovernanceAction.AUTO_REJECT,
    GovernanceAction.MANUAL_REJECT,
}


@dataclass(frozen=True)
class ConfirmationRequest:
    """Input request context for generating outbound multichannel confirmation."""

    session_id: str
    channel_type: ChannelType
    governance_action: GovernanceAction
    language_locale: LanguageLocale = LanguageLocale.ENGLISH
    disbursement_txn_id: str | None = None
    escalation_case_id: str | None = None
    rejection_reason: str | None = None
    missing_entity: str | None = None


class MultichannelConfirmationService:
    """Outbound confirmation dispatch engine generating channel-adapted notifications.

    Translates governance outcomes, payment clearing IDs, and caseworker escalation
    tickets into channel-native formats (Rich WhatsApp Markdown cards, Bhashini TTS voice
    recordings, compact 160-character USSD strings, and transactional SMS).

    See: decisions/step3.5_adaptive_multichannel_confirmation_delivery.md
    """

    def __init__(self, bhashini_service: BhashiniService) -> None:
        """Initializes MultichannelConfirmationService with explicit BhashiniService dependency.

        Args:
            bhashini_service: Injected BhashiniService instance for TTS voice synthesis.
        """
        self._bhashini_service = bhashini_service

    @classmethod
    def from_default(cls) -> "MultichannelConfirmationService":
        """Factory method instantiating MultichannelConfirmationService with default services."""
        return cls(bhashini_service=BhashiniService())

    def _format_whatsapp_message(self, request: ConfirmationRequest) -> str:
        """Formats rich WhatsApp markdown card message."""
        if request.governance_action in APPROVE_ACTIONS:
            txn = request.disbursement_txn_id or "TXN-PENDING"
            return (
                "🌾 *AgriStack Sovereign Relief Confirmation*\n\n"
                "Your crop loss subsidy claim has been *APPROVED*.\n\n"
                f"• *Transaction ID:* `{txn}`\n"
                "• *Status:* Direct Benefit Transfer (DBT) clearing initiated.\n\n"
                "The funds will be credited directly to your Aadhaar-linked bank account."
            )
        if request.governance_action in REVIEW_ACTIONS:
            case = request.escalation_case_id or "SPP-CASE-PENDING"
            return (
                "📋 *AgriStack Claim Staged for Review*\n\n"
                "Your application requires verification by a District Agricultural Officer.\n\n"
                f"• *Incident Case ID:* `{case}`\n"
                "• *Status:* Assigned to verification queue.\n\n"
                "You will receive an update once the officer review is completed."
            )
        if request.governance_action in REJECT_ACTIONS:
            reason = request.rejection_reason or "Policy exclusion or eligibility mismatch"
            return (
                "❌ *AgriStack Claim Determination*\n\n"
                "Your subsidy application could not be approved at this time.\n\n"
                f"• *Reason:* {reason}\n"
                "• *Helpline:* Dial toll-free 1800-180-1551 to file an appeal or inquiry."
            )
        # REQUEST_MORE_INFO / Clarification
        entity = request.missing_entity or "required domain details"
        return (
            "ℹ️ *AgriStack Clarification Needed*\n\n"
            f"Please provide your *{entity}* to proceed with your claim.\n\n"
            "Reply directly to this message with the requested details."
        )

    def _format_spoken_voice_text(self, request: ConfirmationRequest) -> str:
        """Formats vernacular text string for Bhashini Text-To-Speech (TTS) synthesis."""
        is_hindi = str(request.language_locale).startswith("hi")
        if request.governance_action in APPROVE_ACTIONS:
            txn = request.disbursement_txn_id or (
                "sankhya uplabdh nahi" if is_hindi else "unavailable"
            )
            return (
                f"Aapka fasal rahat aavedan swikrit ho gaya hai. Transaction sankhya hai {txn}."
                if is_hindi
                else f"Your crop loss subsidy claim is approved. Transaction reference is {txn}."
            )
        if request.governance_action in REVIEW_ACTIONS:
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
        if request.governance_action in REJECT_ACTIONS:
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

    def _format_ussd_message(self, request: ConfirmationRequest) -> str:
        """Formats compact USSD plain text string strictly under 160 characters."""
        if request.governance_action in APPROVE_ACTIONS:
            txn = request.disbursement_txn_id or "PENDING"
            msg = f"AgriStack: Claim Approved. Txn: {txn}. DBT initiated."
        elif request.governance_action in REVIEW_ACTIONS:
            case = request.escalation_case_id or "PENDING"
            msg = f"AgriStack: Claim Under Review. Ticket: {case}. Officer review pending."
        elif request.governance_action in REJECT_ACTIONS:
            reason = (request.rejection_reason or "Ineligible")[:40]
            msg = f"AgriStack: Claim Rejected ({reason}). Help: 18001801551."
        else:
            entity = (request.missing_entity or "details")[:30]
            msg = f"AgriStack: Missing {entity}. Reply to update."

        # Enforce hard 160 character boundary
        return msg[:MAX_USSD_CHARACTERS]

    def _format_sms_message(self, request: ConfirmationRequest) -> str:
        """Formats concise transactional SMS message."""
        if request.governance_action in APPROVE_ACTIONS:
            txn = request.disbursement_txn_id or "PENDING"
            return (
                f"AgriStack: Your subsidy claim is approved. Txn ID: {txn}. "
                "Benefit sent via DBT to linked account."
            )
        if request.governance_action in REVIEW_ACTIONS:
            case = request.escalation_case_id or "PENDING"
            return (
                f"AgriStack: Your claim is under review. Incident Ticket: {case}. "
                "Updates will follow."
            )
        if request.governance_action in REJECT_ACTIONS:
            reason = request.rejection_reason or "Ineligible"
            return (
                f"AgriStack: Your subsidy claim was rejected ({reason}). "
                "Call toll-free 1800-180-1551 for queries."
            )
        entity = request.missing_entity or "required details"
        return f"AgriStack: Clarification required for {entity}. Please submit details to proceed."

    async def prepare_confirmation(
        self, request: ConfirmationRequest
    ) -> OutboundConfirmationPayload:
        """Prepares channel-adapted OutboundConfirmationPayload with synthesized audio if voice.

        Args:
            request: Validated ConfirmationRequest specifying channel, action, and identifiers.

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
