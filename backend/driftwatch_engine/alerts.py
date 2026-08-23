"""Decision-grade alerting.

Zero-noise policy: Classes 0-2 never alert. Every alert carries class, severity,
summary, confidence, and (when computed) the dollar figure — enough to act on
without opening a dashboard.
"""

from __future__ import annotations

import httpx

from . import db
from .config import Settings
from .domain import CLASS_LABELS, DriftClass


def send_alert(
    *,
    drift_event_id: int,
    source_name: str,
    drift_class: DriftClass,
    severity: str,
    summary: str,
    cost_delta_monthly: float | None,
    settings: Settings,
) -> None:
    if drift_class in (DriftClass.NONE, DriftClass.BENIGN):
        return
    cost_line = (
        f" Estimated impact: {cost_delta_monthly:+,.0f} USD/month." if cost_delta_monthly else ""
    )
    text = f"[{severity.upper()}] {CLASS_LABELS[drift_class]} on {source_name}: {summary}{cost_line}"
    payload = {
        "source": source_name,
        "class": int(drift_class),
        "class_label": CLASS_LABELS[drift_class],
        "severity": severity,
        "summary": summary,
        "cost_delta_monthly": cost_delta_monthly,
        "text": text,
    }
    db.insert("alerts", {
        "drift_event_id": drift_event_id, "channel": "in_app",
        "payload": db.j(payload), "delivered_at": db.now_iso(),
    })
    if settings.slack_webhook_url:
        try:
            httpx.post(settings.slack_webhook_url, json={"text": text}, timeout=10)
            db.insert("alerts", {
                "drift_event_id": drift_event_id, "channel": "slack",
                "payload": db.j(payload), "delivered_at": db.now_iso(),
            })
        except Exception as exc:  # alert delivery must never break the pipeline
            db.audit("machine", "alert.slack_failed", {"drift_event": drift_event_id}, {"error": str(exc)})
