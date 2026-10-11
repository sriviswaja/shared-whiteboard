"""Token-bucket rate limiter (SRS WB-SR-004: 60 messages per second per connection)."""
import time
from typing import Callable


class TokenBucket:
    def __init__(self, rate: float = 60.0, burst: float | None = None,
                 clock: Callable[[], float] = time.monotonic):
        self.rate = rate
        self.capacity = burst if burst is not None else rate
        self._tokens = self.capacity
        self._clock = clock
        self._last = clock()

    def allow(self, cost: float = 1.0) -> bool:
        now = self._clock()
        self._tokens = min(self.capacity, self._tokens + (now - self._last) * self.rate)
        self._last = now
        if self._tokens >= cost:
            self._tokens -= cost
            return True
        return False
