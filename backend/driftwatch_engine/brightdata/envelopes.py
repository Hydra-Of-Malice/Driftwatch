"""Pydantic models of Bright Data CLI/API response envelopes.

Field names mirror the real CLI's JSON output, verified against @brightdata/cli
0.3.5 responses captured live on 2026-08-23 (see docs/LIVE_VALIDATION.md for the
raw envelopes), so replay fixtures and live responses share one shape.

Every envelope carries `completed_steps` and an optional `error`: the CLI reports
vendor refusals *inside* a well-formed envelope (with a `*_failed` status) rather
than by omitting it, so these models must be able to represent failure without
losing the diagnostic. Deciding success from `status` is `live.py`'s job.
"""

from __future__ import annotations

from pydantic import BaseModel


class CreateEnvelope(BaseModel):
    """`brightdata scraper create` result."""

    collector_id: str
    name: str = ""
    # "done" | "failed" | "ai_trigger_failed" (AI Flow refused) | ...
    status: str
    completed_steps: list[str] = []
    view_url: str = ""
    created_at: str = ""
    error: str | None = None


class RunResult(BaseModel):
    """`brightdata scraper run` result (normalized to a single payload)."""

    collector_id: str
    status: str  # "done" | "failed"
    payload: dict | None = None
    http_status: int = 200
    credits_spent: int = 1
    error: str | None = None


class HealEnvelope(BaseModel):
    """`brightdata scraper heal` result — stops at the approval gate by design."""

    collector_id: str
    # "awaiting_approval" | "done" | "failed" | "heal_trigger_failed" (heal refused)
    status: str
    completed_steps: list[str] = []
    prompt: str = ""
    preview_result: list[dict] | dict | None = None
    diff_summary: str = ""
    view_url: str = ""
    next_step: str = ""
    error: str | None = None

    def preview_payload(self) -> dict | None:
        """The CLI returns a list sample; our sources extract one document per page."""
        if isinstance(self.preview_result, list):
            return self.preview_result[0] if self.preview_result else None
        return self.preview_result


class ApproveEnvelope(BaseModel):
    """`brightdata scraper approve [--reject]` result.

    The CLI returns the heal-shaped envelope here; `resume_failed` is what a
    rejected/absent automation job looks like.
    """

    collector_id: str
    status: str  # "done" | "rejected" | "failed" | "resume_failed"
    approved: bool
    completed_steps: list[str] = []
    error: str | None = None


class DiscoverResult(BaseModel):
    """`brightdata discover` result (used for Class 5 relocation proposals).

    Normalized shape: [{url, title, score, reason}]. The live API speaks
    {link, title, relevance_score, description}; `live._normalize_candidate`
    translates at the seam so nothing above this layer sees two vocabularies.
    """

    query: str
    candidates: list[dict] = []
