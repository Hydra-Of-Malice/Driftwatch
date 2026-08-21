"""Drift classification into the five-class taxonomy.

Order of precedence mirrors epistemic priority:
availability (can't see the page) > structural (can't trust extraction) >
semantic (extraction fine, meaning broke) > material (meaning fine, fact changed)
> benign > none.
"""

from __future__ import annotations

from pydantic import BaseModel

from ..contracts.engine import normalize_path, required_leaf_coverage
from ..domain import ContractSpec, DriftClass, FieldChange, Verdict

COVERAGE_COLLAPSE_THRESHOLD = 0.70  # below this, a "successful" run is structurally broken


class Classification(BaseModel):
    drift_class: DriftClass
    severity: str  # "info" | "warning" | "critical"
    summary: str
    material_changes: list[FieldChange] = []


def is_significant(path: str, spec: ContractSpec) -> bool:
    pattern = normalize_path(path)
    return any(pattern == normalize_path(sig) or pattern.endswith(normalize_path(sig)) for sig in
               spec.significant_fields)


def classify(
    *,
    fetch_failed: bool,
    verdict: Verdict | None,
    payload: dict | None,
    changes: list[FieldChange],
    spec: ContractSpec,
) -> Classification:
    if fetch_failed:
        return Classification(
            drift_class=DriftClass.AVAILABILITY, severity="critical",
            summary="Target page unreachable (moved, removed, or blocked). Relocation candidates requested.")

    assert verdict is not None and payload is not None
    schema_gate = verdict.gate("schema")
    invariant_gate = verdict.gate("invariants")
    semantic_gate = verdict.gate("semantics")
    coverage = required_leaf_coverage(payload, spec)

    structurally_broken = (
        (schema_gate is not None and not schema_gate.passed)
        or (invariant_gate is not None and not invariant_gate.passed)
        or coverage < COVERAGE_COLLAPSE_THRESHOLD
    )
    if structurally_broken:
        failing = ", ".join(verdict.failing_fields[:6]) or "required fields"
        return Classification(
            drift_class=DriftClass.STRUCTURAL, severity="critical",
            summary=(f"Extraction no longer satisfies the contract (coverage {coverage:.0%}). "
                     f"Failing: {failing}. Layout change suspected — healing required."))

    if semantic_gate is not None and not semantic_gate.passed:
        detail = semantic_gate.details[0] if semantic_gate.details else "semantic anchor mismatch"
        return Classification(
            drift_class=DriftClass.SEMANTIC, severity="critical",
            summary=f"Extraction succeeded but the meaning changed: {detail}")

    material = [c for c in changes if is_significant(c.path, spec) or c.kind in ("added", "removed")]
    material = [c for c in material if _is_watched(c, spec)]
    if material:
        head = "; ".join(_describe(c) for c in material[:4])
        severity = "critical" if any(_is_critical(c) for c in material) else "warning"
        return Classification(
            drift_class=DriftClass.MATERIAL, severity=severity,
            summary=f"Watched facts changed: {head}", material_changes=material)

    if changes:
        return Classification(
            drift_class=DriftClass.BENIGN, severity="info",
            summary=f"{len(changes)} cosmetic/copy change(s); no watched fact affected.")

    return Classification(drift_class=DriftClass.NONE, severity="info", summary="No change.")


def _is_watched(change: FieldChange, spec: ContractSpec) -> bool:
    if change.kind in ("added", "removed"):
        # whole-entity appearance/disappearance in the watched list is always material
        return "[" in change.path and "." not in change.path.split("[")[-1]
    return is_significant(change.path, spec)


def _is_critical(change: FieldChange) -> bool:
    if change.kind in ("added", "removed"):
        return True
    if isinstance(change.before, int | float) and isinstance(change.after, int | float) and change.before:
        return abs((change.after - change.before) / change.before) >= 0.10
    return isinstance(change.after, bool) or str(change.after).lower() in ("true", "deprecated")


def _describe(change: FieldChange) -> str:
    if change.kind == "added":
        return f"{change.path} added"
    if change.kind == "removed":
        return f"{change.path} removed"
    return f"{change.path}: {change.before!r} -> {change.after!r}"
