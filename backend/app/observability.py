"""Structured logging and the request-id middleware.

Logs never contain image bytes, file names or record ids: access logs record
the method, a path with id segments replaced by ``{id}``, the status code and the
duration.
"""
from __future__ import annotations

import contextvars
import json
import logging
import re
import time
import uuid

from . import config

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_ID_SEGMENT_RE = re.compile(r"(/api/analyses/)[^/]+")

access_log = logging.getLogger("brainscan.access")


class _RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        extra = getattr(record, "fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging() -> None:
    """Configure the root logger once (idempotent)."""
    root = logging.getLogger()
    if getattr(root, "_brainscan_configured", False):
        root.setLevel(config.LOG_LEVEL)
        return
    handler = logging.StreamHandler()
    handler.addFilter(_RequestIdFilter())
    if config.LOG_FORMAT == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s")
        )
    root.handlers = [handler]
    root.setLevel(config.LOG_LEVEL)
    root._brainscan_configured = True  # type: ignore[attr-defined]


def redact_path(path: str) -> str:
    return _ID_SEGMENT_RE.sub(r"\1{id}", path)


class RequestIdMiddleware:
    """Accept or create ``X-Request-ID``, echo it on the response, log one access line."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = ""
        for key, value in scope.get("headers", []):
            if key == b"x-request-id":
                incoming = value.decode("latin-1")
                break
        rid = incoming if _REQUEST_ID_RE.match(incoming) else uuid.uuid4().hex
        token = request_id_var.set(rid)
        scope.setdefault("state", {})["request_id"] = rid
        started = time.perf_counter()
        status = {"code": 500}

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", rid.encode("latin-1")))
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            access_log.info(
                "%s %s -> %s", scope["method"], redact_path(scope["path"]), status["code"],
                extra={"fields": {
                    "method": scope["method"],
                    "path": redact_path(scope["path"]),
                    "status": status["code"],
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                }},
            )
            request_id_var.reset(token)
