"""Contract engine gates: shape, quality, meaning, plausibility."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from driftwatch_engine.contracts.engine import evaluate, load_spec, required_leaf_coverage
from tests.helpers import fixture


class TestContractEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = load_spec("nimbusai-pricing")
        self.baseline = fixture("nimbusai-pricing", "v1_baseline")

    def test_baseline_passes_all_gates(self) -> None:
        verdict = evaluate(self.baseline, self.spec, self.baseline)
        self.assertTrue(verdict.passed)
        self.assertEqual(verdict.confidence, 1.0)
        self.assertEqual(verdict.failing_fields, [])

    def test_broken_extraction_fails_schema_and_coverage(self) -> None:
        broken = fixture("nimbusai-pricing", "v2_redesign.broken")
        verdict = evaluate(broken, self.spec, self.baseline)
        self.assertFalse(verdict.passed)
        schema_gate = verdict.gate("schema")
        assert schema_gate is not None
        self.assertFalse(schema_gate.passed)
        self.assertLess(required_leaf_coverage(broken, self.spec), 0.70)
        self.assertLess(verdict.confidence, 0.5)

    def test_semantic_drift_fails_only_the_semantics_gate(self) -> None:
        semantic = fixture("nimbusai-pricing", "v3_semantic")
        verdict = evaluate(semantic, self.spec, self.baseline)
        self.assertFalse(verdict.passed)
        self.assertTrue(verdict.gate("schema").passed)  # type: ignore[union-attr]
        self.assertTrue(verdict.gate("invariants").passed)  # type: ignore[union-attr]
        self.assertFalse(verdict.gate("semantics").passed)  # type: ignore[union-attr]
        self.assertIn("models[].unit_context", verdict.failing_fields)

    def test_continuity_flags_implausible_jumps(self) -> None:
        implausible = copy.deepcopy(self.baseline)
        implausible["models"][0]["price_input_per_1m"] = 50.0  # +1900%
        verdict = evaluate(implausible, self.spec, self.baseline)
        self.assertFalse(verdict.gate("continuity").passed)  # type: ignore[union-attr]

    def test_invariant_range_and_enum(self) -> None:
        bad = copy.deepcopy(self.baseline)
        bad["models"][0]["price_input_per_1m"] = 9999.0
        bad["models"][1]["status"] = "retired"
        verdict = evaluate(bad, self.spec, self.baseline)
        gate = verdict.gate("invariants")
        assert gate is not None
        self.assertFalse(gate.passed)
        self.assertEqual(len(gate.details), 2)

    def test_first_snapshot_has_vacuous_continuity(self) -> None:
        verdict = evaluate(self.baseline, self.spec, last_good=None)
        self.assertTrue(verdict.passed)


if __name__ == "__main__":
    unittest.main()
