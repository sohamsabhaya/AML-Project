"""Optional API key, per-IP rate limit and early upload-size rejection.

The API key is an optional shared secret for a demo deployment, not user
authentication: anybody who knows the key can read every stored analysis.
Without ``API_KEY`` the API is open (intended for local use only).

``AnalyzeGuardMiddleware`` runs before FastAPI parses the multipart body, so an
oversize or rate-limited request is rejected without reading the upload.
"""
from __future__ import annotations

import hmac
import json
import threading
import time
from collections import deque

from fastapi import HTTPException, Request

from . import config

API_KEY_HEADER = "X-API-Key"


def api_key_ok(provided: str | None) -> bool:
    """True when no key is configured, or the provided key matches."""
    if not config.API_KEY:
        return True
    return provided is not None and hmac.compare_digest(
        provided.encode("utf-8"), config.API_KEY.encode("utf-8")
    )


def require_api_key(request: Request) -> None:
    """FastAPI dependency for every /api route except /api/health."""
    if not api_key_ok(request.headers.get(API_KEY_HEADER)):
        raise HTTPException(401, "A valid X-API-Key header is required.")


class RateLimiter:
    """Sliding one-minute window per key (the client IP). In memory, single process."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, now: float | None = None) -> float:
        """Record a hit. Returns 0 if allowed, else the seconds until a slot frees up."""
        if limit <= 0:
            return 0.0
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= 60.0:
                hits.popleft()
            if len(hits) >= limit:
                return max(1.0, 60.0 - (now - hits[0]))
            hits.append(now)
            if len(self._hits) > 10_000:  # bound memory: drop idle clients
                for stale in [k for k, v in self._hits.items() if not v or now - v[-1] >= 60.0]:
                    self._hits.pop(stale, None)
            return 0.0


class _TooLarge(Exception):
    pass


async def _json_response(send, status: int, detail: str, extra: list[tuple[bytes, bytes]] | None = None):
    body = json.dumps({"detail": detail}).encode()
    headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
    await send({"type": "http.response.start", "status": status, "headers": headers + (extra or [])})
    await send({"type": "http.response.body", "body": body})


class AnalyzeGuardMiddleware:
    """For ``POST /api/analyze``: API key, rate limit and body size, all before parsing."""

    def __init__(self, app, limiter: RateLimiter | None = None) -> None:
        self.app = app
        self.limiter = limiter or RateLimiter()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST" or scope["path"] != "/api/analyze":
            await self.app(scope, receive, send)
            return
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope["headers"]}

        if not api_key_ok(headers.get(API_KEY_HEADER.lower())):
            await _json_response(send, 401, "A valid X-API-Key header is required.")
            return

        client = scope.get("client")
        retry = self.limiter.check(client[0] if client else "unknown", config.RATE_LIMIT_PER_MIN)
        if retry:
            await _json_response(
                send, 429, "Too many analysis requests. Please wait a moment and try again.",
                [(b"retry-after", str(int(retry) + 1).encode())],
            )
            return

        limit = config.MAX_UPLOAD_BYTES + config.MULTIPART_OVERHEAD_BYTES
        too_large = f"File is too large. The maximum size is {config.MAX_UPLOAD_MB} MB."
        declared = headers.get("content-length")
        if declared is not None:
            try:
                size = int(declared)
            except ValueError:
                await _json_response(send, 400, "Invalid Content-Length header.")
                return
            if size > limit:
                await _json_response(send, 413, too_large)
                return

        received = 0
        overflow = False

        async def counting_receive():
            nonlocal received, overflow
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:  # chunked upload without an honest Content-Length
                    overflow = True
                    raise _TooLarge
            return message

        started = False

        async def tracking_send(message):
            nonlocal started
            if overflow:
                # FastAPI turns body-read errors into a 400; replace that with the real 413.
                if message["type"] == "http.response.start" and not started:
                    started = True
                    await _json_response(send, 413, too_large)
                return
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, counting_receive, tracking_send)
        except _TooLarge:
            if not started:
                await _json_response(send, 413, too_large)
