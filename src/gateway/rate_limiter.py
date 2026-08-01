"""Layer 2 Ingress Rate Limiter (Layer 2 Transport Guardrail).

Implements in-memory token bucket rate limiting to protect Layer 3 Intake Gateway
from DDoS, spam, and brute-force ingress attacks across carrier channels.
"""

import time
from collections import defaultdict


class RateLimiter:
    """Token bucket rate limiter tracking requests per identifier/channel."""

    def __init__(self, rate_per_minute: int = 60, capacity: int = 10) -> None:
        """Initializes rate limiter with refill rate and burst capacity.

        Args:
            rate_per_minute: Maximum allowed sustained requests per minute.
            capacity: Maximum burst capacity allowance.
        """
        self.rate_per_second = rate_per_minute / 60.0
        self.capacity = capacity
        self._tokens: dict[str, float] = defaultdict(lambda: float(capacity))
        self._last_update: dict[str, float] = defaultdict(time.monotonic)

    def is_allowed(self, key: str) -> bool:
        """Checks if request for key is within rate limits and consumes 1 token.

        Args:
            key: Rate limit key (e.g. tokenized_citizen_id or IP address).

        Returns:
            True if request is allowed, False if rate limit is exceeded.
        """
        now = time.monotonic()
        if key not in self._tokens:
            self._tokens[key] = float(self.capacity)
            self._last_update[key] = now

        elapsed = now - self._last_update[key]
        self._last_update[key] = now

        # Refill tokens based on elapsed time
        self._tokens[key] = min(
            float(self.capacity),
            self._tokens[key] + elapsed * self.rate_per_second,
        )

        if self._tokens[key] >= 1.0:
            self._tokens[key] -= 1.0
            return True
        return False
