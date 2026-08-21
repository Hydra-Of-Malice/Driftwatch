"""Entity-resolved field-level differ.

Lists of objects are matched by entity key (model_id / id / path / name), not by
index — so `nimbus-large-2` remains the same entity across reorderings and
redesigns. That entity resolution is what keeps the Change Ledger longitudinal.
"""

from __future__ import annotations

from ..contracts.paths import entity_label
from ..domain import FieldChange


def diff(before: dict | None, after: dict | None, entity_key: str | None = None) -> list[FieldChange]:
    changes: list[FieldChange] = []
    _walk("", before, after, entity_key, changes)
    return changes


def _walk(prefix: str, before, after, entity_key: str | None, out: list[FieldChange]) -> None:
    if _is_object_list(before) and _is_object_list(after):
        before_map = {entity_label(item, i, entity_key): item for i, item in enumerate(before)}
        after_map = {entity_label(item, i, entity_key): item for i, item in enumerate(after)}
        for label in before_map.keys() | after_map.keys():
            path = f"{prefix}[{label}]"
            if label not in after_map:
                out.append(FieldChange(path=path, kind="removed", before=before_map[label]))
            elif label not in before_map:
                out.append(FieldChange(path=path, kind="added", after=after_map[label]))
            else:
                _walk(path, before_map[label], after_map[label], entity_key, out)
        return
    if isinstance(before, dict) and isinstance(after, dict):
        for key in before.keys() | after.keys():
            path = f"{prefix}.{key}" if prefix else key
            if key not in after:
                out.append(FieldChange(path=path, kind="removed", before=before[key]))
            elif key not in before:
                out.append(FieldChange(path=path, kind="added", after=after[key]))
            else:
                _walk(path, before[key], after[key], entity_key, out)
        return
    if before != after:
        out.append(FieldChange(path=prefix or "$", kind="changed", before=before, after=after))


def _is_object_list(value) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(i, dict) for i in value)
