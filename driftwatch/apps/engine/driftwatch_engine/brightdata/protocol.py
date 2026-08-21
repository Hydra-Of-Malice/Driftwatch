"""The Bright Data client seam.

Everything above this interface is identical in replay and live modes; flipping
DW_MODE=live (plus BRIGHTDATA_API_KEY) is the only change needed to go from the
offline reference build to real Scraper Studio calls.
"""

from __future__ import annotations

from typing import Protocol

from .envelopes import ApproveEnvelope, CreateEnvelope, DiscoverResult, HealEnvelope, RunResult


class BrightDataClient(Protocol):
    """Scraper Studio lifecycle + discovery, as used by the pipeline."""

    def create_scraper(self, url: str, description: str, name: str) -> CreateEnvelope:
        """Natural-language scraper creation (Scraper Studio AI Flow)."""
        ...

    def run_scraper(self, collector_id: str, url: str, version: int | None = None) -> RunResult:
        """Execute the scraper; `version` pins a specific template version (rollback support)."""
        ...

    def heal_scraper(self, collector_id: str, prompt: str, url: str) -> HealEnvelope:
        """Request an AI repair. Returns at the `awaiting_approval` gate with a preview."""
        ...

    def approve(self, collector_id: str, *, reject: bool = False) -> ApproveEnvelope:
        """Commit or reject the pending heal."""
        ...

    def discover(self, query: str, intent: str) -> DiscoverResult:
        """AI web discovery — used to propose relocations for Class 5 (availability) drift."""
        ...
