from src.models.common import ApplicationIntent, DomainEntityKey
from src.models.governance import ExtractedEntityPayload


def test_extracted_entity_adversarial_zeroing() -> None:
    payload = ExtractedEntityPayload(
        application_intent=ApplicationIntent.APPLY_SUBSIDY,
        ai_confidence_score=0.95,  # High score initially passed
        domain_entities={DomainEntityKey.DISTRICT: "Ambala"},
        is_adversarial_attempt=True,  # Injection flagged
    )
    # Validation must zero out confidence score and wipe entities
    assert payload.ai_confidence_score == 0.0
    assert payload.domain_entities == {}
    assert payload.is_adversarial_attempt is True
