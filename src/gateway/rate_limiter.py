"""Layer 2 Ingress Rate Limiter (Layer 2 Transport Guardrail).

Implements in-memory token bucket rate limiting to protect Layer 3 Intake Gateway
from DDoS, spam, and brute-force ingress attacks across carrier channels.

See: decisions/step3.2_security_and_ingestion_firewalls.md (Section 4.1)
See: decisions/step0.0_master_project_and_business_requirements.md
"""

import time


class RateLimiter:
    """Token bucket rate limiter tracking requests per identifier or communication channel.

    Enforces request quotas and burst allowances to prevent high-frequency request floods.

    Configuration & Behavior:
    - Refill Rate (`rate_per_minute`): Number of tokens added to the bucket per minute.
    - Burst Capacity (`capacity`): Maximum token bucket capacity for transient bursts.
    - Enforcement (`check_rate_limit`): Evaluates and consumes tokens using monotonic time.

    See: decisions/step3.2_security_and_ingestion_firewalls.md (Section 4.1)
    """

    def __init__(self, rate_per_minute: int = 60, capacity: int = 10) -> None:
        """Initializes rate limiter with refill rate and burst capacity.

        Args:
            rate_per_minute: Maximum allowed sustained requests per minute (must be > 0).
            capacity: Maximum burst capacity allowance (must be > 0).

        Raises:
            ValueError: If rate_per_minute or capacity is not positive.
        """
        if rate_per_minute <= 0:
            raise ValueError("rate_per_minute must be a positive integer.")
        if capacity <= 0:
            raise ValueError("capacity must be a positive integer.")

        self.rate_per_second: float = rate_per_minute / 60.0
        self.capacity: int = capacity
        self._tokens: dict[str, float] = {}
        self._last_update: dict[str, float] = {}

    def is_allowed(self, key: str) -> bool:
        """Checks if request for key is within rate limits and consumes 1 token.

        Args:
            key: Rate limit key (e.g. tokenized_citizen_id or IP address).

        Returns:
            True if request is allowed, False if rate limit is exceeded.

        Raises:
            ValueError: If key is empty or whitespace-only.
        """
        clean_key = key.strip()
        if not clean_key:
            raise ValueError("Rate limit key cannot be empty or whitespace-only.")

        now = time.monotonic()
        if clean_key not in self._tokens:
            self._tokens[clean_key] = float(self.capacity)
            self._last_update[clean_key] = now
        else:
            elapsed = now - self._last_update[clean_key]
            self._last_update[clean_key] = now
            # Refill tokens based on elapsed time capped at maximum burst capacity
            self._tokens[clean_key] = min(
                float(self.capacity),
                self._tokens[clean_key] + elapsed * self.rate_per_second,
            )

        if self._tokens[clean_key] >= 1.0:
            self._tokens[clean_key] -= 1.0
            return True
        return False
