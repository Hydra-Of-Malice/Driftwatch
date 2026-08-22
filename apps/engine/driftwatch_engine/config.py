"""Typed runtime configuration, sourced from environment variables.

Single source of truth for every tunable. No secrets are ever committed;
see .env.example at the repo root.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_DIR = REPO_ROOT / "fixtures"
MIRROR_DIR = REPO_ROOT / "mirror"
WEB_DIR = REPO_ROOT / "apps" / "web"


def _load_dotenv(path: Path) -> None:
    """Minimal stdlib .env loader: KEY=VALUE lines; real environment always wins."""
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(REPO_ROOT / ".env")


class Settings(BaseModel):
    """Runtime settings. `mode` decides whether Bright Data calls are live or replayed."""

    mode: str = "replay"  # "replay" (recorded envelopes, offline) | "live" (real Bright Data API)
    db_path: str = str(REPO_ROOT / "driftwatch.db")
    host: str = "127.0.0.1"  # set DW_HOST=0.0.0.0 explicitly to expose beyond localhost
    port: int = 8000
    api_token: str | None = None  # set DW_API_TOKEN to require `Authorization: Bearer <token>` on /api/*
    brightdata_api_key: str | None = None
    anthropic_api_key: str | None = None
    slack_webhook_url: str | None = None
    # Confidence bands for the heal approval policy (see healing/orchestrator.py).
    auto_approve_threshold: float = 0.90
    auto_reject_threshold: float = 0.50
    # Guard: heal prompts must fit Bright Data's documented limit.
    heal_prompt_max_chars: int = 1000
    credits_per_page_load: int = 1
    # Hard ceiling on Bright Data credit spend (free tier: 5,000/month; keep a safety margin).
    credit_budget: int = 4500

    @classmethod
    def from_env(cls) -> Settings:
        def _get(name: str, default: str | None = None) -> str | None:
            value = os.environ.get(name, default)
            return value if value not in ("", None) else None

        return cls(
            mode=_get("DW_MODE", "replay") or "replay",
            db_path=_get("DW_DB_PATH", str(REPO_ROOT / "driftwatch.db")) or str(REPO_ROOT / "driftwatch.db"),
            host=_get("DW_HOST", "127.0.0.1") or "127.0.0.1",
            port=int(_get("DW_PORT", "8000") or "8000"),
            api_token=_get("DW_API_TOKEN"),
            credit_budget=int(_get("DW_CREDIT_BUDGET", "4500") or "4500"),
            brightdata_api_key=_get("BRIGHTDATA_API_KEY"),
            anthropic_api_key=_get("ANTHROPIC_API_KEY"),
            slack_webhook_url=_get("DW_SLACK_WEBHOOK"),
        )


settings = Settings.from_env()
