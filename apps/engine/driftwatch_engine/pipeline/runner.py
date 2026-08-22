"""The extraction pipeline as an explicit state machine.

One entry point: `run_source`. Every run walks visible, persisted states; every
transition is audited; quarantined snapshots never reach analytics or alerts —
the dashboard cannot lie.

    SCHEDULED -> SCRAPING -> VALIDATING
        -> (fetch dead)            RELOCATING -> REVIEW           (Class 5)
        -> (contract broken)       DIAGNOSING -> HEALING -> VERIFYING
                                     -> APPROVING -> RERUNNING -> PUBLISHED   (Class 1, healed)
                                     -> REVIEW                                (gray band)
                                     -> QUARANTINED                           (heal failed)
        -> (meaning shifted)       REVIEW                        (Class 4, quarantined + alerted)
        -> (verdict passes)        DIFFING -> CLASSIFYING [-> IMPACT -> ALERTING] -> PUBLISHED
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .. import db
from ..alerts import send_alert
from ..brightdata.protocol import BrightDataClient
from ..config import FIXTURES_DIR, Settings
from ..contracts.engine import evaluate, load_spec
from ..domain import ContractSpec, DriftClass, FieldChange, RunState, Verdict
from ..drift.classifier import Classification, classify
from ..drift.differ import diff
from ..healing.diagnoser import diagnose
from ..healing.orchestrator import run_heal
from ..impact.cost import estimate, load_usage
from ..impact.scanner import entities_from_changes, scan_repo
from ..llm.provider import Provider


@dataclass
class Deps:
    client: BrightDataClient
    provider: Provider
    settings: Settings
    contracts_dir: Path | None = None
    sample_repo: Path = FIXTURES_DIR / "sample-repo"


def _hash(payload: dict) -> str:
    return hashlib.sha256(db.j(payload).encode()).hexdigest()[:16]


def _set_state(run_id: int, state: RunState, **fields) -> None:
    db.update("runs", run_id, {"state": state.value, **fields})
    db.audit("machine", f"run.{state.value}", {"run": run_id}, {})


def _last_good(source_id: str) -> dict | None:
    return db.query_one(
        "SELECT * FROM snapshots WHERE source_id = ? AND quarantined = 0 ORDER BY id DESC LIMIT 1",
        [source_id],
    )


def _snapshot(run_id: int, source_id: str, payload: dict, verdict: Verdict | None, quarantined: bool) -> int:
    return db.insert("snapshots", {
        "run_id": run_id, "source_id": source_id, "content_hash": _hash(payload),
        "payload": db.j(payload), "verdict": db.j(verdict.model_dump()) if verdict else None,
        "quarantined": int(quarantined), "created_at": db.now_iso(),
    })


def _event(source_id: str, run_id: int, classification: Classification, confidence: float,
           changes: list[FieldChange], before_id: int | None, after_id: int | None) -> int:
    return db.insert("drift_events", {
        "source_id": source_id, "run_id": run_id, "drift_class": int(classification.drift_class),
        "severity": classification.severity, "confidence": confidence,
        "summary": classification.summary,
        "field_changes": db.j([c.model_dump() for c in changes]),
        "before_snapshot_id": before_id, "after_snapshot_id": after_id,
        "created_at": db.now_iso(),
    })


def _impact(event_id: int, drift_class: DriftClass, changes: list[FieldChange], deps: Deps) -> float | None:
    entities = entities_from_changes(changes)
    sites = [s.model_dump() for s in scan_repo(deps.sample_repo, entities)]
    cost = estimate(drift_class, changes, load_usage(deps.sample_repo))
    note = deps.provider.migration_note(drift_class, changes, sites, cost.basis)
    db.insert("impact_reports", {
        "drift_event_id": event_id, "affected": db.j(sites),
        "cost_delta_monthly": cost.monthly_delta, "migration_note": note, "created_at": db.now_iso(),
    })
    return cost.monthly_delta


def run_source(source_id: str, deps: Deps) -> dict:
    source = db.query_one("SELECT * FROM sources WHERE id = ?", [source_id])
    scraper = db.query_one("SELECT * FROM scrapers WHERE source_id = ?", [source_id])
    if source is None or scraper is None:
        raise ValueError(f"unknown source {source_id!r}")
    spec = load_spec(source_id, deps.contracts_dir)
    last_good_row = _last_good(source_id)
    last_good = db.uj(last_good_row["payload"]) if last_good_row else None

    run_id = db.insert("runs", {
        "source_id": source_id, "scraper_version": scraper["active_version"],
        "state": RunState.SCRAPING.value, "started_at": db.now_iso(),
    })
    db.audit("scheduler", "run.started", {"run": run_id, "source": source_id},
             {"scraper_version": scraper["active_version"]})

    result = deps.client.run_scraper(scraper["collector_id"], source["url"],
                                     version=int(scraper["active_version"]))
    db.update("runs", run_id, {"credits_spent": deps.settings.credits_per_page_load})

    if result.status != "done" or result.payload is None:
        return _handle_unreachable(run_id, source, deps, last_good_row)

    payload = result.payload
    _set_state(run_id, RunState.VALIDATING)
    verdict = evaluate(payload, spec, last_good)

    if last_good_row and _hash(payload) == last_good_row["content_hash"] and verdict.passed:
        snap_id = _snapshot(run_id, source_id, payload, verdict, quarantined=False)
        _set_state(run_id, RunState.PUBLISHED, finished_at=db.now_iso(), confidence=verdict.confidence)
        return {"run_id": run_id, "class": 0, "state": "published", "snapshot_id": snap_id}

    semantic_gate = verdict.gate("semantics")
    structural = classify(fetch_failed=False, verdict=verdict, payload=payload, changes=[], spec=spec)

    if structural.drift_class == DriftClass.STRUCTURAL:
        return _handle_structural(run_id, source, scraper, spec, payload, verdict, last_good,
                                  last_good_row, deps, structural)

    if semantic_gate is not None and not semantic_gate.passed:
        return _handle_semantic(run_id, source, spec, payload, verdict, last_good, last_good_row, deps)

    return _publish_and_classify(run_id, source, spec, payload, verdict, last_good, last_good_row, deps)


# -- terminal handlers ------------------------------------------------------------


def _handle_unreachable(run_id: int, source: dict, deps: Deps, last_good_row: dict | None) -> dict:
    _set_state(run_id, RunState.RELOCATING)
    discovery = deps.client.discover(
        f"{source['name']} official page", intent=f"the current official page for: {source['description']}")
    changes = [FieldChange(path="relocation_candidate", kind="added", after=c)
               for c in discovery.candidates[:5]]
    classification = Classification(
        drift_class=DriftClass.AVAILABILITY, severity="critical",
        summary="Target page unreachable; relocation candidates proposed for approval.")
    event_id = _event(source["id"], run_id, classification, 0.9, changes,
                      last_good_row["id"] if last_good_row else None, None)
    send_alert(drift_event_id=event_id, source_name=source["name"],
               drift_class=DriftClass.AVAILABILITY, severity="critical",
               summary=classification.summary, cost_delta_monthly=None, settings=deps.settings)
    _set_state(run_id, RunState.REVIEW, finished_at=db.now_iso(), error="fetch failed")
    return {"run_id": run_id, "class": 5, "state": "review", "event_id": event_id}


def _handle_structural(run_id: int, source: dict, scraper: dict, spec: ContractSpec, payload: dict,
                       verdict: Verdict, last_good: dict | None, last_good_row: dict | None,
                       deps: Deps, classification: Classification) -> dict:
    snap_id = _snapshot(run_id, source["id"], payload, verdict, quarantined=True)
    event_id = _event(source["id"], run_id, classification, verdict.confidence, [],
                      last_good_row["id"] if last_good_row else None, snap_id)
    _set_state(run_id, RunState.DIAGNOSING, confidence=verdict.confidence)
    diagnosis = diagnose(verdict, payload, last_good, spec)
    _set_state(run_id, RunState.HEALING)
    outcome = run_heal(source=source, scraper=scraper, trigger_event_id=event_id, diagnosis=diagnosis,
                       spec=spec, last_good=last_good, client=deps.client, settings=deps.settings)

    if outcome.status == "approved":
        _set_state(run_id, RunState.RERUNNING)
        rerun = deps.client.run_scraper(scraper["collector_id"], source["url"], version=outcome.new_version)
        if rerun.status == "done" and rerun.payload is not None:
            rerun_verdict = evaluate(rerun.payload, spec, last_good)
            if rerun_verdict.passed:
                _snapshot(run_id, source["id"], rerun.payload, rerun_verdict, quarantined=False)
                db.audit("machine", "heal.rerun_verified", {"run": run_id, "heal_event": outcome.heal_event_id},
                         {"confidence": rerun_verdict.confidence})
                # The healed page may ALSO carry a real-world change — classify it now.
                return _publish_and_classify(run_id, source, spec, rerun.payload, rerun_verdict,
                                             last_good, last_good_row, deps, healed=True)
        db.audit("machine", "heal.rerun_failed", {"run": run_id, "heal_event": outcome.heal_event_id}, {})

    if outcome.status == "review":
        send_alert(drift_event_id=event_id, source_name=source["name"], drift_class=DriftClass.STRUCTURAL,
                   severity="warning", summary="Self-heal proposed; confidence in gray band — awaiting review.",
                   cost_delta_monthly=None, settings=deps.settings)
        _set_state(run_id, RunState.REVIEW, finished_at=db.now_iso())
        return {"run_id": run_id, "class": 1, "state": "review", "event_id": event_id,
                "heal_event_id": outcome.heal_event_id}

    send_alert(drift_event_id=event_id, source_name=source["name"], drift_class=DriftClass.STRUCTURAL,
               severity="critical", summary="Self-heal failed verification; source quarantined on last good version.",
               cost_delta_monthly=None, settings=deps.settings)
    _set_state(run_id, RunState.QUARANTINED, finished_at=db.now_iso(), error="heal rejected")
    return {"run_id": run_id, "class": 1, "state": "quarantined", "event_id": event_id,
            "heal_event_id": outcome.heal_event_id}


def _handle_semantic(run_id: int, source: dict, spec: ContractSpec, payload: dict, verdict: Verdict,
                     last_good: dict | None, last_good_row: dict | None, deps: Deps) -> dict:
    snap_id = _snapshot(run_id, source["id"], payload, verdict, quarantined=True)
    changes = diff(last_good, payload, spec.entity_key) if last_good else []
    classification = classify(fetch_failed=False, verdict=verdict, payload=payload, changes=changes, spec=spec)
    classification.summary = deps.provider.drift_summary(
        DriftClass.SEMANTIC, changes, classification.summary)
    event_id = _event(source["id"], run_id, classification, verdict.confidence, changes,
                      last_good_row["id"] if last_good_row else None, snap_id)
    _set_state(run_id, RunState.IMPACT, confidence=verdict.confidence)
    cost = _impact(event_id, DriftClass.SEMANTIC, changes, deps)
    _set_state(run_id, RunState.ALERTING)
    send_alert(drift_event_id=event_id, source_name=source["name"], drift_class=DriftClass.SEMANTIC,
               severity="critical", summary=classification.summary, cost_delta_monthly=cost,
               settings=deps.settings)
    _set_state(run_id, RunState.REVIEW, finished_at=db.now_iso())
    return {"run_id": run_id, "class": 4, "state": "review", "event_id": event_id}


def _publish_and_classify(run_id: int, source: dict, spec: ContractSpec, payload: dict, verdict: Verdict,
                          last_good: dict | None, last_good_row: dict | None, deps: Deps,
                          healed: bool = False) -> dict:
    snap_id = _snapshot(run_id, source["id"], payload, verdict, quarantined=False)
    _set_state(run_id, RunState.DIFFING)
    changes = diff(last_good, payload, spec.entity_key) if last_good else []
    _set_state(run_id, RunState.CLASSIFYING)
    classification = classify(fetch_failed=False, verdict=verdict, payload=payload, changes=changes, spec=spec)

    event_id: int | None = None
    cost: float | None = None
    if classification.drift_class != DriftClass.NONE or healed:
        if classification.drift_class == DriftClass.NONE and healed:
            classification = Classification(
                drift_class=DriftClass.STRUCTURAL, severity="info",
                summary="Page redesign absorbed: template healed, verified and re-approved; data unchanged.")
        classification.summary = deps.provider.drift_summary(
            classification.drift_class, classification.material_changes or changes, classification.summary)
        event_id = _event(source["id"], run_id, classification, verdict.confidence, changes,
                          last_good_row["id"] if last_good_row else None, snap_id)

    if classification.drift_class == DriftClass.MATERIAL:
        _set_state(run_id, RunState.IMPACT)
        cost = _impact(event_id or 0, DriftClass.MATERIAL, classification.material_changes, deps)
        _set_state(run_id, RunState.ALERTING)
        send_alert(drift_event_id=event_id or 0, source_name=source["name"],
                   drift_class=DriftClass.MATERIAL, severity=classification.severity,
                   summary=classification.summary, cost_delta_monthly=cost, settings=deps.settings)

    _set_state(run_id, RunState.PUBLISHED, finished_at=db.now_iso(), confidence=verdict.confidence)
    return {"run_id": run_id, "class": int(classification.drift_class), "state": "published",
            "snapshot_id": snap_id, "event_id": event_id, "cost_delta_monthly": cost, "healed": healed}
