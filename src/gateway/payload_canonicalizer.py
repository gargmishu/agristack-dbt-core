"""Layer 2 Payload Canonicalizer (Layer 2 -> Layer 3 Transport Shim).

Transforms raw channel-specific ingress payloads (WhatsApp, IVR, USSD) into normalized,
zero-PII PublicAgentStandardizedIntakePayload contracts ready for Layer 3 Intake Gateway.

See: decisions/step2.0_canonical_domain_schemas.md (Section 4.2)
"""

from src.data_models.common import ChannelType, PayloadType, StructureLevel
from src.data_models.public_agent import PublicAgentStandardizedIntakePayload
from src.data_models.raw_ingress import (
    IvrIngressPayload,
    UssdIngressPayload,
    WhatsAppIngressPayload,
)
from src.gateway.identity_tokenizer import ZeroTrustIdentityTokenizer

IngressPayloadUnion = (
    WhatsAppIngressPayload | IvrIngressPayload | UssdIngressPayload
)


class IngressCanonicalizer:
    """Canonicalizes raw carrier ingress payloads into Layer 3 intake payloads."""

    def __init__(self, tokenizer: ZeroTrustIdentityTokenizer | None = None) -> None:
        """Initializes canonicalizer with an identity tokenizer."""
        self._tokenizer = tokenizer or ZeroTrustIdentityTokenizer()

    def canonicalize(
        self,
        payload: IngressPayloadUnion,
        language_locale: str = "hi-IN",
    ) -> PublicAgentStandardizedIntakePayload:
        """Canonicalizes any raw ingress payload into PublicAgentStandardizedIntakePayload.

        Args:
            payload: WhatsAppIngressPayload, IvrIngressPayload, or UssdIngressPayload.
            language_locale: Target BCP-47 language code (defaults to hi-IN).

        Returns:
            PublicAgentStandardizedIntakePayload normalized for Layer 3 Intake Gateway.
        """
        tokenized_id = self._tokenizer.tokenize_phone_number(payload.originating_phone_number)

        if isinstance(payload, WhatsAppIngressPayload):
            return self._canonicalize_whatsapp(payload, tokenized_id, language_locale)
        elif isinstance(payload, IvrIngressPayload):
            return self._canonicalize_ivr(payload, tokenized_id, language_locale)
        elif isinstance(payload, UssdIngressPayload):
            return self._canonicalize_ussd(payload, tokenized_id, language_locale)
        else:
            raise ValueError(f"Unsupported ingress payload type: {type(payload)}")

    def _canonicalize_whatsapp(
        self,
        payload: WhatsAppIngressPayload,
        tokenized_id: str,
        language_locale: str,
    ) -> PublicAgentStandardizedIntakePayload:
        if payload.payload_type == PayloadType.AUDIO:
            unprocessed_content = str(payload.audio_recording_url)
            structure_level = StructureLevel.FREE_TEXT
        else:
            unprocessed_content = payload.text_body or ""
            structure_level = StructureLevel.FREE_TEXT

        return PublicAgentStandardizedIntakePayload(
            session_id=payload.session_id,
            tokenized_citizen_id=tokenized_id,
            channel_type=ChannelType.WHATSAPP,
            payload_type=payload.payload_type,
            structure_level=structure_level,
            language_locale=language_locale,
            unprocessed_input_content=unprocessed_content,
            received_at=payload.received_at,
        )

    def _canonicalize_ivr(
        self,
        payload: IvrIngressPayload,
        tokenized_id: str,
        language_locale: str,
    ) -> PublicAgentStandardizedIntakePayload:
        return PublicAgentStandardizedIntakePayload(
            session_id=payload.session_id,
            tokenized_citizen_id=tokenized_id,
            channel_type=ChannelType.IVR_VOICE,
            payload_type=PayloadType.AUDIO,
            structure_level=StructureLevel.FREE_TEXT,
            language_locale=language_locale,
            unprocessed_input_content=str(payload.audio_recording_url),
            received_at=payload.received_at,
        )

    def _canonicalize_ussd(
        self,
        payload: UssdIngressPayload,
        tokenized_id: str,
        language_locale: str,
    ) -> PublicAgentStandardizedIntakePayload:
        return PublicAgentStandardizedIntakePayload(
            session_id=payload.session_id,
            tokenized_citizen_id=tokenized_id,
            channel_type=ChannelType.USSD,
            payload_type=PayloadType.TEXT,
            structure_level=StructureLevel.DTMF_SELECTION,
            language_locale=language_locale,
            unprocessed_input_content=payload.ussd_user_digit_selection,
            received_at=payload.received_at,
        )
