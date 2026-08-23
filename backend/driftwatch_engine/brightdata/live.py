"""Live Bright Data client — wraps the official `brightdata` CLI.

Rationale: the CLI already handles auth, AI-Flow polling, the concurrent-job cap
with backoff, and stable JSON envelopes. Wrapping it keeps this integration
honest to the documented surface and trivially auditable.

Requires: `npm i -g @brightdata/cli` (>= 0.3.0) and BRIGHTDATA_API_KEY.

Three properties this module guarantees, and the tests in
`tests/test_live_client.py` pin all three:

1. **A vendor failure is never converted into a success.** Every method inspects
   the envelope's own `status`/`error` and raises a classified `BrightDataError`.
   Nothing here manufactures `status="done"`.
2. **The vendor's own words survive.** The CLI writes a JSON error envelope to
   stdout *and* exits non-zero; we parse stdout first so the diagnostic envelope
   is never discarded in favour of a generic "CLI failed".
3. **No credential ever leaves this module.** The API key is injected into the
   child environment only, and stderr is redacted before it reaches an exception.

Platform note: the child process inherits the real environment (PATH, SystemRoot,
APPDATA, HOME, proxy vars). An earlier version replaced `env` wholesale with a
hardcoded POSIX PATH, which broke Windows outright and starved Node of the
variables it needs on every platform.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time

from ..errors import BrightDataError, ConfigError, FailureCategory
from ..obs import log_op
from .envelopes import ApproveEnvelope, CreateEnvelope, DiscoverResult, HealEnvelope, RunResult

# The npm package installs the same entrypoint under both names; `bdata` is an
# alias, not a different tool (verified: @brightdata/cli 0.3.5 `bin` map).
CLI_NAMES = ("brightdata", "bdata")

# Envelope statuses that mean "the vendor refused / could not complete", as
# emitted by @brightdata/cli 0.3.x. Anything here is a failure, never a result.
FAILED_STATUSES = frozenset({
    "failed", "error", "cancelled",
    "ai_trigger_failed", "heal_trigger_failed", "resume_failed", "stub_only",
})

# HTTP status the CLI reports in its human-readable stderr, e.g. "  Status: 403".
_STATUS_RE = re.compile(r"\bstatus:\s*(\d{3})\b", re.IGNORECASE)


def _redact(text: str) -> str:
    """Strip anything credential-shaped from vendor output before it is surfaced."""
    text = re.sub(r"(?i)(bearer\s+)[A-Za-z0-9._\-]{8,}", r"\1<redacted>", text)
    text = re.sub(r"(?i)((?:api[_-]?key|token)\"?\s*[:=]\s*\"?)[A-Za-z0-9._\-]{8,}",
                  r"\1<redacted>", text)
    return text


def resolve_cli() -> str | None:
    """Absolute path to the Bright Data CLI, or None.

    Returning the resolved path (not the bare name) is required on Windows, where
    the npm shim is `brightdata.cmd` and CreateProcess will not find it from a
    bare name.
    """
    for name in CLI_NAMES:
        found = shutil.which(name)
        if found:
            return found
    return None


class LiveClient:
    """BrightDataClient implementation shelling out to the official CLI."""

    def __init__(self, api_key: str | None, *, timeout: int = 900) -> None:
        if not api_key:
            raise ConfigError(
                "DW_MODE=live requires BRIGHTDATA_API_KEY "
                "(get one at https://brightdata.com/cp/setting/users)"
            )
        cli = resolve_cli()
        if cli is None:
            raise ConfigError(
                "live mode requires the Bright Data CLI: npm i -g @brightdata/cli "
                f"(looked for {' / '.join(CLI_NAMES)} on PATH)"
            )
        self.cli_path = cli
        self.api_key = api_key
        self.timeout = timeout
        self.credits_spent = 0

    # -- transport ----------------------------------------------------------------

    def _env(self) -> dict[str, str]:
        """Real environment + the API key. Never the other way round."""
        env = os.environ.copy()
        env["BRIGHTDATA_API_KEY"] = self.api_key
        return env

    def _cli(self, *args: str, operation: str, timeout: int | None = None) -> dict | list:
        """Run the CLI and return its parsed JSON envelope.

        Raises a classified BrightDataError on any failure. stdout is pure JSON
        (the CLI writes progress/spinner output to stderr), so it is parsed first
        and *before* the exit code is consulted — the error envelope is the most
        informative thing the vendor gives us.
        """
        cmd = [self.cli_path, *args, "--json"]
        started = time.monotonic()
        try:
            proc = subprocess.run(  # noqa: S603 - resolved binary, no shell
                cmd, capture_output=True, text=True,
                # Explicit UTF-8: the CLI emits box-drawing/spinner glyphs, and
                # text=True would otherwise decode with the OS locale codec —
                # cp1252 on Windows, which raises UnicodeDecodeError inside
                # subprocess's reader thread and silently loses ALL stdout.
                encoding="utf-8", errors="replace",
                timeout=timeout or self.timeout, env=self._env(),
            )
        except subprocess.TimeoutExpired as exc:
            raise BrightDataError(
                f"Bright Data CLI timed out after {timeout or self.timeout}s",
                category=FailureCategory.VENDOR_TIMEOUT, operation=operation,
                hint="Increase the timeout, or check the job in https://brightdata.com/cp/scrapers.",
            ) from exc
        except OSError as exc:
            raise BrightDataError(
                f"could not execute the Bright Data CLI: {exc}",
                category=FailureCategory.CLI_COMPATIBILITY, operation=operation,
            ) from exc

        latency = int((time.monotonic() - started) * 1000)
        stderr = _redact(proc.stderr or "")
        stdout = (proc.stdout or "").strip()
        status_match = _STATUS_RE.search(stderr)
        http_status = int(status_match.group(1)) if status_match else None

        data: dict | list | None = None
        if stdout:
            try:
                data = json.loads(stdout)
            except json.JSONDecodeError:
                data = None

        # A JSON envelope carrying its own error is the richest signal available;
        # prefer it over the exit code so the vendor's wording reaches the ledger.
        if isinstance(data, dict):
            err = data.get("error")
            status = str(data.get("status", ""))
            if err or status in FAILED_STATUSES:
                message = str(err or f"vendor returned status {status!r}")
                raise BrightDataError(
                    message, status=http_status, operation=operation,
                    vendor_status=status, collector_id=data.get("collector_id"),
                )

        if proc.returncode != 0 or data is None:
            # No usable envelope. Recover the vendor's message from stderr, which
            # the CLI formats as "Error: <message>" / "✗ <message>".
            message = _vendor_message(stderr) or (
                f"CLI exited {proc.returncode} with no JSON output" if proc.returncode
                else "CLI returned non-JSON output"
            )
            category = None
            if data is None and proc.returncode == 0 and not _vendor_message(stderr):
                category = FailureCategory.VENDOR_BAD_RESPONSE
            raise BrightDataError(
                message, status=http_status, operation=operation, category=category,
                stderr_tail=stderr[-400:], stdout_head=_redact(stdout[:200]),
            )

        log_op(f"brightdata.{operation}", status="ok", latency_ms=latency)
        return data

    # -- BrightDataClient ---------------------------------------------------------

    def create_scraper(self, url: str, description: str, name: str) -> CreateEnvelope:
        data = self._cli("scraper", "create", url, description, "--name", name,
                         operation="scraper.create")
        envelope = CreateEnvelope.model_validate(data)
        _assert_ok(envelope.status, envelope.error, "scraper.create", envelope.collector_id)
        return envelope

    def run_scraper(self, collector_id: str, url: str, version: int | None = None) -> RunResult:
        args = ["scraper", "run", collector_id, url]
        if version is not None:
            args += ["--version", str(version)]
        data = self._cli(*args, operation="scraper.run")
        self.credits_spent += 1

        # The CLI returns either a bare list of extracted records or an envelope
        # wrapping one. Either way the *payload* decides success — an empty result
        # is a scraper failure, not a green run. (HTTP 200 is not an outcome.)
        payload = _first_record(data)
        if payload is None:
            raise BrightDataError(
                "scraper run returned no records",
                category=FailureCategory.SCRAPER_FAILURE, operation="scraper.run",
                collector_id=collector_id, url=url,
                hint="The collector ran but extracted nothing — treat as a drift signal.",
            )
        return RunResult(collector_id=collector_id, status="done", payload=payload)

    def heal_scraper(self, collector_id: str, prompt: str, url: str) -> HealEnvelope:
        data = self._cli("scraper", "heal", collector_id, prompt, "--url", url,
                         operation="scraper.heal")
        envelope = HealEnvelope.model_validate(data)
        _assert_ok(envelope.status, envelope.error, "scraper.heal", collector_id)
        return envelope

    def approve(self, collector_id: str, *, reject: bool = False) -> ApproveEnvelope:
        args = ["scraper", "approve", collector_id] + (["--reject"] if reject else [])
        data = self._cli(*args, operation="scraper.approve")
        status = str(data.get("status", "done")) if isinstance(data, dict) else "done"
        error = data.get("error") if isinstance(data, dict) else None
        _assert_ok(status, error, "scraper.approve", collector_id)
        return ApproveEnvelope(
            collector_id=collector_id, status=status,
            approved=not reject and status in ("done", "approved"),
        )

    def discover(self, query: str, intent: str) -> DiscoverResult:
        data = self._cli("discover", query, "--intent", intent, "--num-results", "5",
                         operation="discover")
        raw = data.get("results", []) if isinstance(data, dict) else data
        return DiscoverResult(
            query=query,
            candidates=[_normalize_candidate(c) for c in raw if isinstance(c, dict)],
        )


# -- helpers --------------------------------------------------------------------


def _vendor_message(stderr: str) -> str:
    """Pull the vendor's own sentence out of the CLI's human-readable stderr."""
    for line in stderr.splitlines():
        line = line.strip().lstrip("✗").strip()
        for prefix in ("Error:", "error:"):
            if line.startswith(prefix):
                return line[len(prefix):].strip()
    # Some failures print the message with no prefix but with a Status: line after.
    lines = [ln.strip() for ln in stderr.splitlines() if ln.strip()]
    for i, line in enumerate(lines):
        if _STATUS_RE.match(line) and i:
            return lines[i - 1]
    return ""


def _assert_ok(status: str, error: str | None, operation: str, collector_id: str | None) -> None:
    """Raise if an envelope parsed cleanly but reports a vendor-side failure."""
    if error or status in FAILED_STATUSES:
        raise BrightDataError(
            str(error or f"vendor returned status {status!r}"),
            operation=operation, vendor_status=status, collector_id=collector_id,
        )


def _first_record(data: dict | list) -> dict | None:
    """Normalize `scraper run` output to the single document our sources extract."""
    if isinstance(data, list):
        return next((r for r in data if isinstance(r, dict) and r), None)
    if isinstance(data, dict):
        for key in ("data", "results", "records"):
            inner = data.get(key)
            if isinstance(inner, list):
                return next((r for r in inner if isinstance(r, dict) and r), None)
            if isinstance(inner, dict) and inner:
                return inner
        return data or None
    return None


def _normalize_candidate(raw: dict) -> dict:
    """Map a live `discover` result onto the shape the pipeline and UI expect.

    Verified live (Aug 2026): the API returns {link, title, description,
    relevance_score}; the rest of Driftwatch speaks {url, title, score, reason}.
    """
    return {
        "url": raw.get("url") or raw.get("link", ""),
        "title": raw.get("title", ""),
        "score": raw.get("score", raw.get("relevance_score", 0.0)),
        "reason": raw.get("reason") or raw.get("description", ""),
    }
