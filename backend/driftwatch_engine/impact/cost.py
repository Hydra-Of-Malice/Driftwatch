"""Cost-delta estimation: turn a price/unit change into a monthly dollar figure
against the connected repo's declared usage profile (fixtures/sample-repo/usage.yaml)."""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import BaseModel

from ..domain import DriftClass, FieldChange


class CostEstimate(BaseModel):
    monthly_delta: float | None = None
    basis: str = ""


def load_usage(repo_dir: Path) -> dict:
    path = repo_dir / "usage.yaml"
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}


def estimate(drift_class: DriftClass, changes: list[FieldChange], usage: dict) -> CostEstimate:
    models: dict = usage.get("models", {})
    if drift_class == DriftClass.MATERIAL:
        return _material_delta(changes, models)
    if drift_class == DriftClass.SEMANTIC:
        return _unit_flip_delta(changes, models)
    return CostEstimate()


def _entity(path: str) -> str | None:
    match = re.search(r"\[([^\]]+)\]", path)
    return match.group(1) if match else None


def _material_delta(changes: list[FieldChange], models: dict) -> CostEstimate:
    total, notes = 0.0, []
    for change in changes:
        model = _entity(change.path)
        profile = models.get(model or "", {})
        if not profile or change.kind != "changed":
            continue
        if not (isinstance(change.before, int | float) and isinstance(change.after, int | float)):
            continue
        delta_per_1m = float(change.after) - float(change.before)
        if "price_input" in change.path:
            volume = float(profile.get("input_m_tokens_per_month", 0))
        elif "price_output" in change.path:
            volume = float(profile.get("output_m_tokens_per_month", 0))
        else:
            continue
        total += delta_per_1m * volume
        notes.append(f"{model}: {delta_per_1m:+.2f}/1M x {volume:.0f}M tokens")
    if not notes:
        return CostEstimate()
    return CostEstimate(monthly_delta=round(total, 2), basis="; ".join(notes))


def _unit_flip_delta(changes: list[FieldChange], models: dict) -> CostEstimate:
    """Semantic unit flip: price now applies to a wider token base (e.g. input-only ->
    input+output combined). The price number didn't move; the bill did. Summed across
    every model in the declared usage profile."""
    total, notes = 0.0, []
    for change in sorted(changes, key=lambda c: c.path):
        model = _entity(change.path)
        profile = models.get(model or "", {})
        before_ctx, after_ctx = str(change.before or "").lower(), str(change.after or "").lower()
        if not profile or "unit_context" not in change.path:
            continue
        if "input" in before_ctx and ("output" in after_ctx or "combined" in after_ctx):
            price = float(profile.get("price_input_per_1m", 0))
            extra_volume = float(profile.get("output_m_tokens_per_month", 0))
            total += price * extra_volume
            notes.append(f"{model}: same {price:.2f}/1M now also billed on {extra_volume:.0f}M output tokens")
    if not notes:
        return CostEstimate()
    return CostEstimate(monthly_delta=round(total, 2), basis="; ".join(notes))
