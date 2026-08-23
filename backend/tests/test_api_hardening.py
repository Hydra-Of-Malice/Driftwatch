"""Input-validation tests for the onboarding surface.

`source_id` becomes BOTH a filesystem path (`fixtures/contracts/<id>.yaml`) and a
primary key, and `url` is handed to the Bright Data CLI as an argv element. Both
were previously accepted verbatim. These tests pin the boundary.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from driftwatch_engine.api.app import create_app  # noqa: E402
from driftwatch_engine.config import Settings  # noqa: E402
from tests.helpers import EngineTestCase  # noqa: E402

TRAVERSAL_IDS = ["../../etc/passwd", "..\\..\\windows", "a/../../b", "../secrets"]
ABSOLUTE_IDS = ["/etc/shadow", "C:/Windows/system32", "\\\\server\\share"]
BAD_SCHEMES = ["file:///etc/passwd", "data:text/html,x", "ftp://h/x", "javascript:alert(1)"]


class OnboardValidationTest(EngineTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.http = create_app(self.settings, self.world).test_client()

    def _post(self, **over):
        body = {"id": "ok-source", "name": "Ok Source", "description": "extract things",
                "url": "https://example.test/pricing"}
        body.update(over)
        return self.http.post("/api/onboard", json=body)

    def test_path_traversal_source_id_is_rejected(self):
        """`../` in an id previously escaped the contracts directory."""
        for evil in TRAVERSAL_IDS:
            with self.subTest(evil=evil):
                resp = self._post(id=evil)
                self.assertEqual(resp.status_code, 400)
                self.assertEqual(resp.get_json()["error"], "invalid source id")

    def test_absolute_path_source_id_is_rejected(self):
        for evil in ABSOLUTE_IDS:
            with self.subTest(evil=evil):
                self.assertEqual(self._post(id=evil).status_code, 400)

    def test_non_http_schemes_are_rejected(self):
        for evil in BAD_SCHEMES:
            with self.subTest(evil=evil):
                resp = self._post(url=evil)
                self.assertEqual(resp.status_code, 400)
                self.assertEqual(resp.get_json()["error"], "invalid target url")

    def test_argv_flag_injection_url_is_rejected(self):
        """A URL starting with `-` would be read by the CLI as an option, not a value."""
        self.assertEqual(self._post(url="--deliver-webhook=https://attacker.test/x").status_code, 400)

    def test_valid_id_passes_validation(self):
        """A well-formed id must get PAST validation — it then fails on the missing
        contract with 422, which proves it reached the next stage."""
        self.assertNotEqual(self._post(id="valid-source_1").status_code, 400)


class AuthTest(EngineTestCase):
    def test_token_enforced_and_missing_header_rejected(self):
        settings = Settings(mode="replay", db_path=self.settings.db_path, api_token="s3cret")
        http = create_app(settings, self.world).test_client()
        self.assertEqual(http.get("/api/sources").status_code, 401)
        self.assertEqual(
            http.get("/api/sources", headers={"Authorization": "Bearer wrong"}).status_code, 401)
        self.assertEqual(
            http.get("/api/sources", headers={"Authorization": "Bearer s3cret"}).status_code, 200)

    def test_public_demo_opens_reads_and_demo_writes_but_never_onboard(self):
        """DW_PUBLIC_DEMO lets an anonymous SPA drive the demo while routes with
        real-world side effects stay gated. `/api/onboard` creates a Bright Data
        collector and spends credits, so it is behind the token in every config."""
        settings = Settings(mode="replay", db_path=self.settings.db_path,
                            api_token="s3cret", public_demo=True)
        http = create_app(settings, self.world).test_client()

        # reads: open
        self.assertEqual(http.get("/api/sources").status_code, 200)
        self.assertEqual(http.get("/api/meta").status_code, 200)
        # demo-safe writes: open (synthetic, local, no external effect)
        self.assertEqual(http.post("/api/demo/state",
                                   json={"source_id": "nimbusai-pricing",
                                         "variant": "v2_redesign"}).status_code, 200)
        self.assertEqual(http.post("/api/run/nimbusai-pricing").status_code, 200)
        # onboarding: STILL gated, because it reaches Bright Data and costs money
        self.assertEqual(http.post("/api/onboard", json={
            "id": "x", "name": "X", "description": "d", "url": "https://e.test"}).status_code, 401)
        # ...and works with the token
        self.assertNotEqual(http.post("/api/onboard", headers={"Authorization": "Bearer s3cret"},
                                      json={"id": "x", "name": "X", "description": "d",
                                            "url": "https://e.test"}).status_code, 401)

    def test_public_demo_is_opt_in_default_gates_everything(self):
        """Regression guard: the relaxation must never be the default."""
        settings = Settings(mode="replay", db_path=self.settings.db_path, api_token="s3cret")
        self.assertFalse(settings.public_demo)
        http = create_app(settings, self.world).test_client()
        self.assertEqual(http.get("/api/sources").status_code, 401)
        self.assertEqual(http.post("/api/run/nimbusai-pricing").status_code, 401)

    def test_review_of_unknown_heal_returns_json_not_an_html_500(self):
        """The SPA surfaces failures via the JSON taxonomy; an HTML 500 page is
        invisible to it and misreports a client error as a server fault."""
        http = create_app(self.settings, self.world).test_client()
        resp = http.post("/api/review/9999", json={"approve": True})
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.get_json()["code"], "not_reviewable")

    def test_meta_reports_replay_mode_honestly(self):
        """The UI badge must never be able to call a replay run 'live'."""
        data = create_app(self.settings, self.world).test_client().get("/api/meta").get_json()
        self.assertEqual(data["mode"], "replay")
        self.assertFalse(data["live"])
        self.assertFalse(data["live_ready"])
        self.assertEqual(data["gates"], ["schema", "invariants", "semantics", "continuity"])


if __name__ == "__main__":
    unittest.main()
