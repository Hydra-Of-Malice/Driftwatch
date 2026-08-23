"""Live-client contract tests.

These pin the three properties that make the live seam trustworthy, using the
*real* envelopes captured from @brightdata/cli 0.3.5 on 2026-08-23:

1. a vendor refusal never becomes a success,
2. the vendor's own wording and HTTP status survive into the error, and
3. no credential leaks into an exception or a log line.

The CLI itself is stubbed at the subprocess boundary — that is the only thing
these tests fake. The envelope bodies are verbatim vendor output.
"""

from __future__ import annotations

import json
import subprocess
import unittest
from unittest import mock

from driftwatch_engine.brightdata.live import LiveClient, _normalize_candidate, _vendor_message
from driftwatch_engine.errors import BrightDataError, ConfigError, FailureCategory

# Verbatim envelopes captured live (docs/LIVE_VALIDATION.md).
CREATE_REFUSED = {
    "collector_id": "c_mt3vr49h1qtwyctl1g", "name": "driftwatch-spike",
    "status": "ai_trigger_failed", "completed_steps": [],
    "view_url": "https://brightdata.com/cp/scrapers/c_mt3vr49h1qtwyctl1g",
    "created_at": "2026-08-22T04:30:29.717Z", "error": "Automation not allowed",
}
HEAL_REFUSED = {
    "collector_id": "c_msqexhu61uaxbv00x4", "status": "heal_trigger_failed",
    "completed_steps": [], "prompt": "Price must be a plain number.",
    "view_url": "https://brightdata.com/cp/scrapers/c_msqexhu61uaxbv00x4",
    "next_step": "bdata scraper run c_msqexhu61uaxbv00x4 https://example.test",
    "error": "Self healing tool is temporarily disabled",
}
APPROVE_REFUSED = {
    "collector_id": "c_msqexhu61uaxbv00x4", "status": "resume_failed",
    "completed_steps": [], "prompt": "", "error": "Automation not found",
}
DISCOVER_LIVE = {
    "status": "done",
    "results": [
        {"link": "https://www.usenimbus.com/pricing/", "title": "Pricing - Nimbus",
         "description": "Nimbus Cloud Self-hosted lite $25/mo/user.",
         "relevance_score": 0.60546875},
    ],
}

SECRET = "super-secret-api-key-value-1234"


def _proc(stdout: str = "", stderr: str = "", returncode: int = 0):
    return subprocess.CompletedProcess(args=[], returncode=returncode,
                                       stdout=stdout, stderr=stderr)


class LiveClientTest(unittest.TestCase):
    def setUp(self) -> None:
        patcher = mock.patch("driftwatch_engine.brightdata.live.resolve_cli",
                             return_value="C:\\fake\\brightdata.cmd")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = LiveClient(SECRET)

    def _run(self, **kwargs):
        return mock.patch("subprocess.run", return_value=_proc(**kwargs))

    # -- guarantee 1: a refusal is never a success -------------------------------

    def test_create_refusal_raises_and_is_classified(self):
        with self._run(stdout=json.dumps(CREATE_REFUSED), returncode=1), self.assertRaises(BrightDataError) as ctx:
            self.client.create_scraper("https://example.test", "extract things", "spike")
        err = ctx.exception
        self.assertEqual(err.category, FailureCategory.VENDOR_PERMISSION)
        self.assertIn("Automation not allowed", str(err))
        # The diagnostic collector id survives for the ledger.
        self.assertEqual(err.context.get("collector_id"), "c_mt3vr49h1qtwyctl1g")

    def test_heal_disabled_is_vendor_unavailable_not_scraper_failure(self):
        with self._run(stdout=json.dumps(HEAL_REFUSED), returncode=1), self.assertRaises(BrightDataError) as ctx:
            self.client.heal_scraper("c_x", "fix price", "https://example.test")
        self.assertEqual(ctx.exception.category, FailureCategory.VENDOR_UNAVAILABLE)
        self.assertNotEqual(ctx.exception.category, FailureCategory.SCRAPER_FAILURE)

    def test_approve_refusal_raises(self):
        with self._run(stdout=json.dumps(APPROVE_REFUSED), returncode=1), self.assertRaises(BrightDataError):
            self.client.approve("c_msqexhu61uaxbv00x4")

    def test_empty_run_is_a_scraper_failure_not_a_green_run(self):
        """HTTP 200 with zero records must not be reported as a successful run."""
        with self._run(stdout="[]"), self.assertRaises(BrightDataError) as ctx:
            self.client.run_scraper("c_x", "https://example.test")
        self.assertEqual(ctx.exception.category, FailureCategory.SCRAPER_FAILURE)

    def test_successful_run_returns_payload(self):
        with self._run(stdout=json.dumps([{"title": "A Light in the Attic", "price": 51.77}])):
            result = self.client.run_scraper("c_x", "https://example.test")
        self.assertEqual(result.status, "done")
        self.assertEqual(result.payload["price"], 51.77)
        self.assertEqual(self.client.credits_spent, 1)

    # -- guarantee 2: vendor wording + status survive ----------------------------

    def test_non_json_stderr_failure_recovers_vendor_message_and_status(self):
        stderr = ('Failed to trigger scraper: Error: {"error":"Collector does not have a template"}\n'
                  "  Status: 403\n")
        with self._run(stdout="", stderr=stderr, returncode=1), self.assertRaises(BrightDataError) as ctx:
            self.client.run_scraper("c_x", "https://example.test")
        err = ctx.exception
        self.assertEqual(err.status, 403)
        self.assertIn("does not have a template", str(err))
        self.assertEqual(err.category, FailureCategory.CLI_COMPATIBILITY)

    def test_timeout_is_classified(self):
        with mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired("brightdata", 1)), self.assertRaises(BrightDataError) as ctx:
            self.client.run_scraper("c_x", "https://example.test")
        self.assertEqual(ctx.exception.category, FailureCategory.VENDOR_TIMEOUT)

    def test_malformed_json_is_classified(self):
        with self._run(stdout="not json at all", returncode=0), self.assertRaises(BrightDataError) as ctx:
            self.client.run_scraper("c_x", "https://example.test")
        self.assertEqual(ctx.exception.category, FailureCategory.VENDOR_BAD_RESPONSE)

    def test_vendor_message_extraction(self):
        self.assertEqual(_vendor_message("✗ Error: Automation not allowed\n"),
                         "Automation not allowed")
        self.assertEqual(_vendor_message("Your API key lacks permissions\n  Status: 403\n"),
                         "Your API key lacks permissions")

    # -- guarantee 3: no credential leaks ----------------------------------------

    def test_api_key_never_appears_in_raised_error(self):
        stderr = f"Error: auth failed with Bearer {SECRET}\n  Status: 401\n"
        with self._run(stdout="", stderr=stderr, returncode=1), self.assertRaises(BrightDataError) as ctx:
            self.client.run_scraper("c_x", "https://example.test")
        blob = json.dumps(ctx.exception.to_dict())
        self.assertNotIn(SECRET, blob)
        self.assertIn("<redacted>", blob)

    def test_api_key_is_injected_without_wiping_the_environment(self):
        """Regression: an earlier build replaced env with a hardcoded POSIX PATH,
        which broke Windows and starved Node of SystemRoot/APPDATA everywhere."""
        with mock.patch("subprocess.run", return_value=_proc(stdout="[{\"a\":1}]")) as run:
            self.client.run_scraper("c_x", "https://example.test")
        env = run.call_args.kwargs["env"]
        self.assertEqual(env["BRIGHTDATA_API_KEY"], SECRET)
        # Inherited, not replaced: PATH must still be the real one.
        import os
        self.assertEqual(env.get("PATH"), os.environ.get("PATH"))
        self.assertGreater(len(env), 3)

    def test_subprocess_decodes_as_utf8(self):
        """Regression (caught against the real CLI, not a mock): `text=True` alone
        decodes with the OS locale codec. On Windows that is cp1252, and the CLI's
        spinner glyphs raise UnicodeDecodeError inside subprocess's reader thread,
        losing ALL stdout and turning every live call into VENDOR_BAD_RESPONSE."""
        with mock.patch("subprocess.run", return_value=_proc(stdout="[{\"a\":1}]")) as run:
            self.client.run_scraper("c_x", "https://example.test")
        self.assertEqual(run.call_args.kwargs["encoding"], "utf-8")
        self.assertEqual(run.call_args.kwargs["errors"], "replace")

    def test_cli_invoked_by_resolved_absolute_path(self):
        """Windows CreateProcess cannot launch the `brightdata.cmd` npm shim from
        a bare name; the resolved path is required."""
        with mock.patch("subprocess.run", return_value=_proc(stdout="[{\"a\":1}]")) as run:
            self.client.run_scraper("c_x", "https://example.test")
        self.assertEqual(run.call_args.args[0][0], "C:\\fake\\brightdata.cmd")

    # -- config + normalization ---------------------------------------------------

    def test_missing_key_is_a_config_error(self):
        with self.assertRaises(ConfigError):
            LiveClient(None)

    def test_missing_cli_is_a_config_error(self):
        with mock.patch("driftwatch_engine.brightdata.live.resolve_cli", return_value=None), self.assertRaises(ConfigError):
            LiveClient(SECRET)

    def test_discover_normalizes_live_field_names(self):
        with self._run(stdout=json.dumps(DISCOVER_LIVE)):
            result = self.client.discover("nimbus pricing", "official pricing page")
        candidate = result.candidates[0]
        self.assertEqual(candidate["url"], "https://www.usenimbus.com/pricing/")
        self.assertAlmostEqual(candidate["score"], 0.60546875)
        self.assertIn("Nimbus Cloud", candidate["reason"])

    def test_normalize_candidate_accepts_both_vocabularies(self):
        canonical = {"url": "u", "title": "t", "score": 0.5, "reason": "r"}
        self.assertEqual(_normalize_candidate(canonical), canonical)


if __name__ == "__main__":
    unittest.main()
