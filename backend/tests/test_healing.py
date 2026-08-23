"""The autonomous heal loop: detect -> diagnose -> compose -> heal -> verify -> decide."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from driftwatch_engine import db
from driftwatch_engine.contracts.engine import evaluate, load_spec
from driftwatch_engine.healing.composer import compose_heal_prompt
from driftwatch_engine.healing.diagnoser import diagnose
from driftwatch_engine.healing.orchestrator import decide_review, run_heal
from tests.helpers import EngineTestCase, fixture


class TestHealLoop(EngineTestCase):
    SOURCE = "nimbusai-pricing"

    def _structural_setup(self):
        self.world.set_variant(self.SOURCE, "v2_redesign")
        source = db.query_one("SELECT * FROM sources WHERE id = ?", [self.SOURCE])
        scraper = db.query_one("SELECT * FROM scrapers WHERE source_id = ?", [self.SOURCE])
        spec = load_spec(self.SOURCE)
        baseline = fixture(self.SOURCE, "v1_baseline")
        broken = self.client.run_scraper(scraper["collector_id"], source["url"]).payload
        verdict = evaluate(broken, spec, baseline)
        diagnosis = diagnose(verdict, broken, baseline, spec)
        return source, scraper, spec, baseline, diagnosis

    def test_prompt_is_specific_and_within_limit(self) -> None:
        _, _, spec, _, diagnosis = self._structural_setup()
        prompt = compose_heal_prompt("NimbusAI — Platform Pricing", diagnosis, spec)
        self.assertLessEqual(len(prompt), 1000)
        self.assertIn("price_input_per_1m", prompt)
        self.assertIn("2.5", prompt)  # last-known-good example woven in

    def test_verified_heal_is_auto_approved_and_versions_bump(self) -> None:
        source, scraper, spec, baseline, diagnosis = self._structural_setup()
        outcome = run_heal(source=source, scraper=scraper, trigger_event_id=None, diagnosis=diagnosis,
                           spec=spec, last_good=baseline, client=self.client, settings=self.settings)
        self.assertEqual(outcome.status, "approved")
        self.assertEqual(outcome.new_version, 2)
        assert outcome.verdict is not None
        self.assertTrue(outcome.verdict.passed)
        scraper_after = db.query_one("SELECT * FROM scrapers WHERE source_id = ?", [self.SOURCE])
        self.assertEqual(scraper_after["active_version"], 2)
        heal = db.query_one("SELECT * FROM heal_events ORDER BY id DESC LIMIT 1")
        self.assertEqual(heal["decision"], "auto_approved")
        self.assertEqual(heal["decided_by"], "machine")
        # After approval the healed template extracts the redesigned page correctly.
        rerun = self.client.run_scraper(scraper["collector_id"], source["url"])
        self.assertEqual(rerun.payload, fixture(self.SOURCE, "v2_redesign"))

    def test_garbage_preview_is_auto_rejected_never_trusted(self) -> None:
        source, scraper, spec, baseline, diagnosis = self._structural_setup()
        self.world.sabotage_preview[self.SOURCE] = {"totally": "wrong"}
        outcome = run_heal(source=source, scraper=scraper, trigger_event_id=None, diagnosis=diagnosis,
                           spec=spec, last_good=baseline, client=self.client, settings=self.settings)
        self.assertEqual(outcome.status, "rejected")
        scraper_after = db.query_one("SELECT * FROM scrapers WHERE source_id = ?", [self.SOURCE])
        self.assertEqual(scraper_after["active_version"], 1)  # rollback semantics: version never advanced
        decisions = [h["decision"] for h in db.query("SELECT decision FROM heal_events")]
        self.assertEqual(decisions, ["auto_rejected", "auto_rejected"])  # retried once, then gave up

    def test_gray_band_lands_in_review_and_human_approval_uses_same_api(self) -> None:
        source, scraper, spec, baseline, diagnosis = self._structural_setup()
        plausible_but_off = fixture(self.SOURCE, "v1_baseline")
        plausible_but_off = {**plausible_but_off, "models": [
            {**m, "price_input_per_1m": 9999.0} for m in plausible_but_off["models"]]}
        self.world.sabotage_preview[self.SOURCE] = plausible_but_off
        outcome = run_heal(source=source, scraper=scraper, trigger_event_id=None, diagnosis=diagnosis,
                           spec=spec, last_good=baseline, client=self.client, settings=self.settings)
        self.assertEqual(outcome.status, "review")
        pending = db.query("SELECT * FROM heal_events WHERE status = 'review'")
        self.assertEqual(len(pending), 1)
        decided = decide_review(pending[0]["id"], approve=True, client=self.client)
        self.assertEqual(decided["decision"], "human_approved")
        scraper_after = db.query_one("SELECT * FROM scrapers WHERE source_id = ?", [self.SOURCE])
        self.assertEqual(scraper_after["active_version"], 2)


if __name__ == "__main__":
    unittest.main()
