import pytest

from src.gateway import ZeroTrustIdentityTokenizer

EXPECTED_TOKEN_LEN = 64


def test_tokenizer_deterministic_output() -> None:
    tokenizer = ZeroTrustIdentityTokenizer(pepper_key="test_pepper_key")
    phone = "+919876543210"
    token1 = tokenizer.tokenize_phone_number(phone)
    token2 = tokenizer.tokenize_phone_number(phone)

    assert len(token1) == EXPECTED_TOKEN_LEN
    assert token1 == token2
    assert token1.isalnum()


def test_tokenizer_different_peppers_produce_different_tokens() -> None:
    tok1 = ZeroTrustIdentityTokenizer(pepper_key="pepper_1")
    tok2 = ZeroTrustIdentityTokenizer(pepper_key="pepper_2")
    phone = "+919876543210"

    assert tok1.tokenize_phone_number(phone) != tok2.tokenize_phone_number(phone)


def test_tokenizer_empty_identifier_raises() -> None:
    tokenizer = ZeroTrustIdentityTokenizer(pepper_key="test_pepper_key")
    with pytest.raises(ValueError) as exc:
        tokenizer.tokenize_citizen_id("   ")
    assert "cannot be empty or whitespace-only" in str(exc.value)


def test_tokenizer_missing_pepper_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGRISTACK_PEPPER_SECRET", raising=False)
    with pytest.raises(ValueError) as exc:
        ZeroTrustIdentityTokenizer.from_env()
    assert "Required environment variable" in str(exc.value)


def test_tokenizer_empty_pepper_arg_raises() -> None:
    with pytest.raises(ValueError) as exc:
        ZeroTrustIdentityTokenizer(pepper_key="   ")
    assert "pepper_key cannot be empty or whitespace-only" in str(exc.value)


def test_tokenizer_reads_pepper_from_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGRISTACK_PEPPER_SECRET", "env_test_pepper_key")
    tokenizer = ZeroTrustIdentityTokenizer.from_env()
    phone = "+919876543210"
    token = tokenizer.tokenize_phone_number(phone)
    assert len(token) == EXPECTED_TOKEN_LEN
