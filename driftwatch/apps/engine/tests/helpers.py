"""Shared test scaffolding: isolated DB per test, replay world, seeded sources."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE_DIR))

from driftwatch_engine import db, seed  # noqa: E402
from driftwatch_engine.brightdata.replay import ReplayClient, WorldState  # noqa: E402
from driftwatch_engine.config import FIXTURES_DIR, Settings  # noqa: E402
from driftwatch_engine.llm.provider import HeuristicProvider  # noqa: E402
from driftwatch_engine.pipeline.runner import Deps  # noqa: E402


def fixture(source_id: str, name: str) -> dict:
    return json.loads((FIXTURES_DIR / "snapshots" / source_id / f"{name}.json").read_text())


class EngineTestCase(unittest.TestCase):
    """Isolated engine world: temp DB, fresh WorldState, sources onboarded (no history)."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        db.configure(str(Path(self._tmp.name) / "test.db"))
        seed.ensure_sources()
        self.world = WorldState()
        self.client = ReplayClient(self.world)
        self.settings = Settings(mode="replay", db_path=str(Path(self._tmp.name) / "test.db"))
        self.deps = Deps(client=self.client, provider=HeuristicProvider(), settings=self.settings)

    def tearDown(self) -> None:
        db.close()
        self._tmp.cleanup()
