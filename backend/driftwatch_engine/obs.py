"""Structured operation logging.

One line per Bright Data / pipeline operation, machine-parseable, with a stable
field set: operation, source_id, collector_id, status, latency_ms, category.

Secrets never reach here: the only values logged are identifiers, statuses and
vendor *messages* — `LiveClient` redacts credentials before anything is raised.
"""

from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager

logger = logging.getLogger("driftwatch")

# Anything that looks like a credential is scrubbed defensively, even though the
# call sites never intentionally pass one.
_SENSITIVE_KEYS = ("api_key", "apikey", "token", "authorization", "password", "secret")


def _scrub(payload: dict) -> dict:
    return {
        k: ("<redacted>" if any(s in k.lower() for s in _SENSITIVE_KEYS) else v)
        for k, v in payload.items()
    }


def log_op(operation: str, *, status: str, latency_ms: int | None = None,
           source_id: str | None = None, collector_id: str | None = None,
           category: str | None = None, **extra: object) -> None:
    """Emit one structured operation record."""
    record = {
        "operation": operation,
        "status": status,
        "source_id": source_id,
        "collector_id": collector_id,
        "latency_ms": latency_ms,
        "category": category,
        **extra,
    }
    record = _scrub({k: v for k, v in record.items() if v is not None})
    level = logging.ERROR if status in ("error", "failed") else logging.INFO
    logger.log(level, json.dumps(record, default=str, sort_keys=False))


@contextmanager
def operation(name: str, *, source_id: str | None = None, collector_id: str | None = None,
              **extra: object):
    """Time an operation and log its outcome exactly once, success or failure.

    On failure the exception's `category` (if it carries one, e.g. BrightDataError)
    is logged so a vendor refusal is never recorded as a scraper failure.
    """
    started = time.monotonic()
    try:
        yield
    except Exception as exc:  # noqa: BLE001 - re-raised immediately; we only annotate
        log_op(name, status="error", latency_ms=int((time.monotonic() - started) * 1000),
               source_id=source_id, collector_id=collector_id,
               category=getattr(exc, "category", None), error=str(exc), **extra)
        raise
    log_op(name, status="ok", latency_ms=int((time.monotonic() - started) * 1000),
           source_id=source_id, collector_id=collector_id, **extra)
