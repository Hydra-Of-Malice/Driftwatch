"""Tiny field-path resolver.

Contract rules address fields with dotted paths where `[]` fans out over lists:
`models[].price_input_per_1m` resolves to one (concrete_path, value) pair per
list item, with concrete paths like `models[nimbus-large-2].price_input_per_1m`
when an entity key is available (index fallback otherwise).
"""

from __future__ import annotations

from typing import Any

ENTITY_KEYS = ("model_id", "id", "path", "name")  # tried in order to label list items


def entity_label(item: Any, index: int, entity_key: str | None = None) -> str:
    if isinstance(item, dict):
        keys = ([entity_key] if entity_key else []) + list(ENTITY_KEYS)
        for key in keys:
            if key and key in item:
                return str(item[key])
    return str(index)


def resolve(payload: Any, path: str, entity_key: str | None = None) -> list[tuple[str, Any]]:
    """Resolve a rule path against a payload. Missing fields yield (path, None)."""
    parts = path.split(".")
    results: list[tuple[str, Any]] = [("", payload)]
    for part in parts:
        fan_out = part.endswith("[]")
        key = part[:-2] if fan_out else part
        next_results: list[tuple[str, Any]] = []
        for prefix, node in results:
            value = node.get(key) if isinstance(node, dict) else None
            concrete = f"{prefix}.{key}" if prefix else key
            if fan_out:
                if isinstance(value, list):
                    for i, item in enumerate(value):
                        label = entity_label(item, i, entity_key)
                        next_results.append((f"{concrete}[{label}]", item))
                else:
                    next_results.append((f"{concrete}[]", None))
            else:
                next_results.append((concrete, value))
        results = next_results
    return results
