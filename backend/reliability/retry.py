from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import sleep
from typing import TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.25
    max_delay_seconds: float = 5.0
    backoff_multiplier: float = 2.0

    def delay_for_attempt(self, attempt: int) -> float:
        delay = self.base_delay_seconds * (self.backoff_multiplier ** max(attempt - 1, 0))
        return min(delay, self.max_delay_seconds)


class RetryExhaustedError(RuntimeError):
    pass


def retry_sync(
    operation: Callable[[], T],
    policy: RetryPolicy | None = None,
    retryable: tuple[type[BaseException], ...] = (Exception,),
    sleeper: Callable[[float], None] = sleep,
) -> T:
    policy = policy or RetryPolicy()
    last_error: BaseException | None = None
    for attempt in range(1, max(1, policy.max_attempts) + 1):
        try:
            return operation()
        except retryable as exc:
            last_error = exc
            if attempt >= policy.max_attempts:
                break
            sleeper(policy.delay_for_attempt(attempt))
    raise RetryExhaustedError("operation failed after retry limit") from last_error
