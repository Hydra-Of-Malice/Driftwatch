"""Differ (entity resolution) + five-class classifier."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from driftwatch_engine.contracts.engine import evaluate, load_spec
from driftwatch_engine.domain import DriftClass
from driftwatch_engine.drift.classifier import classify
from driftwatch_engine.drift.differ import diff
from tests.helpers import fixture


class TestDiffer(unittest.TestCase):
    def setUp(self) -> None:
        self.baseline = fixture("nimbusai-pricing", "v1_baseline")

    def test_reordering_entities_is_not_a_change(self) -> None:
        reordered = copy.deepcopy(self.baseline)
        reordered["models"] = list(reversed(reordered["models"]))
        self.assertEqual(diff(self.baseline, reordered, "model_id"), [])

    def test_entity_keyed_change_paths(self) -> None:
        changed = fixture("nimbusai-pricing", "v4_material")
        changes = diff(self.baseline, changed, "model_id")
        paths = {c.path for c in changes}
        self.assertIn("models[nimbus-large-2].price_input_per_1m", paths)
        self.assertIn("models[nimbus-vision-1].status", paths)

    def test_added_and_removed_entities(self) -> None:
        smaller = copy.deepcopy(self.baseline)
        removed = smaller["models"].pop()
        changes = diff(self.baseline, smaller, "model_id")
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].kind, "removed")
        self.assertIn(removed["model_id"], changes[0].path)


class TestClassifier(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = load_spec("nimbusai-pricing")
        self.baseline = fixture("nimbusai-pricing", "v1_baseline")

    def _classify(self, payload: dict):
        verdict = evaluate(payload, self.spec, self.baseline)
        changes = diff(self.baseline, payload, self.spec.entity_key)
        return classify(fetch_failed=False, verdict=verdict, payload=payload,
                        changes=changes, spec=self.spec)

    def test_availability(self) -> None:
        result = classify(fetch_failed=True, verdict=None, payload=None, changes=[], spec=self.spec)
        self.assertEqual(result.drift_class, DriftClass.AVAILABILITY)

    def test_structural(self) -> None:
        result = self._classify(fixture("nimbusai-pricing", "v2_redesign.broken"))
        self.assertEqual(result.drift_class, DriftClass.STRUCTURAL)
        self.assertEqual(result.severity, "critical")

    def test_semantic_beats_material(self) -> None:
        result = self._classify(fixture("nimbusai-pricing", "v3_semantic"))
        self.assertEqual(result.drift_class, DriftClass.SEMANTIC)

    def test_material_with_severity(self) -> None:
        result = self._classify(fixture("nimbusai-pricing", "v4_material"))
        self.assertEqual(result.drift_class, DriftClass.MATERIAL)
        self.assertEqual(result.severity, "critical")  # +36% price move and a deprecation
        self.assertTrue(result.material_changes)

    def test_benign(self) -> None:
        edited = copy.deepcopy(self.baseline)
        edited["effective_note"] = "Prices effective July 1, 2026 (updated)"
        result = self._classify(edited)
        self.assertEqual(result.drift_class, DriftClass.BENIGN)

    def test_none(self) -> None:
        result = self._classify(copy.deepcopy(self.baseline))
        self.assertEqual(result.drift_class, DriftClass.NONE)


if __name__ == "__main__":
    unittest.main()
