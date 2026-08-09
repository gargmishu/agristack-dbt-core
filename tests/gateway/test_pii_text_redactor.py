"""Unit tests for Layer 2 PiiTextRedactor."""

from src.gateway.pii_text_redactor import PiiTextRedactor


def test_pii_text_redactor_redacts_indian_mobile_numbers() -> None:
    text = "Mera phone 9876543210 hai aur dusra 919876543211 hai."
    sanitized = PiiTextRedactor.redact_phone_numbers(text)
    assert "[REDACTED]" in sanitized
    assert "9876543210" not in sanitized
    assert "919876543211" not in sanitized


def test_pii_text_redactor_redacts_e164_numbers() -> None:
    text = "Contact me at +919876543210 or +14155552671."
    sanitized = PiiTextRedactor.redact_phone_numbers(text)
    assert "[REDACTED]" in sanitized
    assert "+919876543210" not in sanitized
    assert "+14155552671" not in sanitized


def test_pii_text_redactor_redacts_aadhaar_numbers() -> None:
    text = "Aadhaar 1234 5678 9012 or 123456789012."
    sanitized = PiiTextRedactor.redact_aadhaar_numbers(text)
    assert "[REDACTED]" in sanitized
    assert "1234 5678 9012" not in sanitized
    assert "123456789012" not in sanitized


def test_pii_text_redactor_redact_all() -> None:
    text = "Kisan Ramesh, phone +919876543210, Aadhaar 1234 5678 9012, 2 acre wheat damage."
    sanitized = PiiTextRedactor.redact_all(text, session_id="sess_test_123")
    assert "+919876543210" not in sanitized
    assert "1234 5678 9012" not in sanitized
    assert "wheat damage" in sanitized


def test_pii_text_redactor_handles_empty_and_whitespace() -> None:
    assert PiiTextRedactor.redact_all("") == ""
    assert PiiTextRedactor.redact_all("   ") == "   "
    clean_text = "Sirf gehu ki kheti hai."
    assert PiiTextRedactor.redact_all(clean_text) == clean_text
