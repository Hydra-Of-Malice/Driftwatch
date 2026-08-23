"""Live Bright Data client — wraps the official `brightdata` CLI.

Rationale: the CLI already handles auth, AI-Flow polling, the 3-concurrent-job
cap with backoff, and stable JSON envelopes (`--json` / `-o`). Wrapping it keeps
this integration honest to the documented surface and trivially auditable.
Requires: `npm i -g @brightdata/cli` and BRIGHTDATA_API_KEY (or `brightdata login`).

NOTE (Day-0 spike): before hackathon kickoff, run each method once against a toy
page and adjust envelope parsing if the installed CLI version differs.
"""

from __future__ import annotations

import json
import shutil
import subprocess

from ..errors import BrightDataError, ConfigError
from .envelopes import ApproveEnvelope, CreateEnvelope, DiscoverResult, HealEnvelope, RunResult


class LiveClient:
    """BrightDataClient implementation shelling out to the official CLI."""

    def __init__(self, api_key: str | None) -> None:
        if not api_key:
            raise ConfigError("DW_MODE=live requires BRIGHTDATA_API_KEY")
        if shutil.which("brightdata") is None:
            raise ConfigError("live mode requires the Bright Data CLI: npm i -g @brightdata/cli")
        self.api_key = api_key
        self.credits_spent = 0

    def _cli(self, *args: str, timeout: int = 900) -> dict:
        cmd = ["brightdata", *args, "--json"]
        proc = subprocess.run(  # noqa: S603 - fixed binary, no shell
            cmd, capture_output=True, text=True, timeout=timeout,
            env={"BRIGHTDATA_API_KEY": self.api_key, "PATH": "/usr/local/bin:/usr/bin:/bin"},
        )
        if proc.returncode != 0:
            raise BrightDataError(f"CLI failed: {' '.join(args[:2])}", stderr=proc.stderr[-500:])
        try:
            return json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise BrightDataError("CLI returned non-JSON output", head=proc.stdout[:200]) from exc

    def create_scraper(self, url: str, description: str, name: str) -> CreateEnvelope:
        data = self._cli("scraper", "create", url, description, "--name", name)
        return CreateEnvelope.model_validate(data)

    def run_scraper(self, collector_id: str, url: str, version: int | None = None) -> RunResult:
        args = ["scraper", "run", collector_id, url]
        if version is not None:
            args += ["--version", str(version)]
        data = self._cli(*args)
        self.credits_spent += 1
        payload = data[0] if isinstance(data, list) and data else data
        return RunResult(collector_id=collector_id, status="done", payload=payload)

    def heal_scraper(self, collector_id: str, prompt: str, url: str) -> HealEnvelope:
        data = self._cli("scraper", "heal", collector_id, prompt, "--url", url)
        return HealEnvelope.model_validate(data)

    def approve(self, collector_id: str, *, reject: bool = False) -> ApproveEnvelope:
        args = ["scraper", "approve", collector_id] + (["--reject"] if reject else [])
        data = self._cli(*args)
        status = str(data.get("status", "done"))
        return ApproveEnvelope(collector_id=collector_id, status=status, approved=not reject and status == "done")

    def discover(self, query: str, intent: str) -> DiscoverResult:
        data = self._cli("discover", query, "--intent", intent, "--num-results", "5")
        candidates = data.get("results", data) if isinstance(data, dict) else data
        return DiscoverResult(query=query, candidates=candidates if isinstance(candidates, list) else [])
