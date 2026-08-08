import pytest

from src.gateway import RateLimiter


def test_rate_limiter_burst_allowance() -> None:
    limiter = RateLimiter(rate_per_minute=60, capacity=3)
    key = "user_token_123"

    assert limiter.is_allowed(key) is True
    assert limiter.is_allowed(key) is True
    assert limiter.is_allowed(key) is True
    assert limiter.is_allowed(key) is False  # Capacity 3 exhausted


def test_rate_limiter_different_keys_tracked_independently() -> None:
    limiter = RateLimiter(rate_per_minute=60, capacity=1)

    assert limiter.is_allowed("user_1") is True
    assert limiter.is_allowed("user_1") is False
    assert limiter.is_allowed("user_2") is True


def test_rate_limiter_invalid_config_raises() -> None:
    with pytest.raises(ValueError, match="rate_per_minute must be a positive integer"):
        RateLimiter(rate_per_minute=0, capacity=10)

    with pytest.raises(ValueError, match="capacity must be a positive integer"):
        RateLimiter(rate_per_minute=60, capacity=0)


def test_rate_limiter_empty_key_raises() -> None:
    limiter = RateLimiter(rate_per_minute=60, capacity=10)
    with pytest.raises(ValueError, match="Rate limit key cannot be empty or whitespace-only"):
        limiter.is_allowed("   ")
