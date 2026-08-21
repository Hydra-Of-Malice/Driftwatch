"""End-to-end mirror-break test: the whole state machine across all five classes.

This is the test that answers the hackathon's central question in CI:
"when the website changes, does the system detect, repair, verify, and stay honest?"
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from driftwatch_engine import db
from driftwatch_engine.pipeline.runner import run_source
from tests.helpers import EngineTestCase


class TestEndToEnd(EngineTestCase):
    NIMBUS = "nimbusai-pricing"
    PAYFLUX = "payflux-docs"

    def test_full_lifecycle_across_all_drift_classes(self) -> None:
        # 1) Baseline run publishes.
        first = run_source(self.NIMBUS, self.deps)
        self.assertEqual(first["state"], "published")

        # 2) Unchanged page short-circuits to Class 0 (content-hash, no LLM/credit waste).
        second = run_source(self.NIMBUS, self.deps)
        self.assertEqual(second["class"], 0)

        # 3) Overnight redesign: detect -> auto-heal -> verify -> approve -> re-run -> publish.
        self.world.set_variant(self.NIMBUS, "v2_redesign")
        healed = run_source(self.NIMBUS, self.deps)
        self.assertEqual(healed["state"], "published")
        self.assertTrue(healed["healed"])
        scraper = db.query_one("SELECT * FROM scrapers WHERE source_id = ?", [self.NIMBUS])
        self.assertEqual(scraper["active_version"], 2)
        heal = db.query_one("SELECT * FROM heal_events ORDER BY id DESC LIMIT 1")
        self.assertEqual(heal["status"], "approved")
        self.assertIsNotNone(heal["mttr_seconds"])
        # Class 1 healed cleanly -> no alert noise.
        self.assertEqual(db.query("SELECT * FROM alerts"), [])

        # 4) Semantic drift: extraction green, meaning changed -> quarantined + alerted + priced.
        self.world.set_variant(self.NIMBUS, "v3_semantic")
        semantic = run_source(self.NIMBUS, self.deps)
        self.assertEqual(semantic["class"], 4)
        self.assertEqual(semantic["state"], "review")
        snapshot = db.query_one("SELECT * FROM snapshots ORDER BY id DESC LIMIT 1")
        self.assertEqual(snapshot["quarantined"], 1)  # the dashboard cannot lie
        impact = db.query_one("SELECT * FROM impact_reports ORDER BY id DESC LIMIT 1")
        # large-2: 2.50/1M x 248M output + mini-3: 0.15/1M x 40M output = 620 + 6
        self.assertEqual(impact["cost_delta_monthly"], 626.0)
        self.assertTrue(db.query("SELECT * FROM alerts"))

        # 5) Material change on the second source: diffed, classified, priced, alerted, published.
        run_source(self.PAYFLUX, self.deps)
        self.world.set_variant(self.PAYFLUX, "v4_material")
        material = run_source(self.PAYFLUX, self.deps)
        self.assertEqual(material["class"], 3)
        self.assertEqual(material["state"], "published")
        event = db.query_one("SELECT * FROM drift_events ORDER BY id DESC LIMIT 1")
        self.assertIn("customer_id", event["summary"] + event["field_changes"])
        impact = db.query_one("SELECT * FROM impact_reports ORDER BY id DESC LIMIT 1")
        affected_files = {site["file"] for site in db.uj(impact["affected"])}
        self.assertIn("src/payments.py", affected_files)

        # 6) Material price change on NimbusAI carries the exact dollar figure.
        self.world.set_variant(self.NIMBUS, "v4_material")
        priced = run_source(self.NIMBUS, self.deps)
        self.assertEqual(priced["class"], 3)
        self.assertEqual(priced["cost_delta_monthly"], 412.0)  # (0.90*320)+(0.50*248)

        # 7) Page disappears: Class 5 with relocation candidates for approval.
        self.world.set_variant(self.NIMBUS, "v5_gone")
        gone = run_source(self.NIMBUS, self.deps)
        self.assertEqual(gone["class"], 5)
        event = db.query_one("SELECT * FROM drift_events ORDER BY id DESC LIMIT 1")
        self.assertIn("relocation_candidate", event["field_changes"])

        # 8) The audit ledger recorded machine decisions end to end.
        actions = {a["action"] for a in db.query("SELECT action FROM audit_events")}
        for expected in ("run.started", "heal.requested", "heal.preview_verified",
                         "heal.auto_approved", "heal.rerun_verified"):
            self.assertIn(expected, actions)


if __name__ == "__main__":
    unittest.main()
