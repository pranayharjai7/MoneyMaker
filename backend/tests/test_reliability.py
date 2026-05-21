from __future__ import annotations

import pytest

from backend.reliability.circuit_breaker import CircuitBreaker, CircuitOpenError, CircuitBreakerRegistry
from backend.reliability.idempotency import InMemoryIdempotencyStore, RedisIdempotencyStore
from backend.reliability.queue import InMemoryNotificationQueue, RedisNotificationQueue
from backend.reliability.retry import RetryExhaustedError, RetryPolicy, retry_sync


class FakeRedis:
    def __init__(self) -> None:
        self.keys: set[str] = set()
        self.lists: dict[str, list[str]] = {}

    def set(self, key: str, value: str, nx: bool = False, ex: int | None = None) -> bool:
        del value, ex
        if nx and key in self.keys:
            return False
        self.keys.add(key)
        return True

    def rpush(self, name: str, value: str) -> None:
        self.lists.setdefault(name, []).append(value)

    def lpop(self, name: str) -> bytes | None:
        rows = self.lists.setdefault(name, [])
        if not rows:
            return None
        return rows.pop(0).encode()

    def llen(self, name: str) -> int:
        return len(self.lists.setdefault(name, []))


def test_retry_sync_uses_exponential_backoff_until_success() -> None:
    attempts = {"count": 0}
    delays: list[float] = []

    def flaky() -> str:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ValueError("temporary")
        return "ok"

    result = retry_sync(
        flaky,
        policy=RetryPolicy(max_attempts=3, base_delay_seconds=0.5),
        sleeper=delays.append,
    )

    assert result == "ok"
    assert attempts["count"] == 3
    assert delays == [0.5, 1.0]


def test_retry_sync_raises_after_retry_limit() -> None:
    with pytest.raises(RetryExhaustedError):
        retry_sync(
            lambda: (_ for _ in ()).throw(ValueError("down")),
            policy=RetryPolicy(max_attempts=2, base_delay_seconds=0),
            sleeper=lambda delay: None,
        )


def test_notification_queue_deduplicates_and_dead_letters() -> None:
    queue = InMemoryNotificationQueue(max_attempts=2)

    first = queue.enqueue("user-1", "buy", {"stock_id": "stock-1"})
    duplicate = queue.enqueue("user-1", "buy", {"stock_id": "stock-1"})
    job = queue.dequeue()

    assert first.accepted
    assert not duplicate.accepted
    assert job is not None
    retry = queue.retry_or_dead_letter(job)
    retry_job = queue.dequeue()
    assert retry.reason == "retry_queued"
    assert retry_job is not None
    dead = queue.retry_or_dead_letter(retry_job)
    assert dead.reason == "dead_letter"
    assert len(queue.dead_letters) == 1
    assert queue.dequeue() is None
    assert queue.depth == 0


def test_redis_notification_queue_deduplicates_and_retries() -> None:
    redis = FakeRedis()
    queue = RedisNotificationQueue(redis, max_attempts=2)

    queued = queue.enqueue("user-1", "buy", {"stock_id": "stock-1"})
    duplicate = queue.enqueue("user-1", "buy", {"stock_id": "stock-1"})
    job = queue.dequeue()

    assert queued.accepted
    assert not duplicate.accepted
    assert job is not None
    assert queue.dequeue() is None
    retry = queue.retry_or_dead_letter(job)
    retry_job = queue.dequeue()
    assert retry.reason == "retry_queued"
    assert retry_job is not None
    dead = queue.retry_or_dead_letter(retry_job)
    assert dead.reason == "dead_letter"
    assert queue.depth == 0
    assert redis.llen(queue.dead_letter_name) == 1


def test_idempotency_stores_claim_and_expire_keys() -> None:
    store = InMemoryIdempotencyStore(ttl_seconds=10)

    assert store.claim("key", now=100.0)
    assert not store.claim("key", now=101.0)
    assert store.claim("key", now=111.0)

    redis = FakeRedis()
    redis_store = RedisIdempotencyStore(redis, ttl_seconds=10)
    assert redis_store.claim("redis-key")
    assert not redis_store.claim("redis-key")


def test_circuit_breaker_opens_and_registry_uses_fallback() -> None:
    breaker = CircuitBreaker(name="primary", failure_threshold=1, fallback_name="fallback")
    with pytest.raises(RuntimeError):
        breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("failed")))
    with pytest.raises(CircuitOpenError):
        breaker.call(lambda: "ok")

    registry = CircuitBreakerRegistry(breakers={"primary": breaker})

    assert registry.source_for("primary") == "fallback"


def test_circuit_breaker_recovers_after_success() -> None:
    breaker = CircuitBreaker(name="primary", failure_threshold=2)

    breaker.record_failure()
    assert breaker.state == "closed"
    assert breaker.call(lambda: "ok") == "ok"
    assert breaker.failure_count == 0
