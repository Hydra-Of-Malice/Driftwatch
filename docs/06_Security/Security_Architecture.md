# Security Architecture

[← Documentation index](../README.md)

---

> **Summary for a reviewer in a hurry.** As of 2026-08-22, DriftWatch has an **opt-in** bearer-token authentication gate (off unless `DW_API_TOKEN` is set) and binds `127.0.0.1` by default (was `0.0.0.0`). It still has **no authorization/RBAC, no rate limiting, no CSRF protection, and no security headers**. In its default, out-of-the-box configuration it remains safe to run on a trusted localhost for a demo and unsafe to expose anywhere else — the difference from before is that the *capability* to change that now exists and is one environment variable away, not zero.

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

### C2 — Subprocess hardening (IMPLEMENTED)

```python
proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                      env={"BRIGHTDATA_API_KEY": self.api_key, "PATH": "/usr/local/bin:/usr/bin:/bin"})
```

List form (no shell), fixed binary, explicit timeout, and a **minimal environment** — the API key is the only secret exposed to the child, and the rest of the parent environment is not inherited. This is better than typical.

**Two notes:** the hardcoded POSIX `PATH` means `LiveClient` cannot find the CLI on Windows — the live path is Linux/macOS-only as written. And `url`/`description` reach argv unvalidated; harmless without a shell, but an argument beginning with `-` could be parsed as a flag.

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
| `BRIGHTDATA_API_KEY` | **High** | Plaintext `.env`, mode 644 | Passed to subprocess env |
| `ANTHROPIC_API_KEY` | **High** | Plaintext `.env` | HTTPS header |
| `DW_SLACK_WEBHOOK` | **Medium** | Plaintext `.env` | HTTPS |
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
