from src.transport import IngressRateLimiter


def test_rate_limiter_burst_allowance() -> None:
    limiter = IngressRateLimiter(rate_per_minute=60, capacity=3)
    key = "user_token_123"

    assert limiter.is_allowed(key) is True
    assert limiter.is_allowed(key) is True
    assert limiter.is_allowed(key) is True
    assert limiter.is_allowed(key) is False  # Capacity 3 exhausted


def test_rate_limiter_different_keys_tracked_independently() -> None:
    limiter = IngressRateLimiter(rate_per_minute=60, capacity=1)

    assert limiter.is_allowed("user_1") is True
    assert limiter.is_allowed("user_1") is False
    assert limiter.is_allowed("user_2") is True
