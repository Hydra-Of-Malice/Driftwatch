"""Typed runtime configuration, sourced from environment variables.

Single source of truth for every tunable. No secrets are ever committed;
see .env.example at the repo root.
"""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel

# errors.py imports nothing from this module (it has no project-local imports at
# all), so this direction is safe and cannot cycle.
from .errors import ConfigError

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO_ROOT / "fixtures"
MIRROR_DIR = REPO_ROOT / "mirror"
WEB_DIR = REPO_ROOT / "frontend"


def _load_dotenv(path: Path) -> None:
    """Minimal stdlib .env loader: KEY=VALUE lines; real environment always wins."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
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
    # Opt-in relaxation for the PUBLIC demo deployment only. With DW_API_TOKEN set and this
    # false (the default), every /api/* route needs the bearer token. Setting it true opens
    # reads and the demo-driving writes to anonymous visitors while STILL gating routes with
    # real-world side effects (`/api/onboard` creates Bright Data collectors and spends
    # credits). A browser SPA cannot hide a bearer token from its own viewer, so this is the
    # only way a public demo and a real auth gate can coexist. See render.yaml.
    public_demo: bool = False
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

        settings = cls(
            mode=_get("DW_MODE", "replay") or "replay",
            db_path=_get("DW_DB_PATH", str(REPO_ROOT / "driftwatch.db")) or str(REPO_ROOT / "driftwatch.db"),
            host=_get("DW_HOST", "127.0.0.1") or "127.0.0.1",
            port=int(_get("DW_PORT", "8000") or "8000"),
            api_token=_get("DW_API_TOKEN"),
            public_demo=(_get("DW_PUBLIC_DEMO", "") or "").lower() in ("1", "true", "yes"),
            credit_budget=int(_get("DW_CREDIT_BUDGET", "4500") or "4500"),
            brightdata_api_key=_get("BRIGHTDATA_API_KEY"),
            anthropic_api_key=_get("ANTHROPIC_API_KEY"),
            slack_webhook_url=_get("DW_SLACK_WEBHOOK"),
        )
        validate_live_config(settings)
        return settings


def validate_live_config(settings: Settings) -> None:
    """Fail loudly when `DW_MODE=live` cannot possibly work.

    Live mode without a credential is unrunnable: `build_deps` constructs a
    `LiveClient`, which refuses to exist without an API key. Catching it here
    means the process dies at startup with an actionable message instead of at
    the first scheduled run, and — critically — there is no path in which a
    misconfigured live deploy quietly serves replayed fixtures and calls them
    live data. Silent degradation would make every number in the UI a lie.

    A no-op for replay mode, so `Settings(mode="replay", ...)` built directly
    (tests, embedding callers) is unaffected. Exposed as a module-level function
    so an app that constructs `Settings` some other way can enforce the same
    invariant.
    """
    if settings.mode != "live":
        return
    if not settings.brightdata_api_key:
        raise ConfigError(
            "DW_MODE=live requires BRIGHTDATA_API_KEY, which is not set.\n"
            "  Fix one of:\n"
            "    - export BRIGHTDATA_API_KEY=<key>  (or add it to .env; get a key at\n"
            "      https://brightdata.com/cp/setting/users)\n"
            "    - set DW_MODE=replay to run the offline demo against recorded envelopes\n"
            "  Refusing to start: live mode will not silently fall back to replay.",
            mode=settings.mode,
            missing="BRIGHTDATA_API_KEY",
        )


settings = Settings.from_env()
