import pytest

from src.transport import ZeroTrustIdentityTokenizer


def test_tokenizer_deterministic_output() -> None:
    tokenizer = ZeroTrustIdentityTokenizer(pepper_key="test_pepper_key")
    phone = "+919876543210"
    token1 = tokenizer.tokenize_phone_number(phone)
    token2 = tokenizer.tokenize_phone_number(phone)

    assert len(token1) == 64
    assert token1 == token2
    assert token1.isalnum()


def test_tokenizer_different_peppers_produce_different_tokens() -> None:
    tok1 = ZeroTrustIdentityTokenizer(pepper_key="pepper_1")
    tok2 = ZeroTrustIdentityTokenizer(pepper_key="pepper_2")
    phone = "+919876543210"

    assert tok1.tokenize_phone_number(phone) != tok2.tokenize_phone_number(phone)


def test_tokenizer_empty_identifier_raises() -> None:
    tokenizer = ZeroTrustIdentityTokenizer()
    with pytest.raises(ValueError) as exc:
        tokenizer.tokenize_citizen_id("   ")
    assert "cannot be empty or whitespace-only" in str(exc.value)
