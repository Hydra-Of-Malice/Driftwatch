"""Failure diagnosis: turn a failed Verdict into a machine-usable description
of WHAT broke, with expected examples pulled from the last-known-good snapshot.
This diagnosis is the raw material for the heal prompt."""

from __future__ import annotations

from pydantic import BaseModel

from ..contracts.engine import normalize_path, required_leaf_coverage
from ..contracts.paths import resolve
from ..domain import ContractSpec, Verdict


class Diagnosis(BaseModel):
    failing_fields: list[str]
    expected_examples: dict[str, object]  # rule-pattern path -> last-known-good example value
    coverage: float
    gate_details: list[str]


def diagnose(verdict: Verdict, payload: dict, last_good: dict | None, spec: ContractSpec) -> Diagnosis:
    failing = [normalize_path(f) for f in verdict.failing_fields] or ["(coverage collapse)"]
    examples: dict[str, object] = {}
    if last_good is not None:
        for pattern in dict.fromkeys(failing):
            if "(" in pattern:
                continue
            resolved = resolve(last_good, pattern, spec.entity_key)
            good_values = [v for _, v in resolved if v is not None]
            if good_values:
                examples[pattern] = good_values[0]
    details = [d for gate in verdict.gates if not gate.passed for d in gate.details[:3]]
    return Diagnosis(
        failing_fields=sorted(dict.fromkeys(failing)),
        expected_examples=examples,
        coverage=round(required_leaf_coverage(payload, spec), 3),
        gate_details=details[:6],
    )
