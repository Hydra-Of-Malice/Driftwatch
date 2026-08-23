"""HTTP surface: JSON API + static SPA + the demo mirror site.

One Flask app serves everything on one origin — the UI at /, the API under
/api/*, and the controlled mirror pages under /mirror/* (whose current variant
is what the replay Bright Data client "scrapes").
"""

from __future__ import annotations

import hmac
import re
import statistics
from urllib.parse import urlparse

from flask import Flask, jsonify, request, send_from_directory

from .. import db
from ..brightdata.live import LiveClient, resolve_cli
from ..brightdata.replay import ReplayClient, WorldState
from ..config import FIXTURES_DIR, MIRROR_DIR, WEB_DIR, Settings
from ..domain import CLASS_LABELS
from ..errors import BrightDataError, ConfigError, DriftwatchError, FailureCategory
from ..healing.orchestrator import decide_review
from ..llm.provider import make_provider
from ..pipeline.runner import Deps, run_source

VARIANTS = ["v1_baseline", "v2_redesign", "v3_semantic", "v4_material", "v5_gone"]

# Reachable with no token even when DW_API_TOKEN is set: the SPA shell, its static
# assets, and the demo mirror site (public web content by design, not API state).
PUBLIC_PATH_PREFIXES = ("/assets/", "/mirror/")

# Methods that change state. Everything else is a read.
WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

# Writes that mutate ONLY synthetic, local demo state — the mirror world variant, a pipeline
# run over fixtures, a review decision on a synthetic heal. None of them reach an external
# system, spend money, or touch a real customer source. In DW_PUBLIC_DEMO these stay open so
# an anonymous judge can actually drive the demonstration.
#
# `/api/onboard` is deliberately NOT here: it calls Bright Data to create a real collector
# and, in live mode, spends real credits. It stays behind the token in every configuration.
DEMO_SAFE_WRITE_PREFIXES = ("/api/demo/", "/api/run", "/api/review/")

# A source_id becomes a filesystem path (`fixtures/contracts/<id>.yaml`) and a
# primary key, so it is constrained to an unambiguous slug. Without this, an id
# like `../../secrets` escapes the contracts directory — `Path / "..."` happily
# walks upward, turning onboarding into an arbitrary-path read.
SOURCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


def _valid_source_id(source_id: str) -> bool:
    return bool(SOURCE_ID_RE.fullmatch(source_id))


def _valid_target_url(url: str) -> bool:
    """Public http(s) URLs only.

    Two distinct concerns: (1) the scheme allowlist keeps `file://`, `data:` and
    friends away from the scraper, and (2) a value starting with `-` would be
    parsed by the Bright Data CLI as an option rather than a positional argument,
    so it is rejected before it reaches argv.
    """
    if not url or url.startswith("-"):
        return False
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def build_deps(settings: Settings, world: WorldState) -> Deps:
    client = LiveClient(settings.brightdata_api_key) if settings.mode == "live" else ReplayClient(world)
    return Deps(client=client, provider=make_provider(settings.anthropic_api_key), settings=settings)


def create_app(settings: Settings, world: WorldState | None = None) -> Flask:
    world = world or WorldState()
    deps = build_deps(settings, world)
    app = Flask("driftwatch", static_folder=None)
    app.json.sort_keys = False  # keep payload field order as extracted (snapshot tables mirror the page)

    # -- auth ---------------------------------------------------------------------
    # Opt-in: unset DW_API_TOKEN preserves today's open-localhost-demo behaviour
    # exactly (see docs/06_Security/Security_Architecture.md). Set it to require
    # `Authorization: Bearer <token>` on every route except the SPA/assets/mirror.

    def _is_open_to_anonymous() -> bool:
        """Whether this request may proceed without the bearer token.

        Default (DW_PUBLIC_DEMO unset): only the SPA shell, its assets and the mirror
        site — every /api/* route is gated, which is the right posture for a private
        or live deployment driven by an operator who can send a header.

        DW_PUBLIC_DEMO=true: additionally open reads and the demo-safe writes, because
        the only client is an anonymous browser SPA that cannot hold a secret. Routes
        with external side effects stay gated regardless.
        """
        if request.path == "/" or request.path.startswith(PUBLIC_PATH_PREFIXES):
            return True
        if not settings.public_demo:
            return False
        if request.method not in WRITE_METHODS:
            return True
        return request.path.startswith(DEMO_SAFE_WRITE_PREFIXES)

    @app.before_request
    def _require_auth():
        if not settings.api_token:
            return None
        if _is_open_to_anonymous():
            return None
        expected = f"Bearer {settings.api_token}"
        # Constant-time: a plain `!=` leaks the shared secret's prefix by timing.
        if not hmac.compare_digest(request.headers.get("Authorization", ""), expected):
            return jsonify({"error": "unauthorized"}), 401
        return None

    # -- SPA + assets -----------------------------------------------------------

    @app.get("/")
    def index():
        return send_from_directory(WEB_DIR, "index.html")

    @app.get("/assets/<path:filename>")
    def assets(filename: str):
        return send_from_directory(WEB_DIR / "assets", filename)

    # -- demo mirror ------------------------------------------------------------

    @app.get("/mirror/<source_id>")
    def mirror(source_id: str):
        variant = world.variant(source_id)
        if variant == "v5_gone":
            return ("<h1>404 — page moved</h1>", 404)
        page = MIRROR_DIR / source_id / f"{variant}.html"
        if not page.exists():
            return (f"no mirror page for {source_id}/{variant}", 404)
        return send_from_directory(MIRROR_DIR / source_id, f"{variant}.html")

    @app.post("/api/demo/state")
    def demo_state():
        body = request.get_json(force=True)
        source_id, variant = body.get("source_id"), body.get("variant")
        if variant not in VARIANTS:
            return jsonify({"error": f"variant must be one of {VARIANTS}"}), 400
        world.set_variant(source_id, variant)
        db.audit("human", "demo.variant_set", {"source": source_id}, {"variant": variant})
        return jsonify({"source_id": source_id, "variant": variant})

    @app.get("/api/demo/state")
    def demo_state_get():
        return jsonify({s["id"]: world.variant(s["id"]) for s in db.query("SELECT id FROM sources")})

    # -- core API ---------------------------------------------------------------

    @app.get("/api/sources")
    def sources():
        rows = db.query("SELECT * FROM sources ORDER BY id")
        out = []
        for source in rows:
            last_run = db.query_one(
                "SELECT * FROM runs WHERE source_id = ? ORDER BY id DESC LIMIT 1", [source["id"]])
            last_event = db.query_one(
                "SELECT * FROM drift_events WHERE source_id = ? ORDER BY id DESC LIMIT 1", [source["id"]])
            scraper = db.query_one("SELECT * FROM scrapers WHERE source_id = ?", [source["id"]])
            out.append({**source, "last_run": last_run, "last_event": _event_json(last_event),
                        "scraper": scraper, "mirror_variant": world.variant(source["id"])})
        return jsonify(out)

    @app.get("/api/sources/<source_id>")
    def source_detail(source_id: str):
        source = db.query_one("SELECT * FROM sources WHERE id = ?", [source_id])
        if source is None:
            return jsonify({"error": "unknown source"}), 404
        contract = db.query_one(
            "SELECT * FROM contracts WHERE source_id = ? ORDER BY version DESC LIMIT 1", [source_id])
        scraper = db.query_one("SELECT * FROM scrapers WHERE source_id = ?", [source_id])
        runs = db.query("SELECT * FROM runs WHERE source_id = ? ORDER BY id DESC LIMIT 40", [source_id])
        snapshot = db.query_one(
            "SELECT * FROM snapshots WHERE source_id = ? AND quarantined = 0 ORDER BY id DESC LIMIT 1",
            [source_id])
        return jsonify({
            **source,
            "contract": {**contract, "spec": db.uj(contract["spec"])} if contract else None,
            "scraper": scraper, "runs": runs,
            "latest_snapshot": {**snapshot, "payload": db.uj(snapshot["payload"]),
                                "verdict": db.uj(snapshot["verdict"])} if snapshot else None,
            "mirror_variant": world.variant(source_id),
        })

    @app.get("/api/sources/<source_id>/timeline")
    def timeline(source_id: str):
        runs = db.query(
            "SELECT id, state, started_at, confidence, scraper_version FROM runs "
            "WHERE source_id = ? ORDER BY id DESC LIMIT 200", [source_id])
        events = db.query(
            "SELECT * FROM drift_events WHERE source_id = ? ORDER BY id DESC LIMIT 100", [source_id])
        heals = db.query(
            "SELECT * FROM heal_events WHERE source_id = ? ORDER BY id DESC LIMIT 50", [source_id])
        return jsonify({"runs": runs, "events": [_event_json(e) for e in events], "heals": heals})

    @app.get("/api/events")
    def events():
        limit = int(request.args.get("limit", 100))
        rows = db.query("SELECT * FROM drift_events ORDER BY id DESC LIMIT ?", [limit])
        return jsonify([_event_json(e) for e in rows])

    @app.get("/api/events/<int:event_id>")
    def event_detail(event_id: int):
        event = db.query_one("SELECT * FROM drift_events WHERE id = ?", [event_id])
        if event is None:
            return jsonify({"error": "unknown event"}), 404
        before = db.query_one("SELECT * FROM snapshots WHERE id = ?", [event["before_snapshot_id"]])
        after = db.query_one("SELECT * FROM snapshots WHERE id = ?", [event["after_snapshot_id"]])
        impact = db.query_one("SELECT * FROM impact_reports WHERE drift_event_id = ?", [event_id])
        alerts = db.query("SELECT * FROM alerts WHERE drift_event_id = ?", [event_id])
        heal = db.query_one("SELECT * FROM heal_events WHERE trigger_event_id = ?", [event_id])
        return jsonify({
            **_event_json(event),
            "before_payload": db.uj(before["payload"]) if before else None,
            "after_payload": db.uj(after["payload"]) if after else None,
            "after_verdict": db.uj(after["verdict"]) if after and after["verdict"] else None,
            "impact": {**impact, "affected": db.uj(impact["affected"])} if impact else None,
            "alerts": [{**a, "payload": db.uj(a["payload"])} for a in alerts],
            "heal": _heal_json(heal),
        })

    @app.get("/api/heals")
    def heals():
        rows = db.query("SELECT * FROM heal_events ORDER BY id DESC LIMIT 50")
        return jsonify([_heal_json(h) for h in rows])

    @app.get("/api/review")
    def review_queue():
        rows = db.query("SELECT * FROM heal_events WHERE status = 'review' ORDER BY id DESC")
        return jsonify([_heal_json(h) for h in rows])

    @app.post("/api/review/<int:heal_id>")
    def review_decide(heal_id: int):
        body = request.get_json(force=True)
        approve = bool(body.get("approve"))
        try:
            heal = decide_review(heal_id, approve=approve, client=deps.client)
        except ValueError as exc:
            # Unknown id, or a heal that is not sitting at the review gate. This is a
            # client error, not a server fault — and it must stay JSON so the SPA can
            # surface it through the same taxonomy path as every other failure.
            return jsonify({"error": str(exc), "code": "not_reviewable",
                            "category": FailureCategory.APPLICATION_ERROR,
                            "heal_event_id": heal_id}), 409
        if approve:
            run_source(heal["source_id"], deps)  # verify the human-approved template immediately
        return jsonify(_heal_json(db.query_one("SELECT * FROM heal_events WHERE id = ?", [heal_id])))

    @app.get("/api/ledger")
    def ledger():
        limit = int(request.args.get("limit", 200))
        rows = db.query("SELECT * FROM audit_events ORDER BY id DESC LIMIT ?", [limit])
        return jsonify([{**r, "refs": db.uj(r["refs"]), "payload": db.uj(r["payload"])} for r in rows])

    @app.get("/api/alerts")
    def alerts_feed():
        rows = db.query("SELECT * FROM alerts ORDER BY id DESC LIMIT 50")
        return jsonify([{**a, "payload": db.uj(a["payload"])} for a in rows])

    @app.get("/api/stats")
    def stats():
        events = db.query("SELECT drift_class, COUNT(*) AS n FROM drift_events GROUP BY drift_class")
        # heal_mttr_seconds is a headline stat — seed.py's demo-history rows (seeded=1) are
        # excluded so it never mixes a fabricated constant with a real measurement (GAP-18).
        heal_rows = db.query(
            "SELECT mttr_seconds FROM heal_events WHERE mttr_seconds IS NOT NULL AND seeded = 0")
        heal_all = db.query("SELECT status, COUNT(*) AS n FROM heal_events GROUP BY status")
        runs = db.query_one("SELECT COUNT(*) AS n, COALESCE(SUM(credits_spent),0) AS credits FROM runs")
        verified = db.query_one(
            "SELECT COUNT(*) AS n FROM heal_events WHERE status = 'approved'") or {"n": 0}
        total_heals = sum(h["n"] for h in heal_all) or 1
        mttrs = [h["mttr_seconds"] for h in heal_rows]
        return jsonify({
            "sources": (db.query_one("SELECT COUNT(*) AS n FROM sources") or {}).get("n", 0),
            "runs": runs["n"], "credits_spent": runs["credits"],
            "events_by_class": {CLASS_LABELS[e["drift_class"]]: e["n"] for e in events},
            "heal_mttr_seconds": round(statistics.mean(mttrs), 1) if mttrs else None,
            "heal_mttr_measured_count": len(mttrs),
            "heal_verification_pass_rate": round(verified["n"] / total_heals, 3),
            "quarantined_snapshots": (db.query_one(
                "SELECT COUNT(*) AS n FROM snapshots WHERE quarantined = 1") or {}).get("n", 0),
        })

    @app.post("/api/run/<source_id>")
    def run_now(source_id: str):
        return jsonify(run_source(source_id, deps))

    @app.post("/api/run-all")
    def run_all():
        return jsonify([run_source(s["id"], deps) for s in db.query("SELECT id FROM sources")])

    @app.post("/api/onboard")
    def onboard():
        """Onboard a new source: NL description -> Scraper Studio create -> first run."""
        body = request.get_json(force=True)
        url, description, name = body.get("url"), body.get("description"), body.get("name")
        source_id = body.get("id") or (name or "source").lower().replace(" ", "-")
        if not (url and description and name):
            return jsonify({"error": "url, description and name are required"}), 400
        if not _valid_source_id(source_id):
            return jsonify({
                "error": "invalid source id",
                "detail": ("a source id must match [a-z0-9][a-z0-9_-]{0,63} — it is used as a "
                           "filesystem path for the contract and as a primary key"),
                "source_id": source_id,
            }), 400
        if not _valid_target_url(url):
            return jsonify({
                "error": "invalid target url",
                "detail": "only public http(s) URLs are accepted",
            }), 400
        if db.query_one("SELECT id FROM sources WHERE id = ?", [source_id]) is not None:
            return jsonify({"error": "a source with this id already exists", "source_id": source_id}), 409
        contract_path = (deps.contracts_dir or FIXTURES_DIR / "contracts") / f"{source_id}.yaml"
        if not contract_path.exists():
            return jsonify({
                "error": "no contract available for this source",
                "detail": (
                    f"onboarding requires a hand-authored semantic contract at {contract_path} "
                    "before the first run can pass; none exists for this source_id yet. Write one "
                    "(copy fixtures/contracts/nimbusai-pricing.yaml as a starting point) and retry — "
                    "see docs/09_AI_ML/Model_Limitations.md#8"
                ),
                "source_id": source_id,
            }), 422
        envelope = deps.client.create_scraper(url, description, name=source_id)
        db.insert("sources", {
            "id": source_id, "name": name, "vertical": body.get("vertical", "custom"),
            "url": url, "description": description,
            "schedule_minutes": int(body.get("schedule_minutes", 60)),
            "status": "active", "created_at": db.now_iso(),
        })
        db.insert("scrapers", {
            "source_id": source_id, "collector_id": envelope.collector_id, "active_version": 1,
            "status": "active", "view_url": envelope.view_url, "created_at": db.now_iso(),
        })
        db.audit("human", "source.onboarded", {"source": source_id},
                 {"collector_id": envelope.collector_id, "ai_flow_steps": envelope.completed_steps})
        summary = run_source(source_id, deps)
        return jsonify({"source_id": source_id, "collector_id": envelope.collector_id,
                        "view_url": envelope.view_url, "ai_flow_steps": envelope.completed_steps,
                        "first_run": summary})

    # -- provenance + error surface ----------------------------------------------

    @app.get("/api/meta")
    def meta():
        """What is actually driving this instance.

        The UI renders `mode` as a badge so a viewer can never mistake the
        deterministic replay world for a live Bright Data session. This route is
        the single source of truth for that claim — see docs/LIVE_VALIDATION.md.
        """
        live = settings.mode == "live"
        return jsonify({
            "mode": settings.mode,
            "live": live,
            "brightdata_cli": resolve_cli() is not None,
            "brightdata_key_configured": bool(settings.brightdata_api_key),
            # Live-mode readiness is a fact about configuration, never a fallback:
            # if this is false in live mode the app raises rather than replaying.
            "live_ready": live and bool(settings.brightdata_api_key) and resolve_cli() is not None,
            "data_source": (
                "Bright Data Scraper Studio (live CLI)" if live
                else "recorded Bright Data envelopes + controlled mirror site (replay)"
            ),
            "auto_approve_threshold": settings.auto_approve_threshold,
            "auto_reject_threshold": settings.auto_reject_threshold,
            "gates": ["schema", "invariants", "semantics", "continuity"],
        })

    @app.errorhandler(BrightDataError)
    def _brightdata_error(exc: BrightDataError):
        """A vendor refusal is reported as a vendor refusal — never as a scraper failure.

        Without this the UI would render Bright Data's 403/503 as "extraction
        broke", which is the exact misattribution the failure taxonomy exists to
        prevent. HTTP 502 (bad gateway) is the honest status: our upstream failed.
        """
        return jsonify({"error": str(exc), **exc.to_dict()}), 502

    @app.errorhandler(ConfigError)
    def _config_error(exc: ConfigError):
        return jsonify({"error": str(exc), "code": exc.code,
                        "category": FailureCategory.APPLICATION_ERROR}), 500

    @app.errorhandler(DriftwatchError)
    def _driftwatch_error(exc: DriftwatchError):
        return jsonify({"error": str(exc), "code": exc.code}), 500

    return app


def _event_json(event: dict | None) -> dict | None:
    if event is None:
        return None
    return {**event, "class_label": CLASS_LABELS.get(event["drift_class"], "?"),
            "field_changes": db.uj(event["field_changes"])}


def _heal_json(heal: dict | None) -> dict | None:
    if heal is None:
        return None
    return {**heal, "preview_payload": db.uj(heal["preview_payload"]),
            "verification": db.uj(heal["verification"])}


def serve(settings: Settings) -> None:
    from .. import seed
    from ..scheduler import start as start_scheduler

    db.configure(settings.db_path)
    seed.seed_all()
    world = WorldState()
    for source_id, variant in seed.CURRENT_VARIANTS.items():
        world.set_variant(source_id, variant)
    app = create_app(settings, world)
    start_scheduler(build_deps(settings, world))
    # Binds 127.0.0.1 unless DW_HOST is set explicitly (e.g. DW_HOST=0.0.0.0 to expose
    # beyond localhost) — see docs/08_Deployment/Deployment_Architecture.md § Networking.
    app.run(host=settings.host, port=settings.port, debug=False)
