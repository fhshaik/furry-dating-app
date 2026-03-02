from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass
from math import ceil
from time import monotonic

from fastapi import Request


@dataclass(frozen=True)
class RateLimitRule:
    limit: int
    window_seconds: int


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    retry_after: int

    @property
    def headers(self) -> dict[str, str]:
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
        }
        if not self.allowed:
            headers["Retry-After"] = str(self.retry_after)
        return headers


def parse_rate_limit(value: str) -> RateLimitRule:
    try:
        raw_limit, raw_window = value.split("/", maxsplit=1)
    except ValueError as exc:
        raise ValueError("Rate limit must use the format '<count>/<window>'") from exc

    window_lookup = {
        "second": 1,
        "seconds": 1,
        "minute": 60,
        "minutes": 60,
        "hour": 3600,
        "hours": 3600,
    }
    window_seconds = window_lookup.get(raw_window.strip().lower())
    if window_seconds is None:
        raise ValueError("Rate limit window must be second, minute, or hour")

    limit = int(raw_limit)
    if limit <= 0:
        raise ValueError("Rate limit count must be greater than zero")

    return RateLimitRule(limit=limit, window_seconds=window_seconds)


def get_client_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first_hop = forwarded_for.split(",", maxsplit=1)[0].strip()
        if first_hop:
            return first_hop
    if request.client is not None and request.client.host:
        return request.client.host
    return "anonymous"


class RateLimiter:
    def __init__(self, rate_limit: str) -> None:
        self.rule = parse_rate_limit(rate_limit)
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, request: Request) -> RateLimitResult:
        key = self._build_key(request)
        now = monotonic()
        window_start = now - self.rule.window_seconds

        async with self._lock:
            requests = self._requests[key]
            while requests and requests[0] <= window_start:
                requests.popleft()

            if len(requests) >= self.rule.limit:
                retry_after = max(1, ceil(requests[0] + self.rule.window_seconds - now))
                return RateLimitResult(
                    allowed=False,
                    limit=self.rule.limit,
                    remaining=0,
                    retry_after=retry_after,
                )

            requests.append(now)
            remaining = self.rule.limit - len(requests)
            return RateLimitResult(
                allowed=True,
                limit=self.rule.limit,
                remaining=remaining,
                retry_after=0,
            )

    def _build_key(self, request: Request) -> str:
        client = get_client_identifier(request)
        return f"{client}:{request.method}:{request.url.path}"
