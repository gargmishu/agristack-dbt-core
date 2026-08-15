"""Layer 2 Payload Canonicalizer (Layer 2 -> Layer 3 Transport Shim).

Transforms raw channel-specific ingress payloads (WhatsApp, IVR, USSD, SMS) into normalized,
zero-PII PublicAgentStandardizedIntakePayload contracts ready for Layer 3 Intake Gateway.

See: decisions/step2.0_canonical_domain_schemas.md (Section 4.2)
"""

from src.data_models.common import (
    ChannelType,
    LanguageLocale,
    PayloadType,
    StructureLevel,
)
from src.data_models.public_agent import PublicAgentStandardizedIntakePayload
from src.data_models.raw_ingress import (
    IvrIngressPayload,
    SmsIngressPayload,
    UssdIngressPayload,
    WhatsAppIngressPayload,
)
from src.gateway.pii_purge_guard import PiiPurgeGuard
from src.gateway.zero_trust_identity_tokenizer import ZeroTrustIdentityTokenizer

IngressPayloadUnion = (
    WhatsAppIngressPayload | IvrIngressPayload | UssdIngressPayload | SmsIngressPayload
)


class PayloadCanonicalizer:
    """Canonicalizes raw carrier ingress payloads into Layer 3 intake payloads."""

    def __init__(self, tokenizer: ZeroTrustIdentityTokenizer) -> None:
        """Initializes canonicalizer with an explicit identity tokenizer."""
        self._tokenizer = tokenizer

    @classmethod
    def from_env(cls) -> "PayloadCanonicalizer":
        """Factory method to instantiate canonicalizer using environment configured tokenizer."""
        return cls(tokenizer=ZeroTrustIdentityTokenizer.from_env())

    def canonicalize(
        self,
        payload: IngressPayloadUnion,
        language_locale: LanguageLocale = LanguageLocale.HINDI,
    ) -> PublicAgentStandardizedIntakePayload:
        """Canonicalizes any raw ingress payload into PublicAgentStandardizedIntakePayload.

        Args:
            payload: WhatsAppIngressPayload, IvrIngressPayload, UssdIngressPayload,
                or SmsIngressPayload.
            language_locale: Target BCP-47 language code (defaults to hi-IN).

        Returns:
            PublicAgentStandardizedIntakePayload normalized for Layer 3 Intake Gateway.
        """
        if isinstance(payload, WhatsAppIngressPayload):
            tokenized_id = self._tokenizer.tokenize_phone_number(payload.originating_phone_number)
            return self._canonicalize_whatsapp(payload, tokenized_id, language_locale)
        elif isinstance(payload, IvrIngressPayload):
            tokenized_id = self._tokenizer.tokenize_phone_number(payload.originating_phone_number)
            return self._canonicalize_ivr(payload, tokenized_id, language_locale)
        elif isinstance(payload, UssdIngressPayload):
            tokenized_id = self._tokenizer.tokenize_phone_number(payload.originating_phone_number)
            return self._canonicalize_ussd(payload, tokenized_id, language_locale)
        elif isinstance(payload, SmsIngressPayload):
            tokenized_id = self._tokenizer.tokenize_phone_number(payload.originating_phone_number)
            return self._canonicalize_sms(payload, tokenized_id, language_locale)
        else:
            raise ValueError(f"Unsupported ingress payload type: {type(payload)}")

    def _canonicalize_whatsapp(
        self,
        payload: WhatsAppIngressPayload,
        tokenized_id: str,
        language_locale: LanguageLocale,
    ) -> PublicAgentStandardizedIntakePayload:
        if payload.payload_type == PayloadType.AUDIO:
            unprocessed_content = str(payload.audio_recording_url)
            structure_level = StructureLevel.FREE_TEXT
        else:
            assert payload.text_body is not None  # Guaranteed by WhatsAppIngressPayload validator
            unprocessed_content = PiiPurgeGuard.redact_all(
                payload.text_body, session_id=payload.session_id
            )
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
        language_locale: LanguageLocale,
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
        language_locale: LanguageLocale,
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

    def _canonicalize_sms(
        self,
        payload: SmsIngressPayload,
        tokenized_id: str,
        language_locale: LanguageLocale,
    ) -> PublicAgentStandardizedIntakePayload:
        unprocessed_content = PiiPurgeGuard.redact_all(
            payload.text_body, session_id=payload.session_id
        )
        return PublicAgentStandardizedIntakePayload(
            session_id=payload.session_id,
            tokenized_citizen_id=tokenized_id,
            channel_type=ChannelType.SMS,
            payload_type=PayloadType.TEXT,
            structure_level=StructureLevel.FREE_TEXT,
            language_locale=language_locale,
            unprocessed_input_content=unprocessed_content,
            received_at=payload.received_at,
        )
