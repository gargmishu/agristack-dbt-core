from datetime import UTC, datetime

from src.data_models.common import ChannelType, PayloadType, StructureLevel
from src.data_models.public_agent import PublicAgentStandardizedIntakePayload
from src.public_agent import IntakePayloadEvaluator

VALID_CITIZEN_TOKEN = "a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e"  # noqa: S105


def test_intake_payload_evaluator_dtmf_structured_bypass() -> None:
    evaluator = IntakePayloadEvaluator()
    payload = PublicAgentStandardizedIntakePayload(
        session_id="sess_12345678",
        tokenized_citizen_id=VALID_CITIZEN_TOKEN,
        channel_type=ChannelType.USSD,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.DTMF_SELECTION,
        language_locale="hi-IN",
        unprocessed_input_content="1*2*9876543210",
        received_at=datetime.now(UTC),
    )

    result = evaluator.evaluate_payload(payload)
    assert result.is_valid is True
    assert result.requires_nlu_extraction is False
    assert "Structured input cleared" in result.evaluation_message


def test_intake_payload_evaluator_free_text_requires_nlu() -> None:
    evaluator = IntakePayloadEvaluator()
    payload = PublicAgentStandardizedIntakePayload(
        session_id="sess_12345678",
        tokenized_citizen_id=VALID_CITIZEN_TOKEN,
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale="hi-IN",
        unprocessed_input_content="Mera khet Karnal me hai aur fasal kharab ho gayi hai",
        received_at=datetime.now(UTC),
    )

    result = evaluator.evaluate_payload(payload)
    assert result.is_valid is True
    assert result.requires_nlu_extraction is True
    assert "Free-text input cleared" in result.evaluation_message


def test_intake_payload_evaluator_empty_content_rejected() -> None:
    evaluator = IntakePayloadEvaluator()
    payload = PublicAgentStandardizedIntakePayload(
        session_id="sess_12345678",
        tokenized_citizen_id=VALID_CITIZEN_TOKEN,
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale="hi-IN",
        unprocessed_input_content="Valid before mutate",
        received_at=datetime.now(UTC),
    )
    object.__setattr__(payload, "unprocessed_input_content", "   ")

    result = evaluator.evaluate_payload(payload)
    assert result.is_valid is False
    assert result.requires_nlu_extraction is False
    assert "cannot be empty or whitespace-only" in result.evaluation_message
