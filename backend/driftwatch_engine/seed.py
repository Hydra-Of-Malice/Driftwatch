"""Demo seed: two onboarded sources plus a plausible 12-day operating history.

Seeded history is clearly labeled as such (audit actor "seed"); it exists so the
product opens looking lived-in: a healed redesign three days ago, a material
change two days ago, a benign copyedit yesterday. All payloads come from the
same fixtures the replay client serves — one source of truth.
"""

from __future__ import annotations

import hashlib
import json
import random
from datetime import datetime, timedelta, timezone

from . import db
from .brightdata.replay import AI_FLOW_STEPS
from .config import FIXTURES_DIR
from .contracts.engine import evaluate, load_spec
from .domain import DriftClass
from .drift.differ import diff
from .impact.cost import estimate, load_usage
from .impact.scanner import entities_from_changes, scan_repo

SOURCES = [
    {
        "id": "nimbusai-pricing",
        "name": "NimbusAI — Platform Pricing",
        "vertical": "ai-provider",
        "url": "http://localhost:8000/mirror/nimbusai-pricing",
        "description": "Model pricing per 1M tokens, rate limits, context windows and model status "
                       "for every NimbusAI platform model.",
        "schedule_minutes": 60,
    },
    {
        "id": "payflux-docs",
        "name": "PayFlux — API Reference",
        "vertical": "vendor-docs",
        "url": "http://localhost:8000/mirror/payflux-docs",
        "description": "Endpoints, required parameters, deprecations, rate limits and auth "
                       "requirements from the public PayFlux API reference.",
        "schedule_minutes": 60,
    },
]


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _payload(source_id: str, variant: str) -> dict:
    path = FIXTURES_DIR / "snapshots" / source_id / f"{variant}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_sources() -> None:
    for source in SOURCES:
        if db.query_one("SELECT id FROM sources WHERE id = ?", [source["id"]]):
            continue
        db.insert("sources", {**source, "status": "active", "created_at": db.now_iso()})
        spec = load_spec(source["id"])
        db.insert("contracts", {
            "source_id": source["id"], "version": 1,
            "spec": db.j(spec.model_dump(by_alias=True)), "created_from": "auto_draft",
            "created_at": db.now_iso(),
        })
        db.insert("scrapers", {
            "source_id": source["id"], "collector_id": f"c_replay_{source['id']}",
            "active_version": 1, "status": "active",
            "view_url": f"https://brightdata.com/cp/scrapers/c_replay_{source['id']}",
            "created_at": db.now_iso(),
        })
        db.audit("seed", "source.onboarded", {"source": source["id"]},
                 {"ai_flow_steps": AI_FLOW_STEPS})


def seed_history(days: int = 12, runs_per_day: int = 4) -> None:
    if db.query_one("SELECT id FROM runs LIMIT 1"):
        return  # already seeded (or live) — never double-seed
    rng = random.Random(42)
    now = datetime.now(timezone.utc)

    for source in SOURCES:
        spec = load_spec(source["id"])
        baseline = _payload(source["id"], "v1_baseline")
        verdict = evaluate(baseline, spec, baseline)
        for day in range(days, 0, -1):
            for slot in range(runs_per_day):
                started = now - timedelta(days=day, hours=23 - slot * 6, minutes=rng.randint(0, 50))
                run_id = db.insert("runs", {
                    "source_id": source["id"], "scraper_version": 1, "state": "published",
                    "started_at": _iso(started), "finished_at": _iso(started + timedelta(seconds=8)),
                    "credits_spent": 1, "confidence": verdict.confidence,
                })
                db.insert("snapshots", {
                    "run_id": run_id, "source_id": source["id"],
                    "content_hash": "seedbaseline0000", "payload": db.j(baseline),
                    "verdict": db.j(verdict.model_dump()), "quarantined": 0, "created_at": _iso(started),
                })

    _seed_structural_heal(now - timedelta(days=3, hours=5))
    _seed_material_change(now - timedelta(days=2, hours=2))
    _seed_benign_change(now - timedelta(days=1, hours=7))
    _seed_settle(now - timedelta(hours=2))
    db.audit("seed", "history.seeded", {}, {"days": days})


def _seed_structural_heal(when: datetime) -> None:
    source_id = "nimbusai-pricing"
    spec = load_spec(source_id)
    baseline = _payload(source_id, "v1_baseline")
    broken = _payload(source_id, "v2_redesign.broken")
    verdict = evaluate(broken, spec, baseline)
    run_id = db.insert("runs", {
        "source_id": source_id, "scraper_version": 1, "state": "published",
        "started_at": _iso(when), "finished_at": _iso(when + timedelta(seconds=47)),
        "credits_spent": 2, "confidence": 0.98,
    })
    snap_broken = db.insert("snapshots", {
        "run_id": run_id, "source_id": source_id, "content_hash": "seedbroken000000",
        "payload": db.j(broken), "verdict": db.j(verdict.model_dump()),
        "quarantined": 1, "created_at": _iso(when),
    })
    event_id = db.insert("drift_events", {
        "source_id": source_id, "run_id": run_id, "drift_class": int(DriftClass.STRUCTURAL),
        "severity": "info", "confidence": 0.96,
        "summary": "Page redesign absorbed: pricing table rebuilt as cards; template healed, "
                   "verified against contract and re-approved autonomously. Data unchanged.",
        "field_changes": "[]", "before_snapshot_id": None, "after_snapshot_id": snap_broken,
        "created_at": _iso(when),
    })
    db.insert("heal_events", {
        "source_id": source_id, "trigger_event_id": event_id,
        "composed_prompt": "After a page redesign on NimbusAI — Platform Pricing, these fields fail "
                           "extraction: models[].price_input_per_1m, models[].price_output_per_1m, "
                           "models[].rate_limit_rpm. Field coverage fell to 33%. Previously valid values "
                           "looked like: {\"models[].price_input_per_1m\": 2.5}. Fix the template so every "
                           "field extracts with the same schema and JSON field names as before; numeric "
                           "fields must be plain numbers (no currency symbols), and keep the unit_context "
                           "fields populated with the visible pricing-unit text next to each value.",
        "preview_payload": db.j(baseline),
        "verification": db.j(evaluate(baseline, spec, baseline).model_dump()),
        "decision": "auto_approved", "decided_by": "machine",
        "version_before": 1, "version_after": 2, "status": "approved",
        "mttr_seconds": 42.3, "seeded": 1, "created_at": _iso(when + timedelta(seconds=5)),
    })
    db.update("scrapers", db.query_one(
        "SELECT id FROM scrapers WHERE source_id = ?", [source_id])["id"], {"active_version": 2})
    db.insert("snapshots", {
        "run_id": run_id, "source_id": source_id, "content_hash": "seedbaseline0000",
        "payload": db.j(baseline), "verdict": db.j(evaluate(baseline, spec, baseline).model_dump()),
        "quarantined": 0, "created_at": _iso(when + timedelta(seconds=47)),
    })
    db.audit("machine", "heal.auto_approved", {"source": source_id, "heal_event": event_id},
             {"version": "v1 -> v2", "mttr_seconds": 42.3, "seeded": True})


def _seed_material_change(when: datetime) -> None:
    source_id = "payflux-docs"
    spec = load_spec(source_id)
    baseline = _payload(source_id, "v1_baseline")
    changed = _payload(source_id, "v4_material")
    verdict = evaluate(changed, spec, baseline)
    changes = diff(baseline, changed, spec.entity_key)
    run_id = db.insert("runs", {
        "source_id": source_id, "scraper_version": 1, "state": "published",
        "started_at": _iso(when), "finished_at": _iso(when + timedelta(seconds=9)),
        "credits_spent": 1, "confidence": verdict.confidence,
    })
    snap_id = db.insert("snapshots", {
        "run_id": run_id, "source_id": source_id, "content_hash": "seedmaterial0000",
        "payload": db.j(changed), "verdict": db.j(verdict.model_dump()),
        "quarantined": 0, "created_at": _iso(when),
    })
    event_id = db.insert("drift_events", {
        "source_id": source_id, "run_id": run_id, "drift_class": int(DriftClass.MATERIAL),
        "severity": "critical", "confidence": verdict.confidence,
        "summary": "Watched facts changed: /v2/charges now REQUIRES customer_id; /v1/tokens marked "
                   "deprecated. Integrations that omit customer_id will start failing.",
        "field_changes": db.j([c.model_dump() for c in changes]),
        "before_snapshot_id": None, "after_snapshot_id": snap_id, "created_at": _iso(when),
    })
    entities = entities_from_changes(changes)
    sites = [s.model_dump() for s in scan_repo(FIXTURES_DIR / "sample-repo", entities)]
    cost = estimate(DriftClass.MATERIAL, changes, load_usage(FIXTURES_DIR / "sample-repo"))
    db.insert("impact_reports", {
        "drift_event_id": event_id, "affected": db.j(sites),
        "cost_delta_monthly": cost.monthly_delta,
        "migration_note": "Material change — migration checklist:\n"
                          "- `/v2/charges` now requires `customer_id`: pass it in payments.create_charge().\n"
                          "- `/v1/tokens` is deprecated: migrate legacy tokenize() to /v2 payment methods.\n"
                          "- Touch points: src/payments.py.",
        "created_at": _iso(when),
    })
    db.insert("alerts", {
        "drift_event_id": event_id, "channel": "in_app",
        "payload": db.j({"text": "[CRITICAL] Material change on PayFlux — API Reference: "
                                 "/v2/charges now requires customer_id; /v1/tokens deprecated."}),
        "delivered_at": _iso(when),
    })


def _seed_benign_change(when: datetime) -> None:
    source_id = "nimbusai-pricing"
    spec = load_spec(source_id)
    baseline = _payload(source_id, "v1_baseline")
    edited = json.loads(json.dumps(baseline))
    edited["effective_note"] = "Prices effective July 1, 2026 (updated wording)"
    verdict = evaluate(edited, spec, baseline)
    run_id = db.insert("runs", {
        "source_id": source_id, "scraper_version": 2, "state": "published",
        "started_at": _iso(when), "finished_at": _iso(when + timedelta(seconds=7)),
        "credits_spent": 1, "confidence": verdict.confidence,
    })
    snap_id = db.insert("snapshots", {
        "run_id": run_id, "source_id": source_id, "content_hash": "seedbenign000000",
        "payload": db.j(edited), "verdict": db.j(verdict.model_dump()),
        "quarantined": 0, "created_at": _iso(when),
    })
    db.insert("drift_events", {
        "source_id": source_id, "run_id": run_id, "drift_class": int(DriftClass.BENIGN),
        "severity": "info", "confidence": verdict.confidence,
        "summary": "1 cosmetic/copy change (effective-date wording); no watched fact affected.",
        "field_changes": db.j([{"path": "effective_note", "kind": "changed",
                                "before": baseline["effective_note"], "after": edited["effective_note"]}]),
        "before_snapshot_id": None, "after_snapshot_id": snap_id, "created_at": _iso(when),
    })


def _seed_settle(when: datetime) -> None:
    """Close the story arcs so the live replay world starts consistent: each source's
    last-known-good equals what its mirror page currently shows (see CURRENT_VARIANTS)."""
    for source_id, variant, version in (("nimbusai-pricing", "v1_baseline", 2),
                                        ("payflux-docs", "v4_material", 1)):
        spec = load_spec(source_id)
        payload = _payload(source_id, variant)
        prior = db.query_one(
            "SELECT payload FROM snapshots WHERE source_id = ? AND quarantined = 0 "
            "ORDER BY id DESC LIMIT 1", [source_id])
        verdict = evaluate(payload, spec, db.uj(prior["payload"]) if prior else None)
        run_id = db.insert("runs", {
            "source_id": source_id, "scraper_version": version, "state": "published",
            "started_at": _iso(when), "finished_at": _iso(when + timedelta(seconds=8)),
            "credits_spent": 1, "confidence": verdict.confidence,
        })
        real_hash = hashlib.sha256(db.j(payload).encode()).hexdigest()[:16]
        db.insert("snapshots", {
            "run_id": run_id, "source_id": source_id, "content_hash": real_hash,
            "payload": db.j(payload), "verdict": db.j(verdict.model_dump()),
            "quarantined": 0, "created_at": _iso(when),
        })


# What each mirrored page "currently shows" after the seeded story; the API layer
# aligns the replay WorldState with this at startup.
CURRENT_VARIANTS = {"nimbusai-pricing": "v1_baseline", "payflux-docs": "v4_material"}


def seed_all() -> None:
    ensure_sources()
    seed_history()
