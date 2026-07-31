from datetime import UTC, datetime

from src.data_models.common import ChannelType, PayloadType, StructureLevel
from src.data_models.public_agent import PublicAgentStandardizedIntakePayload
from src.public_agent import IntakeValidator


def test_intake_validator_dtmf_structured_bypass() -> None:
    validator = IntakeValidator()
    payload = PublicAgentStandardizedIntakePayload(
        session_id="sess_12345678",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        channel_type=ChannelType.USSD,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.DTMF_SELECTION,
        language_locale="hi-IN",
        unprocessed_input_content="1*2*9876543210",
        received_at=datetime.now(UTC),
    )

    result = validator.validate_intake(payload)
    assert result.is_valid is True
    assert result.requires_nlu_extraction is False
    assert "Structured input cleared" in result.validation_message


def test_intake_validator_free_text_requires_nlu() -> None:
    validator = IntakeValidator()
    payload = PublicAgentStandardizedIntakePayload(
        session_id="sess_12345678",
        tokenized_citizen_id="a1b2c3d4e5f60718293a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e",
        channel_type=ChannelType.WHATSAPP,
        payload_type=PayloadType.TEXT,
        structure_level=StructureLevel.FREE_TEXT,
        language_locale="hi-IN",
        unprocessed_input_content="Mera khet Karnal me hai aur fasal kharab ho gayi hai",
        received_at=datetime.now(UTC),
    )

    result = validator.validate_intake(payload)
    assert result.is_valid is True
    assert result.requires_nlu_extraction is True
    assert "Free-text input cleared" in result.validation_message
