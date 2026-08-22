"""Replay Bright Data client.

Faithfully simulates the Scraper Studio lifecycle against recorded fixtures so
the entire product — pipeline, healing, verification, UI, tests, demo — runs
offline and deterministically. The simulation mirrors the real CLI's behavior:
runs return extraction payloads, heals stop at an `awaiting_approval` gate with
a `preview_result`, approvals commit the new template.

World model
-----------
Each source's target page is in exactly one *variant* (what the page looks like):

  v1_baseline   the page as first onboarded
  v2_redesign   layout rebuilt; the old template breaks (nulls / coverage collapse)
  v3_semantic   layout intact, values extract fine — but meaning changed (unit flip)
  v4_material   a watched fact genuinely changed (price up, param added, deprecation)
  v5_gone       the page was moved/removed (fetch fails)

Fixtures (fixtures/snapshots/<source>/):
  <variant>.json          ground truth — what a CORRECT template extracts
  <variant>.broken.json   what the OUTDATED template extracts (only for variants
                          that break the old template, e.g. v2_redesign)

A heal requested while the page is at variant X previews the truth for X; an
approval commits it, after which runs at X extract correctly ("the template was
regenerated"). Tests can sabotage the preview to exercise rejection paths.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path

from ..config import FIXTURES_DIR
from ..errors import BrightDataError
from .envelopes import ApproveEnvelope, CreateEnvelope, DiscoverResult, HealEnvelope, RunResult

AI_FLOW_STEPS = [
    "prepare_intent_analyzer",
    "planner",
    "schema_builder",
    "template_builder",
    "validation_run",
]


class WorldState:
    """Mutable state of the simulated web + simulated Studio templates."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.variants: dict[str, str] = {}  # source_id -> current page variant
        self.healed: dict[str, set[str]] = {}  # source_id -> variants the template handles
        self.pending_heal: dict[str, str] = {}  # source_id -> variant the pending heal targets
        self.sabotage_preview: dict[str, dict] = {}  # source_id -> forced bad preview (tests)

    def set_variant(self, source_id: str, variant: str) -> None:
        with self._lock:
            self.variants[source_id] = variant

    def variant(self, source_id: str) -> str:
        return self.variants.get(source_id, "v1_baseline")

    def mark_healed(self, source_id: str, variant: str) -> None:
        with self._lock:
            self.healed.setdefault(source_id, set()).add(variant)

    def is_healed(self, source_id: str, variant: str) -> bool:
        return variant in self.healed.get(source_id, set())


class ReplayClient:
    """BrightDataClient implementation backed by fixtures + WorldState."""

    def __init__(self, world: WorldState, fixtures_dir: Path | None = None) -> None:
        self.world = world
        self.fixtures = fixtures_dir or FIXTURES_DIR
        self.credits_spent = 0

    # -- helpers ----------------------------------------------------------------

    def _source_from_collector(self, collector_id: str) -> str:
        # Deterministic mapping used across the replay world: c_replay_<source_id>
        return collector_id.removeprefix("c_replay_")

    def _fixture(self, source_id: str, name: str) -> dict | None:
        path = self.fixtures / "snapshots" / source_id / f"{name}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def _truth(self, source_id: str, variant: str) -> dict:
        payload = self._fixture(source_id, variant)
        if payload is None:
            raise BrightDataError(f"no fixture for {source_id}/{variant}")
        return payload

    # -- BrightDataClient -------------------------------------------------------

    def create_scraper(self, url: str, description: str, name: str) -> CreateEnvelope:
        source_id = name  # onboarding names scrapers after the source id
        return CreateEnvelope(
            collector_id=f"c_replay_{source_id}",
            name=name,
            status="done",
            completed_steps=AI_FLOW_STEPS,
            view_url=f"https://brightdata.com/cp/scrapers/c_replay_{source_id}",
            created_at="replay",
        )

    def run_scraper(self, collector_id: str, url: str, version: int | None = None) -> RunResult:
        source_id = self._source_from_collector(collector_id)
        variant = self.world.variant(source_id)
        self.credits_spent += 1
        if variant == "v5_gone":
            return RunResult(collector_id=collector_id, status="failed", http_status=404,
                             error="target returned 404 (page moved or removed)")
        broken = self._fixture(source_id, f"{variant}.broken")
        if broken is not None and not self.world.is_healed(source_id, variant):
            # Outdated template against a redesigned page: extraction "succeeds" badly.
            return RunResult(collector_id=collector_id, status="done", payload=broken)
        return RunResult(collector_id=collector_id, status="done", payload=self._truth(source_id, variant))

    def heal_scraper(self, collector_id: str, prompt: str, url: str) -> HealEnvelope:
        source_id = self._source_from_collector(collector_id)
        variant = self.world.variant(source_id)
        self.world.pending_heal[source_id] = variant
        preview = self.world.sabotage_preview.get(source_id) or self._truth(source_id, variant)
        return HealEnvelope(
            collector_id=collector_id,
            status="awaiting_approval",
            prompt=prompt,
            preview_result=[preview],
            diff_summary="proposed template has 1 step(s) — review at view_url",
            view_url=f"https://brightdata.com/cp/scrapers/{collector_id}",
            next_step=f"bdata scraper approve {collector_id} --url {url}",
        )

    def approve(self, collector_id: str, *, reject: bool = False) -> ApproveEnvelope:
        source_id = self._source_from_collector(collector_id)
        pending = self.world.pending_heal.pop(source_id, None)
        if pending is None:
            return ApproveEnvelope(collector_id=collector_id, status="failed", approved=False,
                                   error="no heal awaiting approval")
        if reject:
            return ApproveEnvelope(collector_id=collector_id, status="rejected", approved=False)
        self.world.mark_healed(source_id, pending)
        return ApproveEnvelope(collector_id=collector_id, status="done", approved=True)

    def discover(self, query: str, intent: str) -> DiscoverResult:
        fixture = self.fixtures / "envelopes" / "discover.json"
        candidates = json.loads(fixture.read_text())["candidates"] if fixture.exists() else []
        return DiscoverResult(query=query, candidates=candidates)
