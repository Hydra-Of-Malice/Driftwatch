# Security Architecture

[← Documentation index](../README.md)

---

> **Summary for a reviewer in a hurry.** As of 2026-08-22, DriftWatch has an **opt-in** bearer-token authentication gate (off unless `DW_API_TOKEN` is set) and binds `127.0.0.1` by default (was `0.0.0.0`). It still has **no authorization/RBAC, no rate limiting, no CSRF protection, and no security headers**. In its default, out-of-the-box configuration it remains safe to run on a trusted localhost for a demo and unsafe to expose anywhere else — the difference from before is that the *capability* to change that now exists and is one environment variable away, not zero. One public deployment (the Render replay demo) runs deliberately without that gate for reasons scoped and justified below — see [The public Render demo is a documented exception](#the-public-render-demo-is-a-documented-exception-2026-08-23). Two claims in this document were corrected on 2026-08-23: the subprocess environment description in C2, which had it exactly backwards, and the deployment section, which did not mention a networked deployment at all.

The controls that *do* exist are real and worth stating precisely, because overstating them would be worse than having none.

---

## Control inventory

| Control | Status | Evidence |
|---|---|---|
| Authentication | **PARTIALLY IMPLEMENTED** | `api/app.py :: _require_auth`, a `before_request` bearer-token check allowlisting `/`, `/assets/*`, `/mirror/*` — active only when `DW_API_TOKEN` is set; unset by default |
| Authorization / RBAC | **NOT IMPLEMENTED** | No roles, no permission checks |
| Session management | **NOT IMPLEMENTED** | No sessions, no cookies |
| Token management | **NOT IMPLEMENTED** | — |
| Password handling | **N/A** | No user accounts |
| TLS | **NOT IMPLEMENTED** | Plain HTTP; no reverse proxy |
| Secrets in environment, not code | **IMPLEMENTED** | `config.py :: Settings.from_env` |
| Secrets excluded from VCS | **VALIDATED** | `.env` gitignored; verified absent from git history |
| Secrets manager | **NOT IMPLEMENTED** | `.env` file on disk |
| SQL parameter binding | **IMPLEMENTED** | `db.py` binds all values |
| Shell-injection avoidance | **IMPLEMENTED** | `subprocess.run` list form, no `shell=True` |
| Subprocess environment isolation | **NOT IMPLEMENTED** (accepted) | Child inherits the full parent env — `brightdata/live.py :: _env`; see C2 |
| Path-traversal protection (assets) | **IMPLEMENTED** | `send_from_directory` |
| Input validation | **PARTIAL** | Variant allowlist and required-field checks only |
| Output encoding (SPA) | **PARTIAL** | `esc()` helper exists; use not systematically verified |
| CSRF protection | **NOT IMPLEMENTED** | — |
| Rate limiting | **NOT IMPLEMENTED** | — |
| Security headers | **NOT IMPLEMENTED** | No CSP, HSTS, X-Frame-Options |
| CORS policy | **NOT CONFIGURED** | Flask default — same-origin |
| Audit trail | **IMPLEMENTED** | `audit_events` |
| Dependency pinning | **PARTIAL** | Floor constraints (`>=`) only, no lockfile |
| Prompt-injection defence | **NOT IMPLEMENTED** | See T-08 |

---

## Controls that genuinely exist

### C1 — SQL parameter binding (IMPLEMENTED)

```python
cur = conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", list(row.values()))
```

Table and column names are f-string interpolated; **values are always bound**. Every call site was inspected: all pass literal table names and dict keys defined in code. No user-controlled data reaches an identifier position.

**Assessment: not exploitable today.** The pattern is nonetheless fragile — a future caller passing user input as a column name would create an injection. **RECOMMENDED:** allowlist table names.

### C2 — Subprocess invocation (IMPLEMENTED; full environment inheritance is an accepted trade-off)

```python
def _env(self) -> dict[str, str]:
    """Real environment + the API key. Never the other way round."""
    env = os.environ.copy()
    env["BRIGHTDATA_API_KEY"] = self.api_key
    return env
```

`backend/driftwatch_engine/brightdata/live.py:99-103`, consumed at `live.py:123` (`env=self._env()`).

**What holds.** List-form argv with no `shell=True`; an absolute binary path resolved once via `shutil.which` rather than a bare name (`live.py:63-74`); an explicit timeout (`live.py:123`); explicit UTF-8 decoding rather than the OS locale codec (`live.py:122`).

**What does not hold — state it plainly.** The child process inherits the **entire parent environment**. Every other secret that happens to be present in the DriftWatch process environment is therefore readable by the Bright Data CLI child and by anything it spawns:

| Variable | Why it is in the parent environment | Visible to the CLI child |
|---|---|---|
| `BRIGHTDATA_API_KEY` | Required by the child; injected deliberately | Yes — intended |
| `DW_API_TOKEN` | API bearer gate (`config.py :: Settings.from_env`) | **Yes — not intended, not prevented** |
| `ANTHROPIC_API_KEY` | Alert prose provider | **Yes — not intended, not prevented** |
| `DW_SLACK_WEBHOOK` | Notifier | **Yes — not intended, not prevented** |

This is a **deliberate, accepted trade-off**, not a minimal-exposure design, and it must not be sold as one. The exposure is broader than the previous text of this section claimed, and the honest framing is: DriftWatch trusts the Bright Data CLI binary with the whole environment of the process that launches it.

> **Correction (2026-08-23) — this section previously asserted the opposite.** It showed `env={"BRIGHTDATA_API_KEY": ..., "PATH": "/usr/local/bin:/usr/bin:/bin"}` and claimed the API key was "the only secret exposed to the child ... better than typical". That code no longer exists, and the claim was hollow even while it did: the "minimal" build could not launch the CLI **at all** on Windows (the npm shim is `brightdata.cmd`, which a hardcoded POSIX `PATH` never finds) and starved Node of `SystemRoot`/`APPDATA` on every platform. It was not a shipping control that traded usability for safety; it was a broken code path that no live run ever survived. A control that cannot execute provides no security.

**Why a wholesale `env=` replacement is not viable.** The child is Node, not a static binary. A curated environment would have to reproduce, correctly and per-platform, at minimum: `SystemRoot` and `SystemDrive` (Windows API and crypto initialisation — Node aborts without them), `APPDATA`/`LOCALAPPDATA` (npm and CLI config/credential cache), `PATH` (the shim re-invokes `node`), `TEMP`/`TMP`, `HOME`/`USERPROFILE`, and `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY` wherever the operator's network requires them. Maintaining that allowlist across Windows, macOS and Linux is a standing correctness liability whose failure mode — as demonstrated — is a live path that silently does not work at all, while the security benefit is bounded by the fact that the CLI is already trusted with the account credential and with network egress. Inheriting is the choice that keeps live mode able to run.

**Mitigations that do hold** (each verified against current source):

| Mitigation | Evidence |
|---|---|
| Credential-shaped text in vendor **stderr** is redacted before it can reach an exception | `live.py:55-60` (`_redact`, matching `bearer <token>` and `api_key`/`token` assignments), applied at `live.py:138` |
| The same redaction covers the **stdout** head carried on a failure | `live.py:174` (`stdout_head=_redact(stdout[:200])`) |
| Structured logs redact by key name as an independent second layer | `obs.py:21` (`_SENSITIVE_KEYS`) and `obs.py:24-28` (`_scrub`), applied at `obs.py:44` |
| A test pins that the API key never appears in a raised error | `backend/tests/test_live_client.py:134` (`test_api_key_never_appears_in_raised_error`) |
| A regression test pins that the environment is *inherited and augmented*, never replaced — so the Windows break cannot silently return | `backend/tests/test_live_client.py:142` (`test_api_key_is_injected_without_wiping_the_environment`) |

Note precisely what these cover: they stop credentials leaking **outward** through DriftWatch's own error and log surfaces. They do nothing to stop the child from **reading** what it inherits.

**Residual risk (accepted, not closed).** A compromised, backdoored or typo-squatted `@brightdata/cli` — or any transitive dependency it loads — sees `DW_API_TOKEN`, `ANTHROPIC_API_KEY` and `DW_SLACK_WEBHOOK` in its own `process.env` and can exfiltrate them over the network egress it already legitimately uses. Redaction cannot mitigate this; it is an inbound-trust problem, not an outbound-logging one. **RECOMMENDED (the real mitigation):** run live mode in a dedicated process, service account or container whose environment holds the Bright Data key plus the platform variables Node requires, and nothing else — process-level isolation, which is enforceable, rather than an in-process env allowlist, which is not maintainable. Until that exists the exposure is accepted and recorded here.

**Unchanged from the previous assessment:** `url`/`description` reach argv unvalidated. Harmless without a shell, but an argument beginning with `-` could be parsed as a flag.

### C3 — Secrets hygiene (VALIDATED)

`.env` is gitignored at repo root; `_load_dotenv` uses `os.environ.setdefault` so the real environment always wins over the file. Verified during this review that no `.env` appears anywhere in git history and no key appears in tracked files.

### C4 — Audit trail (IMPLEMENTED, with a caveat)

Every state transition writes an `audit_events` row with actor, action, refs, payload, timestamp.

> **The caveat is severe, and only mitigated, not closed.** `POST /api/review/<id>` records `decided_by: "human"` for the request — and unless `DW_API_TOKEN` is set, that request is still unauthenticated. The ledger can still attribute an anonymous network call to a person it cannot identify by default. An `_require_auth` gate now exists ([GAP-01](../02_Requirements/Requirements_Gap_Analysis.md#gap-01--no-authentication-on-any-endpoint)), but it is opt-in — the intersection with the product's central integrity claim is only as closed as the operator's configuration.

### C5 — Deterministic core (IMPLEMENTED — a security property)

No pipeline decision depends on a language model; the `Provider` interface returns only `str`. A compromised or manipulated model **cannot** cause a bad template to be approved, because no branch reads model output. This meaningfully bounds the blast radius of T-08.

---

## Data classification

| Data | Sensitivity | At rest | In transit |
|---|---|---|---|
| `BRIGHTDATA_API_KEY` | **High** | Plaintext `.env`, mode 644 | Injected into the CLI child env |
| `ANTHROPIC_API_KEY` | **High** | Plaintext `.env` | HTTPS header; **also inherited by the CLI child** |
| `DW_SLACK_WEBHOOK` | **Medium** | Plaintext `.env` | HTTPS; **also inherited by the CLI child** |
| `DW_API_TOKEN` | **High** | Environment only | Bearer header; **also inherited by the CLI child** |
| Scraped payloads | Low (public pages) | Plaintext SQLite | Plain HTTP to client |
| Audit ledger | Medium (decision record) | Plaintext SQLite | Plain HTTP |
| Connected repo contents | **Potentially high** | Snippets copied into `impact_reports.affected` | Plain HTTP |

> **Under-appreciated exposure.** `scan_repo()` reads a connected repository and stores up to 160 characters of each matching line in `impact_reports.affected`. Those snippets are then served by `GET /api/events/<id>` — **unauthenticated**. Pointing DriftWatch at a private repository publishes matching source lines to anyone who can reach the port. Today `deps.sample_repo` defaults to a fixture directory, so the risk is latent rather than active.
> Evidence: `impact/scanner.py`; `pipeline/runner.py :: Deps.sample_repo`

---

## Deployment security posture

```python
# As of 2026-08-22: settings.host defaults to "127.0.0.1"; DW_HOST=0.0.0.0 opts in explicitly.
app.run(host=settings.host, port=settings.port, debug=False)
```

| Aspect | State |
|---|---|
| Server | Flask development server — **not for production** (Werkzeug docs) |
| Bind address | **`127.0.0.1` by default (fixed 2026-08-22, was hardcoded `0.0.0.0`)** — `DW_HOST=0.0.0.0` opts in explicitly to exposing beyond localhost |
| Debug mode | `False` ✅ — no interactive debugger, no code execution via traceback |
| TLS | None |
| Process supervision | None |
| Container isolation | None |

`debug=False` is the one thing that prevents this from being critical rather than high: Werkzeug's debugger would otherwise offer remote code execution to anyone on the network.

### The public Render demo is a documented exception (2026-08-23)

`render.yaml` deploys a public, anonymous-access demo under gunicorn on `0.0.0.0:$PORT` with **`DW_API_TOKEN` deliberately unset**. `_require_auth` is unchanged and still gates every `/api/*` route whenever the variable *is* set; it is simply not set there.

| Question | Answer for that deployment |
|---|---|
| Why no token? | The only client is the bundled SPA, which issues bare `fetch('/api/...')` calls (`frontend/assets/app.js`). A static page served to the public cannot keep a bearer token secret from its own viewer, so a `generateValue: true` token would 401 every judge and protect nothing — the deployed demo rendered as an empty shell until this was corrected. |
| What protects it instead? | Scope reduction, not access control: `DW_MODE=replay`, so no Bright Data key is present and no credits are reachable; the scraped site is the bundled synthetic mirror; the scanned repo is the fixture directory; the SQLite file is ephemeral free-tier disk, discarded on redeploy. |
| What is actually at risk? | Nothing that has value outside the demo. A visitor can approve a synthetic review item and mutate a throwaway ledger — that is the demonstration, not a breach. |
| When must the token be set? | Any non-public deployment, and **every** live-mode deployment, where the operator drives the API directly rather than through the anonymous SPA. |

See [Threat Model § Residual risk](Threat_Model.md#residual-risk) for the same exception scored against T-01–T-06.

---

## Dependency security

Five runtime dependencies with floor constraints (`flask>=3`, `pydantic>=2`, `jsonschema>=4`, `pyyaml>=6`, `httpx>=0.27`).

| Issue | Detail |
|---|---|
| No lockfile | `pip install -r requirements.txt` resolves differently over time — builds are not reproducible |
| No vulnerability scanning | CI runs `ruff` only; no `pip-audit`, no Dependabot |
| Unbounded upper versions | A breaking major release installs silently |
| `yaml.safe_load` used | ✅ Correct — not `yaml.load` |

**RECOMMENDED:** add a lockfile and `pip-audit` to CI. ~1 hour.

---

## Prioritised remediation

| # | Action | Effort | Addresses |
|---|---|---|---|
| 1 | ~~Bearer-token check in `before_request`, allowlist `/` and `/assets/*`~~ | 1 h | **Done 2026-08-22** — opt-in via `DW_API_TOKEN`; GAP-01, T-03, C4 caveat |
| 2 | ~~Bind `127.0.0.1` by default; require an explicit flag for `0.0.0.0`~~ | 15 m | **Done 2026-08-22** — T-03 |
| 3 | JSON error handler — stop leaking Flask HTML tracebacks | 30 m | Error catalog |
| 4 | Bound `limit`; wrap `get_json` | 30 m | T-06 |
| 5 | Security headers via `after_request` | 30 m | T-07 |
| 6 | Lockfile + `pip-audit` in CI | 1 h | Supply chain |
| 7 | Delimit untrusted values in heal prompts | 2 h | T-08 |
| 8 | Rate-limit `run-all` / `onboard` / `review` | 2 h | T-06 |

Items 1–5 total under three hours and move the security posture from "unsafe on any network" to "defensible on a private one".

---

**Next:** [Threat Model](Threat_Model.md) · [Risk Register](Risk_Register.md)
