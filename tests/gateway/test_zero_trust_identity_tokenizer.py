from typing import Final

import pytest

from src.gateway import ZeroTrustIdentityTokenizer

EXPECTED_TOKEN_LENGTH: Final[int] = 64


def test_tokenizer_deterministic_output() -> None:
    tokenizer = ZeroTrustIdentityTokenizer(pepper_key="test_pepper_key")
    phone = "+919876543210"
    token1 = tokenizer.tokenize_id(phone)
    token2 = tokenizer.tokenize_id(phone)

    assert len(token1) == EXPECTED_TOKEN_LENGTH
    assert token1 == token2
    assert token1.isalnum()


def test_tokenizer_different_peppers_produce_different_tokens() -> None:
    tokenizer_alpha = ZeroTrustIdentityTokenizer(pepper_key="pepper_1")
    tokenizer_beta = ZeroTrustIdentityTokenizer(pepper_key="pepper_2")
    phone = "+919876543210"

    assert tokenizer_alpha.tokenize_id(phone) != tokenizer_beta.tokenize_id(phone)


def test_tokenizer_empty_identifier_raises() -> None:
    tokenizer = ZeroTrustIdentityTokenizer(pepper_key="test_pepper_key")
    with pytest.raises(ValueError) as exception_info:
        tokenizer.tokenize_id("   ")
    assert "cannot be empty or whitespace-only" in str(exception_info.value)


def test_tokenizer_missing_pepper_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGRISTACK_PEPPER_SECRET", raising=False)
    with pytest.raises(ValueError) as exception_info:
        ZeroTrustIdentityTokenizer.from_env()
    assert "Required environment variable" in str(exception_info.value)


def test_tokenizer_empty_pepper_arg_raises() -> None:
    with pytest.raises(ValueError) as exception_info:
        ZeroTrustIdentityTokenizer(pepper_key="   ")
    assert "pepper_key cannot be empty or whitespace-only" in str(exception_info.value)


def test_tokenizer_reads_pepper_from_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGRISTACK_PEPPER_SECRET", "env_test_pepper_key")
    tokenizer = ZeroTrustIdentityTokenizer.from_env()
    phone = "+919876543210"
    token = tokenizer.tokenize_id(phone)
    assert len(token) == EXPECTED_TOKEN_LENGTH
