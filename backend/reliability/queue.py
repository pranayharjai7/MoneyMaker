from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from backend.reliability.idempotency import idempotency_key


@dataclass(frozen=True)
class NotificationJob:
    user_id: str
    event_type: str
    payload: dict[str, Any]
    dedupe_key: str
    attempts: int = 0


@dataclass
class QueueResult:
    accepted: bool
    reason: str


@dataclass
class InMemoryNotificationQueue:
    max_attempts: int = 3
    _queue: deque[NotificationJob] = field(default_factory=deque)
    _dedupe_keys: set[str] = field(default_factory=set)
    dead_letters: list[NotificationJob] = field(default_factory=list)

    def enqueue(self, user_id: str, event_type: str, payload: Mapping[str, Any]) -> QueueResult:
        key = idempotency_key(
            "notification",
            {"user_id": user_id, "event_type": event_type, "payload": dict(payload)},
        )
        if key in self._dedupe_keys:
            return QueueResult(accepted=False, reason="duplicate")
        self._dedupe_keys.add(key)
        self._queue.append(
            NotificationJob(
                user_id=user_id,
                event_type=event_type,
                payload=dict(payload),
                dedupe_key=key,
            )
        )
        return QueueResult(accepted=True, reason="queued")

    def dequeue(self) -> NotificationJob | None:
        if not self._queue:
            return None
        return self._queue.popleft()

    def retry_or_dead_letter(self, job: NotificationJob) -> QueueResult:
        next_job = NotificationJob(
            user_id=job.user_id,
            event_type=job.event_type,
            payload=job.payload,
            dedupe_key=job.dedupe_key,
            attempts=job.attempts + 1,
        )
        if next_job.attempts >= self.max_attempts:
            self.dead_letters.append(next_job)
            return QueueResult(accepted=False, reason="dead_letter")
        self._queue.append(next_job)
        return QueueResult(accepted=True, reason="retry_queued")

    @property
    def depth(self) -> int:
        return len(self._queue)


class RedisNotificationQueue:
    def __init__(
        self,
        redis_client: Any,
        queue_name: str = "moneymaker:notifications",
        dead_letter_name: str = "moneymaker:notifications:dead_letter",
        dedupe_ttl_seconds: int = 86400,
        max_attempts: int = 3,
    ):
        self.redis_client = redis_client
        self.queue_name = queue_name
        self.dead_letter_name = dead_letter_name
        self.dedupe_ttl_seconds = dedupe_ttl_seconds
        self.max_attempts = max_attempts

    def enqueue(self, user_id: str, event_type: str, payload: Mapping[str, Any]) -> QueueResult:
        key = idempotency_key(
            "notification",
            {"user_id": user_id, "event_type": event_type, "payload": dict(payload)},
        )
        if not self.redis_client.set(key, "1", nx=True, ex=self.dedupe_ttl_seconds):
            return QueueResult(accepted=False, reason="duplicate")
        job = NotificationJob(user_id=user_id, event_type=event_type, payload=dict(payload), dedupe_key=key)
        self.redis_client.rpush(self.queue_name, _encode_job(job))
        return QueueResult(accepted=True, reason="queued")

    def dequeue(self) -> NotificationJob | None:
        raw = self.redis_client.lpop(self.queue_name)
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        return _decode_job(str(raw))

    def retry_or_dead_letter(self, job: NotificationJob) -> QueueResult:
        next_job = NotificationJob(
            user_id=job.user_id,
            event_type=job.event_type,
            payload=job.payload,
            dedupe_key=job.dedupe_key,
            attempts=job.attempts + 1,
        )
        encoded = _encode_job(next_job)
        if next_job.attempts >= self.max_attempts:
            self.redis_client.rpush(self.dead_letter_name, encoded)
            return QueueResult(accepted=False, reason="dead_letter")
        self.redis_client.rpush(self.queue_name, encoded)
        return QueueResult(accepted=True, reason="retry_queued")

    @property
    def depth(self) -> int:
        return int(self.redis_client.llen(self.queue_name))


def _encode_job(job: NotificationJob) -> str:
    import json

    return json.dumps(
        {
            "user_id": job.user_id,
            "event_type": job.event_type,
            "payload": job.payload,
            "dedupe_key": job.dedupe_key,
            "attempts": job.attempts,
        },
        sort_keys=True,
        default=str,
    )


def _decode_job(raw: str) -> NotificationJob:
    import json

    data = json.loads(raw)
    return NotificationJob(
        user_id=str(data["user_id"]),
        event_type=str(data["event_type"]),
        payload=dict(data.get("payload") or {}),
        dedupe_key=str(data["dedupe_key"]),
        attempts=int(data.get("attempts") or 0),
    )
