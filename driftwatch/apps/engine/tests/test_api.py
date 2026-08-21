"""API surface smoke tests via the Flask test client."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from driftwatch_engine.api.app import create_app
from tests.helpers import EngineTestCase


class TestApi(EngineTestCase):
    def setUp(self) -> None:
        super().setUp()
        app = create_app(self.settings, self.world)
        self.http = app.test_client()

    def test_sources_and_run_flow(self) -> None:
        sources = self.http.get("/api/sources").get_json()
        self.assertEqual({s["id"] for s in sources}, {"nimbusai-pricing", "payflux-docs"})

        run = self.http.post("/api/run/nimbusai-pricing").get_json()
        self.assertEqual(run["state"], "published")

        detail = self.http.get("/api/sources/nimbusai-pricing").get_json()
        self.assertIsNotNone(detail["latest_snapshot"])
        self.assertEqual(detail["contract"]["spec"]["source_id"], "nimbusai-pricing")

    def test_demo_state_drives_the_world_and_events_flow(self) -> None:
        self.http.post("/api/run/nimbusai-pricing")
        set_state = self.http.post(
            "/api/demo/state", json={"source_id": "nimbusai-pricing", "variant": "v4_material"})
        self.assertEqual(set_state.status_code, 200)
        run = self.http.post("/api/run/nimbusai-pricing").get_json()
        self.assertEqual(run["class"], 3)

        events = self.http.get("/api/events").get_json()
        self.assertTrue(any(e["drift_class"] == 3 for e in events))
        detail = self.http.get(f"/api/events/{events[0]['id']}").get_json()
        self.assertIn("impact", detail)

        stats = self.http.get("/api/stats").get_json()
        self.assertGreaterEqual(stats["runs"], 2)
        self.assertIn("Material change", stats["events_by_class"])

    def test_invalid_variant_rejected(self) -> None:
        bad = self.http.post("/api/demo/state", json={"source_id": "x", "variant": "nope"})
        self.assertEqual(bad.status_code, 400)


if __name__ == "__main__":
    unittest.main()
