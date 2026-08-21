"""The Semantic Contract Engine.

A contract is shape (JSON Schema) + quality (invariants) + meaning (semantic
assertions with unit anchors) + plausibility (continuity vs last-known-good).
`evaluate` runs all four gates and returns a Verdict with a composite
confidence. The same function verifies fresh extractions AND heal previews —
one definition of correctness everywhere in the system.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

import yaml
from jsonschema import Draft202012Validator

from ..config import FIXTURES_DIR
from ..domain import ContractSpec, GateResult, Verdict
from .paths import resolve

GATE_WEIGHTS = {"schema": 0.35, "invariants": 0.25, "semantics": 0.25, "continuity": 0.15}


class GateOutcome(NamedTuple):
    result: GateResult
    score: float  # partial credit in [0, 1]: fraction of checks that passed


def load_spec(source_id: str, contracts_dir: Path | None = None) -> ContractSpec:
    path = (contracts_dir or FIXTURES_DIR / "contracts") / f"{source_id}.yaml"
    return ContractSpec.model_validate(yaml.safe_load(path.read_text()))


def normalize_path(concrete: str) -> str:
    """`models[nimbus-large-2].price` -> `models[].price` (rule-pattern space)."""
    return re.sub(r"\[[^\]]*\]", "[]", concrete)


def _outcome(gate: str, checks: int, details: list[str], fields: list[str]) -> GateOutcome:
    result = GateResult(gate=gate, passed=not details, details=details, failing_fields=fields)
    score = 1.0 if checks == 0 else (checks - len(details)) / checks
    return GateOutcome(result, score if details else 1.0)


def _gate_schema(payload: dict, spec: ContractSpec) -> GateOutcome:
    validator = Draft202012Validator(spec.json_schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.absolute_path))
    details, fields = [], []
    for err in errors[:25]:
        path = ".".join(str(p) for p in err.absolute_path) or "$"
        details.append(f"{path}: {err.message}")
        fields.append(normalize_path(path))
    # Schema partial credit: proportion of top-level checks is opaque; use a coarse penalty.
    score = 0.0 if errors else 1.0
    return GateOutcome(GateResult(gate="schema", passed=not errors, details=details, failing_fields=fields), score)


def _check_invariant(inv, concrete: str, value) -> str | None:
    """Return a failure detail, or None if the check passes."""
    if inv.kind == "non_null":
        return None if value is not None else f"{concrete}: is null/missing"
    if inv.kind == "range":
        if not isinstance(value, int | float):
            return f"{concrete}: expected number in [{inv.min}, {inv.max}], got {value!r}"
        if (inv.min is not None and value < inv.min) or (inv.max is not None and value > inv.max):
            return f"{concrete}: {value} outside [{inv.min}, {inv.max}]"
        return None
    if inv.kind == "enum":
        return None if value in (inv.values or []) else f"{concrete}: {value!r} not in {inv.values}"
    return f"{concrete}: unknown invariant kind {inv.kind!r}"


def _gate_invariants(payload: dict, spec: ContractSpec, last_good: dict | None) -> GateOutcome:
    details, fields, checks = [], [], 0
    for inv in spec.invariants:
        if inv.kind == "cardinality_drop":
            checks += 1
            now_list = resolve(payload, inv.field, spec.entity_key)[0][1]
            prev_list = resolve(last_good, inv.field, spec.entity_key)[0][1] if last_good else None
            if isinstance(now_list, list) and isinstance(prev_list, list) and prev_list:
                drop = 100.0 * (len(prev_list) - len(now_list)) / len(prev_list)
                if inv.max_drop_pct is not None and drop > inv.max_drop_pct:
                    details.append(
                        f"{inv.field}: cardinality dropped {drop:.0f}% ({len(prev_list)} -> {len(now_list)})")
                    fields.append(inv.field)
            continue
        for concrete, value in resolve(payload, inv.field, spec.entity_key):
            checks += 1
            failure = _check_invariant(inv, concrete, value)
            if failure:
                details.append(failure)
                fields.append(normalize_path(concrete))
    return _outcome("invariants", checks, details, fields)


def _gate_semantics(payload: dict, spec: ContractSpec) -> GateOutcome:
    """The Class 4 tripwire: unit/scope anchors captured near each value must still hold."""
    details, fields, checks = [], [], 0
    for assertion in spec.assertions:
        for concrete, context in resolve(payload, assertion.unit_context_field, spec.entity_key):
            checks += 1
            text = str(context or "").lower()
            if not any(anchor.lower() in text for anchor in assertion.anchors):
                details.append(
                    f"{concrete}: page context {str(context)!r} matches no anchor "
                    f"[{', '.join(assertion.anchors)}] — asserted meaning: {assertion.meaning}")
                fields.append(normalize_path(concrete))
    return _outcome("semantics", checks, details, fields)


def _gate_continuity(payload: dict, spec: ContractSpec, last_good: dict | None) -> GateOutcome:
    """Plausibility vs last-known-good: huge silent jumps are suspect even when well-formed."""
    if last_good is None:
        return GateOutcome(
            GateResult(gate="continuity", passed=True, details=["no prior snapshot; vacuous pass"]), 1.0)
    details, fields, checks = [], [], 0
    for rule in spec.continuity:
        if rule.max_change_pct is not None:
            now = dict(resolve(payload, rule.field, spec.entity_key))
            before = dict(resolve(last_good, rule.field, spec.entity_key))
            for concrete, value in now.items():
                prev = before.get(concrete)
                if isinstance(value, int | float) and isinstance(prev, int | float) and prev:
                    checks += 1
                    change = abs(100.0 * (value - prev) / prev)
                    if change > rule.max_change_pct:
                        details.append(
                            f"{concrete}: changed {change:.0f}% ({prev} -> {value}), beyond "
                            f"plausibility bound {rule.max_change_pct}%")
                        fields.append(normalize_path(concrete))
        if rule.max_cardinality_drop_pct is not None:
            now_list = resolve(payload, rule.field, spec.entity_key)[0][1]
            prev_list = resolve(last_good, rule.field, spec.entity_key)[0][1]
            if isinstance(now_list, list) and isinstance(prev_list, list) and prev_list:
                checks += 1
                drop = 100.0 * (len(prev_list) - len(now_list)) / len(prev_list)
                if drop > rule.max_cardinality_drop_pct:
                    details.append(f"{rule.field}: cardinality dropped {drop:.0f}%")
                    fields.append(rule.field)
    return _outcome("continuity", checks, details, fields)


def evaluate(payload: dict, spec: ContractSpec, last_good: dict | None = None) -> Verdict:
    """Run all four gates; compose weighted confidence; list every failing field."""
    outcomes = [
        _gate_schema(payload, spec),
        _gate_invariants(payload, spec, last_good),
        _gate_semantics(payload, spec),
        _gate_continuity(payload, spec, last_good),
    ]
    confidence = sum(GATE_WEIGHTS[o.result.gate] * o.score for o in outcomes)
    failing = sorted({f for o in outcomes for f in o.result.failing_fields})
    return Verdict(
        passed=all(o.result.passed for o in outcomes),
        confidence=round(confidence, 3),
        gates=[o.result for o in outcomes],
        failing_fields=failing,
    )


def required_leaf_coverage(payload: dict, spec: ContractSpec) -> float:
    """Fraction of schema-required leaf fields (inside the main list) that are non-null.

    A field that was 100%-present all week and suddenly nulls out is a structural
    tripwire even when the run "succeeds" — this is the number that trips it.
    """
    props = spec.json_schema.get("properties", {})
    list_field = next((k for k, v in props.items() if isinstance(v, dict) and v.get("type") == "array"), None)
    if list_field is None:
        return 1.0
    required = (props[list_field].get("items", {}) or {}).get("required", [])
    items = payload.get(list_field) or []
    total = len(items) * len(required)
    present = sum(
        1 for item in items for field in required if isinstance(item, dict) and item.get(field) is not None
    )
    return 1.0 if total == 0 else present / total
