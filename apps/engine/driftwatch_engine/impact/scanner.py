"""Impact Graph: map confirmed drift events onto an actual codebase.

v1 is a deliberate 7-day scope: literal entity scanning (model IDs, endpoint
paths) across a connected repo. AST-level call-graph analysis is a listed
non-goal for the hackathon.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel

from ..domain import FieldChange

SCANNABLE = {".py", ".ts", ".tsx", ".js", ".jsx", ".yaml", ".yml", ".json", ".env", ".md"}


class CallSite(BaseModel):
    file: str
    line: int
    snippet: str
    entity: str


def entities_from_changes(changes: list[FieldChange]) -> list[str]:
    """Entity labels come from concrete paths (`models[nimbus-large-2].price` -> nimbus-large-2)
    plus changed values that look like endpoint paths."""
    entities: set[str] = set()
    for change in changes:
        entities.update(re.findall(r"\[([^\]]+)\]", change.path))
        for value in (change.before, change.after):
            if isinstance(value, str) and value.startswith("/"):
                entities.add(value)
    return sorted(e for e in entities if not e.isdigit())


def scan_repo(repo_dir: Path, entities: list[str]) -> list[CallSite]:
    sites: list[CallSite] = []
    if not repo_dir.exists() or not entities:
        return sites
    for path in sorted(repo_dir.rglob("*")):
        if not path.is_file() or path.suffix not in SCANNABLE:
            continue
        rel = path.relative_to(repo_dir).as_posix()  # stable across platforms
        for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), start=1):
            for entity in entities:
                if entity in line:
                    sites.append(CallSite(file=rel, line=lineno, snippet=line.strip()[:160], entity=entity))
    return sites
