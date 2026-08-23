"""Heal-prompt composition.

Bright Data's `scraper heal` takes a human-written prompt (≤1000 chars)
describing what's wrong and what correct output looks like. Driftwatch is the
"human": it composes that prompt from the diagnosis — the exact failing fields,
expected types and last-known-good examples — deterministically and within the
documented length limit.
"""

from __future__ import annotations

import json

from ..domain import ContractSpec
from .diagnoser import Diagnosis

MAX_EXAMPLES = 4


def compose_heal_prompt(source_name: str, diagnosis: Diagnosis, spec: ContractSpec,
                        max_chars: int = 1000, attempt: int = 1, prior_failure: str | None = None) -> str:
    fields = ", ".join(diagnosis.failing_fields[:6])
    examples = {k: v for k, v in list(diagnosis.expected_examples.items())[:MAX_EXAMPLES]}
    example_str = json.dumps(examples, ensure_ascii=False) if examples else "see schema"
    parts = [
        f"After a page redesign on {source_name}, these fields fail extraction: {fields}.",
        f"Field coverage fell to {diagnosis.coverage:.0%}.",
        f"Previously valid values looked like: {example_str}.",
        "Fix the template so every field extracts with the same schema and JSON field names as before;",
        "numeric fields must be plain numbers (no currency symbols), and keep the",
        "unit_context fields populated with the visible pricing-unit text next to each value.",
    ]
    if attempt > 1 and prior_failure:
        parts.append(f"Previous fix attempt failed verification: {prior_failure}. Address this specifically.")
    prompt = " ".join(parts)
    if len(prompt) > max_chars:
        prompt = prompt[: max_chars - 1].rsplit(" ", 1)[0] + "…"
    return prompt
