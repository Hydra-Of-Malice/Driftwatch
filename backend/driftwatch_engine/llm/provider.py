"""LLM seam with a deterministic default.

Every AI-generated text in the product flows through this interface. The
HeuristicProvider is the default and makes the whole system deterministic and
offline-runnable (fixtures, tests, demo). The AnthropicProvider upgrades
summaries/adjudication/migration notes to model quality when ANTHROPIC_API_KEY
is present — behavior, states and decisions do not change, only prose quality.
"""

from __future__ import annotations

from typing import Protocol

import httpx

from ..domain import CLASS_LABELS, DriftClass, FieldChange


class Provider(Protocol):
    def drift_summary(self, drift_class: DriftClass, changes: list[FieldChange], base_summary: str) -> str: ...
    def migration_note(self, drift_class: DriftClass, changes: list[FieldChange],
                       call_sites: list[dict], cost_basis: str) -> str: ...


class HeuristicProvider:
    """Deterministic templates. No network, no keys, no variance."""

    def drift_summary(self, drift_class: DriftClass, changes: list[FieldChange], base_summary: str) -> str:
        return base_summary

    def migration_note(self, drift_class: DriftClass, changes: list[FieldChange],
                       call_sites: list[dict], cost_basis: str) -> str:
        files = sorted({site["file"] for site in call_sites})
        lines = [f"{CLASS_LABELS[drift_class]} — migration checklist:"]
        for change in changes[:5]:
            if change.kind == "changed":
                lines.append(f"- Update assumptions on `{change.path}`: {change.before!r} -> {change.after!r}.")
            elif change.kind == "added":
                lines.append(f"- New entity `{change.path}` — review whether your integration must handle it.")
            else:
                lines.append(f"- `{change.path}` removed/deprecated — replace usages before it disappears.")
        if files:
            lines.append(f"- Touch points: {', '.join(files[:6])} ({len(call_sites)} call sites).")
        if cost_basis:
            lines.append(f"- Cost basis: {cost_basis}.")
        return "\n".join(lines)


class AnthropicProvider(HeuristicProvider):
    """Optional model-backed provider. Falls back to heuristics on any error."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5") -> None:
        self.api_key = api_key
        self.model = model

    def _complete(self, prompt: str, max_tokens: int = 400) -> str | None:
        try:
            response = httpx.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
                json={"model": self.model, "max_tokens": max_tokens,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()["content"][0]["text"].strip()
        except Exception:
            return None

    def drift_summary(self, drift_class: DriftClass, changes: list[FieldChange], base_summary: str) -> str:
        prompt = (
            f"One crisp sentence for an engineering alert. Drift class: {CLASS_LABELS[drift_class]}. "
            f"Deterministic summary: {base_summary}. Field changes: "
            f"{[c.model_dump() for c in changes[:5]]}. No preamble."
        )
        return self._complete(prompt, 120) or super().drift_summary(drift_class, changes, base_summary)

    def migration_note(self, drift_class: DriftClass, changes: list[FieldChange],
                       call_sites: list[dict], cost_basis: str) -> str:
        prompt = (
            f"Write a terse migration note (<=8 bullet lines) for engineers. "
            f"Change class: {CLASS_LABELS[drift_class]}. Changes: {[c.model_dump() for c in changes[:5]]}. "
            f"Affected call sites: {call_sites[:8]}. Cost basis: {cost_basis or 'n/a'}."
        )
        return self._complete(prompt) or super().migration_note(drift_class, changes, call_sites, cost_basis)


def make_provider(anthropic_api_key: str | None) -> Provider:
    return AnthropicProvider(anthropic_api_key) if anthropic_api_key else HeuristicProvider()
