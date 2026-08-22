"""Pydantic models of Bright Data CLI/API response envelopes.

Field names mirror the real CLI's JSON output (verified against the official
@brightdata/cli README, Aug 2026) so that replay fixtures and live responses
share one shape.
"""

from __future__ import annotations

from pydantic import BaseModel


class CreateEnvelope(BaseModel):
    """`brightdata scraper create` result."""

    collector_id: str
    name: str
    status: str  # "done" | "failed" | ...
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
    status: str  # "awaiting_approval" | "done" | "failed"
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
    """`brightdata scraper approve [--reject]` result."""

    collector_id: str
    status: str  # "done" | "rejected" | "failed"
    approved: bool
    error: str | None = None


class DiscoverResult(BaseModel):
    """`brightdata discover` result (used for Class 5 relocation proposals)."""

    query: str
    candidates: list[dict] = []  # [{url, title, score, reason}]
