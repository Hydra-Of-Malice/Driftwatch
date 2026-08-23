"""Core domain types: the drift taxonomy, pipeline states, contracts and verdicts.

These types are the vocabulary of the whole system; DB rows and API payloads are
projections of them.
"""

from __future__ import annotations

from enum import Enum, IntEnum

from pydantic import BaseModel, Field


class DriftClass(IntEnum):
    """The five-class drift taxonomy (Class 0 = no change).

    1 STRUCTURAL   page changed shape, meaning intact  -> heal, verify, approve; user sees a green pulse
    2 BENIGN       copyedits / cosmetic content        -> ledger only, never alerts
    3 MATERIAL     a watched fact actually changed     -> alert + impact analysis
    4 SEMANTIC     extraction "succeeds", meaning shifted (unit/scope/definition) -> the killer class
    5 AVAILABILITY page moved / removed / blocked      -> discover-powered relocation
    """

    NONE = 0
    STRUCTURAL = 1
    BENIGN = 2
    MATERIAL = 3
    SEMANTIC = 4
    AVAILABILITY = 5


CLASS_LABELS = {
    DriftClass.NONE: "No change",
    DriftClass.STRUCTURAL: "Structural drift",
    DriftClass.BENIGN: "Benign content drift",
    DriftClass.MATERIAL: "Material change",
    DriftClass.SEMANTIC: "Semantic drift",
    DriftClass.AVAILABILITY: "Availability drift",
}


class RunState(str, Enum):
    """Explicit, persisted pipeline states. Every transition writes an audit event."""

    SCHEDULED = "scheduled"
    SCRAPING = "scraping"
    VALIDATING = "validating"
    DIFFING = "diffing"
    CLASSIFYING = "classifying"
    IMPACT = "impact"
    ALERTING = "alerting"
    PUBLISHED = "published"
    DIAGNOSING = "diagnosing"
    HEALING = "healing"
    VERIFYING = "verifying"
    APPROVING = "approving"
    RERUNNING = "rerunning"
    REVIEW = "review"
    QUARANTINED = "quarantined"
    RELOCATING = "relocating"
    FAILED = "failed"


class Invariant(BaseModel):
    """A machine-checkable data-quality rule bound to a field path (supports `a[].b`)."""

    field: str
    kind: str  # "range" | "enum" | "cardinality_drop" | "non_null"
    min: float | None = None
    max: float | None = None
    values: list[str] | None = None
    max_drop_pct: float | None = None


class SemanticAssertion(BaseModel):
    """Meaning, made checkable.

    `meaning` documents what the field claims to be; `unit_context_field` names a
    sibling field the scraper captures verbatim from the page near the value;
    `anchors` are strings at least one of which must appear in that context for
    the meaning to still hold. A green schema with a failed anchor is Class 4.
    """

    field: str
    meaning: str
    unit_context_field: str
    anchors: list[str]


class ContinuityRule(BaseModel):
    """Plausibility of change vs the last-known-good snapshot."""

    field: str
    max_change_pct: float | None = None  # numeric fields: |delta| % beyond this is implausible
    max_cardinality_drop_pct: float | None = None  # list fields: shrinking beyond this is implausible


class ContractSpec(BaseModel):
    """A source's semantic data contract: shape + quality + meaning + plausibility."""

    source_id: str
    version: int = 1
    json_schema: dict = Field(alias="schema")
    invariants: list[Invariant] = []
    assertions: list[SemanticAssertion] = []
    continuity: list[ContinuityRule] = []
    significant_fields: list[str] = []  # fields whose change is Class 3 (material)
    entity_key: str | None = None  # key used to entity-resolve list items across snapshots

    model_config = {"populate_by_name": True}


class GateResult(BaseModel):
    """Outcome of one verification gate."""

    gate: str  # "schema" | "invariants" | "semantics" | "continuity"
    passed: bool
    details: list[str] = []
    failing_fields: list[str] = []


class Verdict(BaseModel):
    """Aggregate contract verdict for one extraction payload."""

    passed: bool
    confidence: float
    gates: list[GateResult]
    failing_fields: list[str] = []

    def gate(self, name: str) -> GateResult | None:
        return next((g for g in self.gates if g.gate == name), None)


class FieldChange(BaseModel):
    """One field-level difference between two snapshots (entity-resolved for lists)."""

    path: str
    kind: str  # "changed" | "added" | "removed"
    before: object | None = None
    after: object | None = None
