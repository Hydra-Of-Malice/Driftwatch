"""The autonomous heal orchestrator — the loop Bright Data leaves open, closed.

Bright Data's design has a human at both ends of `scraper heal`: someone notices
breakage, writes the prompt, reviews the preview, and approves. This module is
that human, formalized:

  detect (contracts)  ->  diagnose  ->  compose prompt  ->  heal  ->  verify
  preview against the contract  ->  three-band decision:

    confidence >= auto_approve_threshold  ->  approve, bump version, re-run
    confidence <= auto_reject_threshold   ->  reject, retry once with refined prompt
    in between                            ->  human Review Queue (same approve API)

Rollback is version pinning: the active version only advances after a verified
re-run; a failed heal leaves the previous template active and the interval
quarantined. Every step lands in the audit ledger.
"""

from __future__ import annotations

import time

from pydantic import BaseModel

from .. import db
from ..brightdata.protocol import BrightDataClient
from ..config import Settings
from ..domain import ContractSpec, Verdict
from .composer import compose_heal_prompt
from .diagnoser import Diagnosis
from .verifier import verify_preview


class HealOutcome(BaseModel):
    status: str  # "approved" | "review" | "rejected"
    heal_event_id: int
    verdict: Verdict | None = None
    new_version: int | None = None
    prompt: str = ""


def run_heal(
    *,
    source: dict,
    scraper: dict,
    trigger_event_id: int | None,
    diagnosis: Diagnosis,
    spec: ContractSpec,
    last_good: dict | None,
    client: BrightDataClient,
    settings: Settings,
) -> HealOutcome:
    started = time.monotonic()
    collector_id = scraper["collector_id"]
    version_before = int(scraper["active_version"])
    prior_failure: str | None = None

    for attempt in (1, 2):
        prompt = compose_heal_prompt(
            source["name"], diagnosis, spec,
            max_chars=settings.heal_prompt_max_chars, attempt=attempt, prior_failure=prior_failure,
        )
        db.audit("machine", "heal.requested",
                 {"source": source["id"], "collector_id": collector_id},
                 {"attempt": attempt, "prompt": prompt})
        envelope = client.heal_scraper(collector_id, prompt, source["url"])
        preview = envelope.preview_payload()
        verdict = verify_preview(preview, spec, last_good)
        heal_event_id = db.insert("heal_events", {
            "source_id": source["id"],
            "trigger_event_id": trigger_event_id,
            "composed_prompt": prompt,
            "preview_payload": db.j(preview),
            "verification": db.j(verdict.model_dump()),
            "decision": None,
            "decided_by": None,
            "version_before": version_before,
            "version_after": None,
            "status": "verifying",
            "created_at": db.now_iso(),
        })
        db.audit("machine", "heal.preview_verified",
                 {"source": source["id"], "heal_event": heal_event_id},
                 {"confidence": verdict.confidence, "passed": verdict.passed,
                  "diff_summary": envelope.diff_summary})

        if verdict.passed and verdict.confidence >= settings.auto_approve_threshold:
            client.approve(collector_id)
            new_version = version_before + 1
            db.update("scrapers", scraper["id"], {"active_version": new_version})
            mttr = round(time.monotonic() - started, 1)
            db.update("heal_events", heal_event_id, {
                "decision": "auto_approved", "decided_by": "machine",
                "version_after": new_version, "status": "approved", "mttr_seconds": mttr,
            })
            db.audit("machine", "heal.auto_approved",
                     {"source": source["id"], "heal_event": heal_event_id},
                     {"version": f"v{version_before} -> v{new_version}", "mttr_seconds": mttr})
            return HealOutcome(status="approved", heal_event_id=heal_event_id,
                               verdict=verdict, new_version=new_version, prompt=prompt)

        if verdict.confidence <= settings.auto_reject_threshold:
            client.approve(collector_id, reject=True)
            prior_failure = "; ".join(
                d for g in verdict.gates if not g.passed for d in g.details[:2]) or "empty preview"
            db.update("heal_events", heal_event_id, {
                "decision": "auto_rejected", "decided_by": "machine", "status": "rejected",
            })
            db.audit("machine", "heal.auto_rejected",
                     {"source": source["id"], "heal_event": heal_event_id},
                     {"confidence": verdict.confidence, "reason": prior_failure})
            continue  # retry once with a refined prompt

        # Gray band: hold Bright Data's approval gate open for a human decision.
        db.update("heal_events", heal_event_id, {"status": "review"})
        db.audit("machine", "heal.escalated_to_review",
                 {"source": source["id"], "heal_event": heal_event_id},
                 {"confidence": verdict.confidence})
        return HealOutcome(status="review", heal_event_id=heal_event_id, verdict=verdict, prompt=prompt)

    return HealOutcome(status="rejected", heal_event_id=heal_event_id, verdict=verdict, prompt=prompt)


def decide_review(heal_event_id: int, *, approve: bool, client: BrightDataClient) -> dict:
    """Apply a human Review Queue decision through the same Bright Data approval API."""
    heal = db.query_one("SELECT * FROM heal_events WHERE id = ?", [heal_event_id])
    if heal is None or heal["status"] != "review":
        raise ValueError(f"heal event {heal_event_id} is not awaiting review")
    scraper = db.query_one("SELECT * FROM scrapers WHERE source_id = ?", [heal["source_id"]])
    assert scraper is not None
    client.approve(scraper["collector_id"], reject=not approve)
    if approve:
        new_version = int(scraper["active_version"]) + 1
        db.update("scrapers", scraper["id"], {"active_version": new_version})
        db.update("heal_events", heal_event_id, {
            "decision": "human_approved", "decided_by": "human",
            "version_after": new_version, "status": "approved",
        })
        db.audit("human", "heal.human_approved", {"heal_event": heal_event_id},
                 {"version": f"v{scraper['active_version']} -> v{new_version}"})
    else:
        db.update("heal_events", heal_event_id, {
            "decision": "human_rejected", "decided_by": "human", "status": "rejected",
        })
        db.audit("human", "heal.human_rejected", {"heal_event": heal_event_id}, {})
    return db.query_one("SELECT * FROM heal_events WHERE id = ?", [heal_event_id]) or {}
