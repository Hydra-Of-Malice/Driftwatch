# Live validation log — Bright Data Scraper Studio

Engineering log of the real, credentialed run against Bright Data's API on **2026-08-23**.
Written to be checked, not believed: every row below is a status code and a verbatim vendor
string, and every claim that is *not* live-proven is marked as such.

**Read this before reading any other claim in the repo about live mode.** Where a claim elsewhere
conflicts with this file, this file is the ground truth.

## Environment

| Item | Value |
|---|---|
| Date | 2026-08-23 (Day-0 spike envelopes: 2026-08-22) |
| OS | Windows 11, PowerShell 7 + Git Bash |
| Node | v22.22.2 |
| Python | `py -3.12`. The machine's default `python` is **3.10.11** and cannot run this engine — `datetime.UTC` requires >= 3.11 |
| Bright Data CLI | `@brightdata/cli@0.3.5`, installed globally 2026-08-23 |
| API base | `https://api.brightdata.com` |
| Account | customer id `hl_8b1d3640`, balance **$49.99** (read live with the Admin key — see the experiment below; billing/credits are ruled out as a cause of anything here) |
| Zones present | `cli_unlocker` (`unblocker`), `cli_browser` (`browser_api`) |
| Auth | `BRIGHTDATA_API_KEY` from the environment. **Two** keys exist on this account: the original with `Permissions = User`, and a second issued later with `Permissions = Admin`. Both belong to the same Admin account user; the difference is the token's permission setting alone. Neither key is printed, logged, echoed or committed; `live.py` redacts them out of CLI stderr before any error is raised (`test_api_key_never_appears_in_raised_error`) |

## CLI identity: `brightdata` vs `bdata`

Resolved. They are **the same program**. `@brightdata/cli@0.3.5` ships a two-entry `bin` map in
its `package.json`, both entries pointing at one file:

```json
{"brightdata": "dist/index.js", "bdata": "dist/index.js"}
```

`bdata` is an alias — not a second CLI, not an older CLI, not a different API surface. npm installs
both shims (`brightdata.cmd` and `bdata.cmd` on Windows) side by side.

This matters because the captured failure envelopes in `scripts/spike_out/` contain
`"next_step": "bdata scraper run ..."`. The CLI writes its own suggested next command using the
short alias, which is why `bdata` appears in output that was produced by invoking `brightdata`.
It is not evidence of a second toolchain.

`LiveClient` therefore probes both names, in order, and uses whichever resolves:
`CLI_NAMES = ("brightdata", "bdata")` in `backend/driftwatch_engine/brightdata/live.py`.

## What the CLI actually calls

Read out of `dist/commands/scraper.js` in the installed package, not from the README:

| CLI command | HTTP call |
|---|---|
| `scraper create` step 1 | `POST /dca/collector` — creates the collector with a **stub** template |
| `scraper create` step 2 | `POST /dca/collectors/{id}/automate_template` — the AI Flow trigger |
| (AI Flow poll) | `GET /dca/collectors/{id}/automate_template/progress` |
| `scraper heal` | `POST /dca/collectors/{id}/refactor_template` |
| `scraper approve` | `POST /dca/collectors/{id}/resume_automation_job` |
| `scraper run` | `POST /dca/trigger_immediate` \| `/dca/crawl` \| `/dca/trigger` |
| `discover` | `POST /discover` |

`scraper create` being **two** calls is load-bearing for the diagnosis below: step 1 succeeds and
returns a real `collector_id` even when step 2 is refused. That is why real collector ids exist for
scrapers that were never actually generated.

## Endpoint results (live, this account, both keys)

`User` and `Admin` are the two keys' `Permissions` settings; identical requests were sent with
each. The methodology and what the difference proves are in the next section.

| Operation | Endpoint / path | `User` key | `Admin` key | Verbatim body or result | Verdict |
|---|---|---|---|---|---|
| List zones | `GET /zone/get_active_zones` | **200** | **200** | `[{"name":"cli_unlocker",...},{"name":"cli_browser",...}]` | **WORKS** |
| Budget / balance | `GET /customer/balance` | **403** | **200** | 403: `Your API key lacks the required permissions for this action. You can change your token permissions at https://brightdata.com/cp/setting/users` — 200: `{"balance":49.99,"credit":0,"prepayment":0,"pending_costs":0.01}` | **Finding 1 — token scope, FIXED by the Admin key** |
| Web Unlocker scrape | `POST /request` (zone `cli_unlocker`) | **200** | **200** | Full markdown of a `books.toscrape.com` product page | **WORKS** |
| Collector create (step 1) | `POST /dca/collector` | **200** | **200** | real id `c_mt5og4ec1cp5lb1yjd`, `"template":{"stub":true}` | **WORKS** |
| AI Flow trigger (step 2) | `POST /dca/collectors/{id}/automate_template` | **403** | **403 (unchanged)** | `Automation not allowed` (plain text, not JSON) | **Finding 2 — account feature entitlement** |
| AI Flow progress read | `GET /dca/collectors/{id}/automate_template/progress` | **200** | **200** | `{}` | Reachable, but nothing to report — no job was ever created |
| Heal / self-heal | `POST /dca/collectors/{id}/refactor_template` | **503** | **503 (unchanged)** | `Self healing tool is temporarily disabled` (plain text, not JSON) | **Finding 3 — server-side global disable** |
| Scraper run (stub collector) | CLI `scraper run` | **403** | **403** | `{"error":"Collector does not have a template"}` | Downstream symptom of Finding 2 |
| **Discover** | CLI `discover` → `POST /discover` | **200** | **200** | Real AI ranking, 17s wall clock: 5 queries → 18 candidates → 3 reranked | **WORKS** |

Five things are live-proven to work end to end on this account: **zone listing**, **Web Unlocker
fetch**, **collector creation**, **`discover`**, and — with the Admin key — **balance reporting**.
Everything gated behind Scraper Studio's AI automation is refused, for two unrelated reasons,
neither of which is the token.

## Real collector IDs created

All are genuine, vendor-issued `c_*` ids, visible in the Bright Data control panel at
`https://brightdata.com/cp/scrapers/<id>`. None holds a generated template, because in every case
`automate_template` was refused after the collector row already existed.

| Collector id | Created | Status | Notes |
|---|---|---|---|
| `c_mt3vr49h1qtwyctl1g` | 2026-08-22 | `ai_trigger_failed` | Day-0 spike — `scripts/spike_out/create.json` |
| `c_msqexhu61uaxbv00x4` | 2026-08-22 | `heal_trigger_failed` → `resume_failed` | Target of the heal and approve attempts — `scripts/spike_out/heal.json`, `approve.json` |
| `c_mt5moeyi28i2av0bzd` | 2026-08-23 | `ai_trigger_failed` | Repeat attempt, identical refusal |
| `c_mt5og4ec1cp5lb1yjd` | 2026-08-23 | created, template `{"stub": true}` | Diagnostic: raw `POST /dca/collector` only, AI step deliberately not attempted — this is what isolated the two-call structure. Later re-tested with the Admin key: still 403 on `automate_template` |
| `c_mt5p4epqlomcj1iim` | 2026-08-23 | `ai_trigger_failed` | **Admin-key experiment**, raw API. Fresh collector, so a stale-collector explanation is ruled out — still 403 |
| `c_mt5p5irb2aw2fyjfgu` | 2026-08-23 | `ai_trigger_failed` | **Admin-key experiment, created by Driftwatch's own `LiveClient.create_scraper`** against real Bright Data — see the live-proof section below |

### Verbatim failure envelopes

`scripts/spike_out/create.json`:

```json
{"collector_id":"c_mt3vr49h1qtwyctl1g","name":"driftwatch-spike","status":"ai_trigger_failed","completed_steps":[],"view_url":"https://brightdata.com/cp/scrapers/c_mt3vr49h1qtwyctl1g","created_at":"2026-08-22T04:30:29.717Z","error":"Automation not allowed"}
```

`scripts/spike_out/heal.json`:

```json
{"collector_id":"c_msqexhu61uaxbv00x4","status":"heal_trigger_failed","completed_steps":[],"prompt":"...","view_url":"...","next_step":"bdata scraper run ...","error":"Self healing tool is temporarily disabled"}
```

`scripts/spike_out/approve.json`:

```json
{"collector_id":"c_msqexhu61uaxbv00x4","status":"resume_failed","completed_steps":[],"prompt":"","error":"Automation not found"}
```

The `approve` failure is not independent: `resume_automation_job` has nothing to resume because
the heal that would have created the automation job never started. It is a cascade of Finding 3.

## Three distinct findings — do not conflate them

The common misreading of this log is "the Bright Data integration is blocked." It is blocked by
**three different things**, at three different layers, with different owners. One of them has been
fixed. Neither of the other two is fixable from this side, and — this is the correction that the
controlled experiment forced — **neither of them is a token problem**.

### The controlled experiment (2026-08-23, later the same day)

An earlier revision of this document recorded the AI-Flow 403 as *probably* an under-scoped API
token, explicitly labelled an inference rather than a proof. That inference has now been **tested
and disproven**. The method: the account holder issued a **second** API key with
`Permissions = Admin` (the original was `Permissions = User`; both keys belong to the same Admin
account user). The identical requests were then sent with each key, holding everything else
constant — same account, same collectors, same bodies, same minutes.

| Endpoint | `User`-scoped key | `Admin`-scoped key | What it proves |
|---|---|---|---|
| `GET /customer/balance` | 403 `...lacks the required permissions...` | **200** `{"balance":49.99,"credit":0,"prepayment":0,"pending_costs":0.01}` | Token scope **was** the cause here — and the Admin key really is more privileged |
| `POST /dca/collector` | 200 | 200 | Unaffected by scope |
| `POST /dca/collectors/{id}/automate_template` | 403 `Automation not allowed` | **403 `Automation not allowed` — UNCHANGED** | **Not** token scope |
| `POST /dca/collectors/{id}/refactor_template` | 503 `Self healing tool is temporarily disabled` | **503 — UNCHANGED** | **Not** token scope |
| `GET /zone/get_active_zones` | 200 | 200 | Unaffected by scope |

The `automate_template` call was retried under the Admin key against **three** collectors — a
freshly created one (`c_mt5p4epqlomcj1iim`) and both pre-existing ones (`c_mt5og4ec1cp5lb1yjd`,
`c_mt3vr49h1qtwyctl1g`). All three returned 403. A stale-collector or bad-collector-state
explanation is therefore ruled out as well.

**The Admin token was necessary but not sufficient.** It is a real, demonstrated privilege
increase — it turned a 403 into a 200 on `/customer/balance` in the same test run — and it changed
nothing about AI Flow. Account balance is **$49.99** with `pending_costs` of $0.01, so credits and
billing are ruled out too.

### Why this was not obvious, and why it matters methodologically

Bright Data returns **403 for both** `/customer/balance` and `automate_template`, on the same
account, minutes apart. For the first it supplies a helpful body naming token permissions and
linking the token settings page; for the second it supplies the bare string `Automation not
allowed` and no cause at all. Read together — and the vendor's own remediation text invites you to
read them together — they look like one problem with one fix: re-issue the token.

They are two problems. **Only varying the token while holding the request constant separates
them.** The vendor's own error text was, in effect, pointing at the wrong remedy for one of the two
cases, and no amount of reading the message more carefully would have revealed that; it took an
experiment.

This is precisely the argument for the failure taxonomy below. A system that trusts a vendor's
remediation prose will confidently tell an operator to go re-issue a token that is already
correct — a wrong instruction delivered with full confidence, which is worse than no instruction.
Driftwatch classifies on the *observed* behaviour of the endpoint, and the classification is
revised when an experiment says so; `errors.py` was corrected the same day (see the fix log).

### Finding 1 — `/customer/balance` 403: token scope. **FIXED**

`Your API key lacks the required permissions for this action.` The vendor named the cause, the
cause was real, and issuing an Admin-permission key fixed it: the endpoint now returns 200 with
the live balance. This finding is closed, and it is what makes the experiment interpretable —
without it, an unchanged 403 on `automate_template` could have been dismissed as "the new key
didn't take."

Classified as `VENDOR_PERMISSION_ERROR`, hint: re-issue the token with the required permissions.

### Finding 2 — `automate_template` 403 `Automation not allowed`: **account feature entitlement**

**Shape: entitlement, not permission.** HTTP 403 is Forbidden — the credential was accepted, the
action was not. But the experiment above establishes *which* credential property is being refused,
and it is not the token's permission set. Scraper Studio AI automation is withheld at the
**account** level on customer `hl_8b1d3640`.

Consequences, stated plainly:

- **No token change lifts this.** Re-issuing, re-scoping, or upgrading the API token has been
  tested and does not help. Any documentation that tells an operator to do so is wrong.
- It is not credits or billing — the balance is $49.99 and `/customer/balance` answers 200.
- It is not collector state — three collectors, one of them seconds old, all 403.
- The remedy is Bright Data enabling AI automation on the account. That is a vendor/account action,
  not an engineering one.
- The collector itself is still created and usable (`POST /dca/collector` returns 200 throughout).
  Only the *generation* step is withheld — which is why real `c_*` ids exist for scrapers that hold
  nothing but a stub template.

Classified as `VENDOR_PERMISSION_ERROR` by `classify_vendor_error` in
`backend/driftwatch_engine/errors.py`. The category is right — the vendor refused a permitted-looking
action — and the **remediation hint was corrected** on 2026-08-23 to state the account-entitlement
finding instead of advising an Admin token.

### Finding 3 — `refactor_template` → HTTP 503 `Self healing tool is temporarily disabled`

**Shape: outage.** Categorically different from both of the above, and the most consequential of
the three.

HTTP **503 Service Unavailable** is not an authorization response. The vendor's own message says
what it is: the self-healing tool is *temporarily disabled*. This is a **server-side, global,
vendor-controlled feature disable**. Concretely:

- Not a credential problem — the same key works for `/dca/collector`, `/discover`, zones and Web Unlocker.
- Not a token-scope problem — **tested directly**: the Admin-permission key returns the identical 503. An under-scoped token yields 403 on this account, not 503, as Findings 1 and 2 both show.
- Not a plan or credit problem — those refuse with 402/403-class responses and a billing message; the balance is $49.99.
- Not an account setting — there is no control-panel toggle that re-enables a service the vendor has switched off.
- Not a client-code problem — no change to `LiveClient`, the CLI, the request body, or the retry policy can make a disabled endpoint serve.

**Therefore: the live self-heal round trip (`heal` → `awaiting_approval` → `preview_result` →
`approve` → verified re-run) is not demonstrable for as long as Bright Data has this endpoint
disabled.** No engineering on this side changes that. Retrying later is the only remediation, and
it is the vendor's call, not ours.

**What Driftwatch does about it — and what it deliberately does not do.** In live mode Driftwatch
does **not** fall back to the replay client, does **not** synthesize a heal preview, and does
**not** manufacture a success. `api/app.py` selects the client once, at construction:
`LiveClient(...) if settings.mode == "live" else ReplayClient(world)`. There is no silent
live → replay downgrade anywhere in the codebase. In live mode the real 503 propagates, is
classified as `VENDOR_UNAVAILABLE`, and is surfaced as exactly that. The healing story is
demonstrated in **replay mode**, against recorded envelope shapes and a controlled mirror site, and
is labelled replay everywhere it is shown.

### Why the taxonomy is the point

All three findings arrive at the seam as "the CLI exited non-zero with some text." Without
classification, the obvious thing to do is report that as a failed scrape — and that would be a
**lie in the operator's dashboard**. It would say a scraper broke when in fact the vendor turned a
feature off, or withheld a feature from the account, or a token is missing a permission checkbox.
Those four conditions demand four different human responses (wait; ask the vendor to enable the
feature; fix the token; fix the scraper), and collapsing them into one red banner destroys the only
information the operator actually needs.

Note the second-order lesson from the experiment: it is not enough to classify on the vendor's own
*words*, because the vendor's words for Finding 2 named the wrong remedy. Categories here are
assigned to observed endpoint behaviour and revised when evidence contradicts them — which is what
happened to the `automation not allowed` hint on 2026-08-23.

`FailureCategory` + `VENDOR_ERROR_SIGNATURES` in `backend/driftwatch_engine/errors.py` keep them
apart, matching the vendor's observed message strings first and falling back to HTTP status class:

| Live vendor message | HTTP | Category | What the operator is told to do |
|---|---|---|---|
| `Automation not allowed` | 403 | `VENDOR_PERMISSION_ERROR` | **Corrected 2026-08-23:** account-level feature entitlement, proven by controlled experiment; re-issuing the token will not help — Bright Data must enable AI automation on the account |
| `Self healing tool is temporarily disabled` | 503 | `VENDOR_UNAVAILABLE` | Vendor-side; not fixable here — retry when re-enabled |
| `...lacks the required permissions...` | 403 | `VENDOR_PERMISSION_ERROR` | Token is under-scoped for this endpoint |
| `Collector does not have a template` | 403 | `CLI_COMPATIBILITY` | Downstream symptom of a blocked AI trigger — not a scrape failure |
| `Automation not found` | — | `VENDOR_PERMISSION_ERROR` | Nothing to resume; the heal never started |
| `Cannot run more than N...` | 429 | `VENDOR_RATE_LIMIT` | AI-Flow concurrency cap — serialise and back off |
| (scraper ran, returned zero records) | 200 | `SCRAPER_FAILURE` | **This** is "the scraper broke" — and only this |

The last row is the whole argument in one line: `SCRAPER_FAILURE` is reserved for the case where
our scraper genuinely ran and genuinely failed. A vendor 503 never wears that label.

## Live proof of the seam itself

The two artifacts below are the strongest evidence this project has, because they are not curl
transcripts — they are **Driftwatch's own `LiveClient` talking to real Bright Data with a real
key**, on 2026-08-23, with the Admin token.

### 1. A real vendor refusal, correctly classified — `LiveClient.create_scraper`

```
category      = VENDOR_PERMISSION_ERROR
operation     = scraper.create
status        = 403
message       = Automation not allowed
collector     = c_mt5p5irb2aw2fyjfgu
vendor_status = ai_trigger_failed
```

Read what that record does and does not contain:

| Property | Evidence in the record |
|---|---|
| It reached the real vendor | `c_mt5p5irb2aw2fyjfgu` is a real, vendor-issued collector id, visible in the control panel |
| It preserved the vendor's own words | `message = Automation not allowed`, verbatim, unparaphrased |
| It preserved the vendor's transport status | `status = 403` |
| It preserved the vendor's envelope status | `vendor_status = ai_trigger_failed` |
| It classified rather than guessed | `category = VENDOR_PERMISSION_ERROR` — **not** `SCRAPER_FAILURE` |
| It knew which call failed | `operation = scraper.create` |
| It did **not** fabricate success | The call raised; no green run, no synthetic payload |
| It did **not** fall back to replay | No live → replay downgrade exists in the codebase |
| It did **not** leak the key | The key appears nowhere in the error, by construction and by test |

Every one of the fix-log bugs below would have destroyed one of those properties. Bug #4 would have
reported a success. Bug #5 would have let `ai_trigger_failed` pass as healthy. Bug #3 would have
thrown away `Automation not allowed` and left a bare exit code. Bug #6 would have labelled a vendor
entitlement refusal a broken scraper. Bug #10 would have produced an empty `VENDOR_BAD_RESPONSE`
with no vendor message at all. This single record is the regression test for all of them, run
against the real thing.

### 2. A real vendor success through the same seam — `LiveClient.discover`

`LiveClient.discover` ran live and returned **5 real AI-ranked candidates**, normalized at the seam
to `{url, title, score, reason}` from the vendor's `{link, title, relevance_score, description}`
(see the envelope-drift section). Same client, same key, same process — one vendor path permitted,
one refused, both handled correctly and differently.

Taken together these two runs demonstrate the property the whole exercise was for: **the seam
reports what actually happened.** It does not upgrade a refusal into a success, and it does not
downgrade a vendor policy decision into a scraper bug.

## Root-cause / fix log

Bugs found by attempting the live path for real — several of them invisible to mocks and only
reachable by running against the real CLI and the real API. All are fixed in
`backend/driftwatch_engine/`; the suite is green — `cd backend && py -3.12 -m unittest discover -s
tests` → **40 tests, OK** (23 pre-existing replay/E2E plus 17 live-client contract tests in
`tests/test_live_client.py`).

| # | Symptom | Root cause | Layer fixed | How verified |
|---|---|---|---|---|
| 1 | Live mode could not start at all on Windows; on Linux the CLI behaved erratically | `LiveClient._env()` **replaced** the child environment with `{"BRIGHTDATA_API_KEY": ..., "PATH": "/usr/local/bin:/usr/bin:/bin"}` — a hardcoded POSIX PATH. On Windows that PATH locates nothing; on every platform it starved Node of `SystemRoot`, `APPDATA`, `TEMP` and proxy vars | `brightdata/live.py` — `_env()` now copies `os.environ` and *adds* the key | `test_api_key_is_injected_without_wiping_the_environment` |
| 2 | `FileNotFoundError` launching the CLI on Windows even with the CLI on PATH | `subprocess.run` was given the bare name `"brightdata"`; the npm shim is `brightdata.cmd`, and `CreateProcess` will not resolve a `.cmd` from a bare name | `brightdata/live.py` — `resolve_cli()` returns the `shutil.which()`-resolved **absolute** path, probing `brightdata` then `bdata` | `test_cli_invoked_by_resolved_absolute_path`, `test_missing_cli_is_a_config_error` |
| 3 | The vendor's actual message was lost; failures surfaced as a bare non-zero exit | `_cli` raised on a non-zero exit code *before* parsing stdout, discarding the JSON error envelope — the single most informative artifact the vendor returns | `brightdata/live.py` — stdout is parsed first; the envelope's own `error`/`status` wins, with a stderr `Error:`/`Status:` scrape as fallback | `test_non_json_stderr_failure_recovers_vendor_message_and_status`, `test_vendor_message_extraction` |
| 4 | A run that extracted **nothing** was reported as a healthy run | `run_scraper` hardcoded `status="done"` on every response — it manufactured success out of HTTP 200 | `brightdata/live.py` — an empty / record-less payload now raises `BrightDataError(category=SCRAPER_FAILURE)` | `test_empty_run_is_a_scraper_failure_not_a_green_run`, `test_successful_run_returns_payload` |
| 5 | `ai_trigger_failed`, `heal_trigger_failed`, `resume_failed` envelopes flowed downstream as if healthy | `create_scraper` / `heal_scraper` / `approve` never inspected the envelope's `status` field — the CLI exits 0 while reporting a failed status *inside* the JSON | `brightdata/live.py` — `_assert_ok()` on every envelope; `FAILED_STATUSES` in `brightdata/envelopes.py` | `test_create_refusal_raises_and_is_classified`, `test_approve_refusal_raises` |
| 6 | A vendor 403/503 would have rendered to the operator as "your scraper broke" | No vendor error taxonomy existed at all | `errors.py` — added `FailureCategory`, `VENDOR_ERROR_SIGNATURES`, `classify_vendor_error`; `BrightDataError` now carries `category`, `hint`, `status` | `test_heal_disabled_is_vendor_unavailable_not_scraper_failure`, `test_timeout_is_classified`, `test_malformed_json_is_classified` |
| 7 | No way to reconstruct what was actually called during a failed live attempt | No structured operation logging | `obs.py` — per-op structured logging with credential scrubbing | `test_api_key_never_appears_in_raised_error` |
| 8 | Envelope models did not match CLI 0.3.5 | Models were written from the README, not from live output; real envelopes carry `completed_steps` and the `*_failed` statuses | `brightdata/envelopes.py` | Models validated against the verbatim `scripts/spike_out/*.json` envelopes quoted above |
| 9 | Discover results arrived with unusable field names (see next section) | Live `/discover` returns `link`/`relevance_score`/`description`; the rest of the engine speaks `url`/`score`/`reason` | `brightdata/live.py` — `_normalize_candidate` at the seam | `test_discover_normalizes_live_field_names`, `test_normalize_candidate_accepts_both_vocabularies` |
| 10 | **Every** live call failed as `VENDOR_BAD_RESPONSE` with empty stdout — no envelope, no vendor message, nothing to classify | `subprocess.run(text=True)` decodes with the **OS locale codec**. On Windows that is cp1252; the CLI emits UTF-8 (box-drawing and spinner characters in its output), the decode failed, and *all* stdout was silently lost. Invisible to mocks — a `MagicMock` returns whatever `str` the test supplies, so no unit test could ever see it. Only running against the real CLI exposed it | `brightdata/live.py` — `encoding="utf-8", errors="replace"` on the `subprocess.run` call | `test_subprocess_decodes_as_utf8` (asserts the kwarg explicitly, so the regression cannot come back) |
| 11 | Operators were told to fix a token that was already correct | The `automation not allowed` remediation hint in `errors.py` advised issuing an Admin-permission token — a reasonable inference from the vendor's *other* 403, and disproven by the controlled experiment above | `errors.py` — hint rewritten to state the account-level entitlement finding, dated and attributed to the experiment; the `VENDOR_PERMISSION_ERROR` category itself was already correct and is unchanged | The experiment itself: Admin key, three collectors, still 403 |

### Documentation that was wrong about its own code

Recorded because a judge auditing this repo will hit the contradiction. Before this validation
pass, `docs/02_Requirements/SRS.md` marked **CMP-002** ("the system shall behave identically on
Windows and Linux") as **VALIDATED**, with the note *"Platform-dependent path bug fixed."* That
referred to a different, genuinely fixed path bug in `impact/scanner.py`. Meanwhile bug #1 above —
the hardcoded POSIX `PATH` in `LiveClient` — was still in the code and made live mode impossible
on Windows, the maintainer's own platform. `docs/06_Security/Risk_Register.md` **R-20** had it
right and kept it **OPEN**, quoting the exact broken line, and
`docs/06_Security/Security_Architecture.md` reproduced that line verbatim. Two docs in the same
repo disagreed, and the one claiming success was the wrong one. The code is now actually fixed
(bug #1); claim and code agree for the first time.

## Envelope drift: `discover` field names

Real, live-verified drift between the vocabulary the engine expected and what `POST /discover`
actually returns on CLI 0.3.5. Verbatim live envelope (2026-08-23, trimmed to one result for
length; the run returned 3 reranked results):

```json
{"status":"done","duration_seconds":17,"timestamp":"...","counts":{"queries":5,"candidate_results":18,"raw_results":3,"reranked":3},
 "results":[{"link":"https://www.usenimbus.com/pricing/","title":"Pricing - Nimbus","description":"...","relevance_score":0.60546875}]}
```

| Live field | Driftwatch field | Note |
|---|---|---|
| `link` | `url` | |
| `relevance_score` | `score` | float, 0–1 |
| `description` | `reason` | the ranker's justification text |
| `title` | `title` | unchanged |

Normalized in exactly one place — `_normalize_candidate` in
`backend/driftwatch_engine/brightdata/live.py` — which accepts **either** vocabulary
(`raw.get("url") or raw.get("link", "")`), so it survives the vendor renaming these back. Nothing
above the seam knows the live names exist. This is the one place where the day's work produced a
concrete, verified schema drift against the vendor, which is pointedly the exact class of problem
Driftwatch is built to detect.

## Reproduction

Everything below is runnable by a judge with their **own** Bright Data key. Set it first; no
command here prints it.

```powershell
$env:BRIGHTDATA_API_KEY = "<your key>"   # never commit this
```

### 1. Zones — expect 200

```powershell
curl -s -w "HTTP %{http_code}" -H "Authorization: Bearer $env:BRIGHTDATA_API_KEY" `
  https://api.brightdata.com/zone/get_active_zones
```

### 2. Balance — expect 403 with the token-scope message

```powershell
curl -s -w "HTTP %{http_code}" -H "Authorization: Bearer $env:BRIGHTDATA_API_KEY" `
  https://api.brightdata.com/customer/balance
```

### 3. Web Unlocker fetch — expect 200 and page content

```powershell
curl -s -w "HTTP %{http_code}" -X POST https://api.brightdata.com/request `
  -H "Authorization: Bearer $env:BRIGHTDATA_API_KEY" -H "Content-Type: application/json" `
  -d '{\"zone\":\"cli_unlocker\",\"url\":\"https://books.toscrape.com/\",\"format\":\"raw\",\"data_format\":\"markdown\"}'
```

Substitute your own `unblocker`-type zone name for `cli_unlocker`.

### 4. Collector create, step 1 only — expect 200, a real `c_*` id, and a stub template

```powershell
curl -s -w "HTTP %{http_code}" -X POST https://api.brightdata.com/dca/collector `
  -H "Authorization: Bearer $env:BRIGHTDATA_API_KEY" -H "Content-Type: application/json" `
  -d '{\"name\":\"judge-repro\"}'
```

### 5. Finding 2 — AI Flow trigger. Expect **403 `Automation not allowed`**

```powershell
$cid = "<collector id from step 4>"
curl -s -w "HTTP %{http_code}" -X POST "https://api.brightdata.com/dca/collectors/$cid/automate_template" `
  -H "Authorization: Bearer $env:BRIGHTDATA_API_KEY" -H "Content-Type: application/json" `
  -d '{\"url\":\"https://books.toscrape.com/\",\"prompt\":\"extract the book title and price\"}'
```

### 5b. Reproduce the controlled experiment — the step that separates Findings 1 and 2

This is the part worth reproducing, because it is what corrected the diagnosis. Issue a **second**
API key at `https://brightdata.com/cp/setting/users` with `Permissions = Admin`, then run steps 2
and 5 with **each** key, changing nothing else:

```powershell
$env:BRIGHTDATA_API_KEY = "<your User-permission key>"
# ...run step 2 (balance) and step 5 (automate_template)...
$env:BRIGHTDATA_API_KEY = "<your Admin-permission key>"
# ...run the identical step 2 and step 5 again...
```

Expected on this account: balance flips **403 → 200** (the Admin key is genuinely more privileged
and the change definitely took effect), while `automate_template` stays **403 → 403**. That pair of
outcomes is the proof that the AI-Flow refusal is an account entitlement and not a token scope.
Repeat step 5 against a freshly created collector too, to rule out collector state.

If `automate_template` returns 2xx for you on **either** key, your account has Scraper Studio AI
automation entitled and this one is not entitled — which would confirm the account-entitlement
finding from the other direction, and is the single most useful piece of feedback this log can
receive.

### 6. Finding 3 — self-heal. Expect **503 `Self healing tool is temporarily disabled`**

```powershell
curl -s -w "HTTP %{http_code}" -X POST "https://api.brightdata.com/dca/collectors/$cid/refactor_template" `
  -H "Authorization: Bearer $env:BRIGHTDATA_API_KEY" -H "Content-Type: application/json" `
  -d '{\"prompt\":\"price is returned as a string with a currency symbol; return a plain number\"}'
```

This is the one to run if you only run one. A 503 here, from *your* account on *your* key, is the
proof that Finding 3 is global and vendor-side rather than anything about this project's
credentials. It also returns 503 under the Admin key here, so a privileged token is not the answer.

### 7. The CLI path — same results, one layer up

```powershell
npm i -g "@brightdata/cli"          # 0.3.5 at time of writing
brightdata --version
node -e "console.log(JSON.stringify(require('@brightdata/cli/package.json').bin))"   # proves the bdata alias

brightdata discover "AI API pricing page" --intent "find current pricing pages" --num-results 5 --json

brightdata scraper create "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html" `
  "Extract the book title, price as a number, availability text as unit_context, and star rating" `
  --name judge-repro --json

brightdata scraper heal "<collector id>" "return price as a plain number" --url "<url>" --json
```

Expected: `discover` returns 200 with real ranked results. `scraper create` returns an envelope
with `"status":"ai_trigger_failed"` and `"error":"Automation not allowed"`. `scraper heal` returns
`"status":"heal_trigger_failed"` and `"error":"Self healing tool is temporarily disabled"`.

The whole day-0 sequence is scripted in `scripts/day0_spike.ps1`, which writes every raw envelope
to `scripts/spike_out/`.

### 8. Driftwatch's own handling of these failures

```powershell
cd backend
py -3.12 -m unittest discover -s tests        # 40 tests, OK
py -3.12 -m unittest tests.test_live_client -v
```

`tests/test_live_client.py` asserts the classification of the exact live strings above — including
that a 503 self-heal refusal is `VENDOR_UNAVAILABLE` and **not** `SCRAPER_FAILURE`, and that the
CLI subprocess is decoded as UTF-8 rather than the OS locale codec (bug #10).

## Current status

**Live-proven to work**, on this account, 2026-08-23:
`GET /zone/get_active_zones` (200) · Web Unlocker fetch via `POST /request` (200, real page
content) · `POST /dca/collector` (200, six real vendor-issued `c_*` collector ids) ·
`GET /customer/balance` (200 under the Admin key, balance $49.99) · `discover` (200, real AI
ranking — 5 queries → 18 candidates → 3 reranked in 17s, which also exposed a genuine field-name
drift, now normalized at the seam).

**Live-proven through Driftwatch's own client** (not curl): `LiveClient.discover` returned 5 real
AI-ranked candidates normalized to `{url,title,score,reason}`, and `LiveClient.create_scraper`
surfaced a real vendor refusal as
`VENDOR_PERMISSION_ERROR / scraper.create / 403 / "Automation not allowed" / c_mt5p5irb2aw2fyjfgu /
ai_trigger_failed` — classified, vendor's own words intact, real collector id intact, no fabricated
success, no replay fallback.

**Resolved:**

| Finding | Was | Now |
|---|---|---|
| `/customer/balance` 403 | Token scope | **FIXED** — Admin-permission key returns 200 |

**Blocked, and by what:**

| Capability | Blocked by | Owner | Fixable here? |
|---|---|---|---|
| Scraper Studio AI generation (`automate_template`) | **403 `Automation not allowed`** — **account-level feature entitlement**, proven by controlled experiment (Admin key changes nothing; three collectors incl. a fresh one; balance $49.99 rules out billing) | Bright Data — must enable AI automation on account `hl_8b1d3640` | **No.** Token scope is tested and disproven; no client-side change helps |
| Live self-heal round trip (`refactor_template`) | **503 `Self healing tool is temporarily disabled`** — server-side global feature disable, identical under both keys | Bright Data, service-side | **No.** Not by any token, plan, account setting, or code change |
| Live `scraper run` returning records | Cascade of the AI-Flow entitlement — the collectors exist but hold stub templates, so runs return `Collector does not have a template` | Follows the entitlement | Follows the entitlement |

**What is therefore honest to claim.** The Bright Data seam is live-exercised and correct on every
path the vendor permits: real collectors created, real `discover` results ranked and normalized,
real refusals classified with the vendor's own words preserved. Driftwatch's break → diagnose →
heal → verify → approve loop is demonstrated in **replay mode**, against recorded envelope shapes
and a controlled mirror site, and is labelled replay wherever it is shown. It is **not**
demonstrated live, because the two vendor capabilities it depends on are withheld — one from this
account, one from everybody. Live mode does not paper over either: there is no live → replay
fallback, the real vendor errors propagate, and they are classified `VENDOR_PERMISSION_ERROR` and
`VENDOR_UNAVAILABLE` rather than dressed up as scraper failures or as successes.

*Last updated 2026-08-23, after the Admin-token experiment. The token-scope hypothesis recorded in
the previous revision of this file has been tested and disproven; that correction is preserved
above rather than quietly deleted, because how the diagnosis changed is itself evidence. If Bright
Data entitles AI automation on this account, or re-enables the self-heal endpoint, this is the file
to update first.*
