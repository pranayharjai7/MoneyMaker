from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from time import time
from typing import Any


def idempotency_key(namespace: str, payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    digest = hashlib.sha256(encoded).hexdigest()
    return f"{namespace}:{digest}"


@dataclass
class InMemoryIdempotencyStore:
    ttl_seconds: int = 86400
    _expires_at: dict[str, float] = field(default_factory=dict)

    def claim(self, key: str, now: float | None = None) -> bool:
        now = time() if now is None else now
        self._purge(now)
        if key in self._expires_at:
            return False
        self._expires_at[key] = now + self.ttl_seconds
        return True

    def _purge(self, now: float) -> None:
        expired = [key for key, expires_at in self._expires_at.items() if expires_at <= now]
        for key in expired:
            del self._expires_at[key]


class RedisIdempotencyStore:
    def __init__(self, redis_client: Any, ttl_seconds: int = 86400):
        self.redis_client = redis_client
        self.ttl_seconds = ttl_seconds

    def claim(self, key: str, now: float | None = None) -> bool:
        del now
        return bool(self.redis_client.set(key, "1", nx=True, ex=self.ttl_seconds))
