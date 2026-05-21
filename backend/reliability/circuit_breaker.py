from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TypeVar


T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    pass


@dataclass
class CircuitBreaker:
    name: str
    failure_threshold: int = 3
    recovery_timeout_seconds: int = 300
    fallback_name: str | None = None
    failure_count: int = 0
    opened_at: datetime | None = None

    @property
    def state(self) -> str:
        if self.opened_at is None:
            return "closed"
        if datetime.now(tz=UTC) >= self.opened_at + timedelta(seconds=self.recovery_timeout_seconds):
            return "half_open"
        return "open"

    def call(self, operation: Callable[[], T]) -> T:
        if self.state == "open":
            raise CircuitOpenError(f"circuit '{self.name}' is open")
        try:
            result = operation()
        except Exception:
            self.record_failure()
            raise
        self.record_success()
        return result

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.opened_at = datetime.now(tz=UTC)

    def record_success(self) -> None:
        self.failure_count = 0
        self.opened_at = None

    def can_use_primary(self) -> bool:
        return self.state != "open"


@dataclass
class CircuitBreakerRegistry:
    breakers: dict[str, CircuitBreaker]

    def breaker_for(self, name: str, fallback_name: str | None = None) -> CircuitBreaker:
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(name=name, fallback_name=fallback_name)
        return self.breakers[name]

    def source_for(self, name: str, fallback_name: str | None = None) -> str:
        breaker = self.breaker_for(name, fallback_name=fallback_name)
        if breaker.can_use_primary():
            return name
        return breaker.fallback_name or name
