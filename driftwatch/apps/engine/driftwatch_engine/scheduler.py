"""Minimal durable-enough scheduler (stdlib only).

A background thread wakes every SCHEDULER_TICK_SECONDS and runs any active
source whose last run is older than its schedule. The jobs "queue" is the runs
table itself — restart-safe, observable, and visible in the product UI.
"""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime

from . import db
from .pipeline.runner import Deps, run_source

SCHEDULER_TICK_SECONDS = 30


def _due_sources() -> list[dict]:
    sources = db.query("SELECT * FROM sources WHERE status = 'active'")
    due = []
    for source in sources:
        last = db.query_one(
            "SELECT started_at FROM runs WHERE source_id = ? ORDER BY id DESC LIMIT 1", [source["id"]])
        if last is None:
            due.append(source)
            continue
        started = datetime.fromisoformat(last["started_at"])
        age_minutes = (datetime.now(UTC) - started).total_seconds() / 60
        if age_minutes >= source["schedule_minutes"]:
            due.append(source)
    return due


def start(deps: Deps) -> threading.Thread:
    def loop() -> None:
        while True:
            try:
                for source in _due_sources():
                    db.audit("scheduler", "tick.run_due", {"source": source["id"]}, {})
                    run_source(source["id"], deps)
            except Exception as exc:  # scheduler must survive any single failure
                db.audit("scheduler", "tick.error", {}, {"error": str(exc)})
            time.sleep(SCHEDULER_TICK_SECONDS)

    thread = threading.Thread(target=loop, name="driftwatch-scheduler", daemon=True)
    thread.start()
    return thread
