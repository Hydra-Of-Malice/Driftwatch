# Test Strategy

[← Documentation index](../README.md)

---

## Current state

```
23 tests · 5 files · runtime ~0.4 s · ruff clean · CI green (ubuntu-latest, Python 3.11)
```

Verified during this review on Windows / Python 3.13.11 after two platform fixes: **23/23 pass**.

| File | Tests | Layer |
|---|---|---|
| `test_contracts.py` | 6 | Unit — contract engine |
| `test_drift.py` | 8 | Unit — differ + classifier |
| `test_healing.py` | 4 | Integration — heal loop |
| `test_api.py` | 3 | Integration — HTTP |
| `test_e2e_pipeline.py` | 1 | End-to-end — all five classes |

---

## What makes this suite better than its size suggests

Twenty-three tests is small. Three properties make it meaningful anyway:

**1. Nine of fifteen engine modules are pure functions.** `evaluate`, `diff`, `classify`, `diagnose`, `compose_heal_prompt`, `estimate`, `resolve`, `entity_label`, `required_leaf_coverage` take data and return data. Testing them requires no mocking and no setup, so the tests assert behaviour rather than interaction.

**2. `ReplayClient` is a model, not a mock.** 154 lines simulating the vendor's world: an approval gate, version pinning, outdated templates producing `.broken.json` output, and a sabotage hook for rejection paths. Integration tests therefore exercise the real orchestrator against realistic vendor behaviour.
Evidence: `brightdata/replay.py`

**3. The E2E test walks the whole taxonomy in one pass.** `test_full_lifecycle_across_all_drift_classes` drives baseline → redesign → semantic → material → gone, asserting class, state, quarantine, cost, and affected files at each step. One test covering the entire product thesis.

---

## Test pyramid — actual shape

```
        ╱╲          E2E: 1
       ╱  ╲         Integration: 7
      ╱    ╲        Unit: 15
     ╱______╲       Frontend: 0   ← entire layer missing
```

Backend proportions are healthy. The frontend layer is empty.

---

## Coverage by module

| Module | Lines | Covered? | Notes |
|---|---|---|---|
| `contracts/engine.py` | 179 | **Strong** | All four gates, partial credit, vacuous pass |
| `contracts/paths.py` | 46 | **Indirect** | Via engine tests |
| `drift/classifier.py` | 106 | **Strong** | All six branches |
| `drift/differ.py` | 48 | **Strong** | Reorder, entity paths, add/remove |
| `healing/orchestrator.py` | 146 | **Strong** | All three bands + human path |
| `healing/composer.py` | 38 | **Good** | Length and content |
| `healing/diagnoser.py` | 38 | **Indirect** | |
| `healing/verifier.py` | 20 | **Strong** | Central to two tests |
| `impact/cost.py` | 80 | **Partial** | Material asserted; unit-flip exercised, value unasserted |
| `impact/scanner.py` | 51 | **Partial** | E2E asserts one file |
| `pipeline/runner.py` | 253 | **Good** | All terminal handlers via E2E |
| `api/app.py` | 259 | **Weak** | **3 of 19 routes** |
| `db.py` | 210 | **Indirect** | No direct tests |
| `alerts.py` | 54 | **Partial** | In-app only; Slack branch untested |
| `scheduler.py` | 49 | **None** | Zero coverage |
| `llm/provider.py` | 89 | **Partial** | Heuristic only; Anthropic branch untested |
| `brightdata/live.py` | 72 | **None** | Zero coverage |
| `frontend/assets/*.js` | 838 | **None** | Zero coverage |

**No coverage tooling is configured.** The above is derived by reading tests against modules, not from `coverage.py`. **RECOMMENDED:** add `coverage run -m unittest` to CI so this table becomes a measurement rather than an assessment.

---

## Gaps ranked

### CRITICAL

**1. Audit-ledger integrity (FR-026, FR-028).** The ledger is the product's integrity claim and nothing tests it. Deleting a `db.audit()` call would pass all 23 tests.

```python
def test_every_transition_is_audited(self):
    run_source(self.NIMBUS, self.deps)
    actions = [r["action"] for r in db.query("SELECT action FROM audit_events ORDER BY id")]
    self.assertIn("run.started", actions)
    self.assertIn("run.published", actions)

def test_audit_events_are_never_updated(self):
    ...  # snapshot rows, run a pipeline, assert prior rows byte-identical
```

**2. Reliability handlers (REL-001/002/003).** Three "the system survives failure" claims implemented as try/except and never triggered. Untested exception handlers are a classic source of production surprise — the handler itself can be wrong.

```python
def test_alert_failure_does_not_break_pipeline(self):
    settings = Settings(mode="replay", slack_webhook_url="http://127.0.0.1:1/nope")
    # assert run completes and an alert.slack_failed audit row exists
```

### HIGH

**3. API routes** — 16 untested, including every state-changing one. `review_decide` approves templates into production and has no HTTP-level test.

**4. Frontend** — 838 lines. Minimum viable: load each hash route in a headless browser, assert no console errors and that a known selector renders.

**5. LLM fallback (AI-003)** — `AnthropicProvider` failing over to heuristics is never exercised. A stub returning HTTP 500 would cover it in ten lines.

### MEDIUM

**6. Scheduler** — `_due_sources` has clear boundary conditions (never run, exactly at interval, past interval) and zero tests.

**7. Property-based testing for the differ.** The differ is pure with rich structural inputs — an ideal Hypothesis target. Invariants worth asserting: `diff(x, x) == []`; permuting a keyed list yields no changes; every reported path resolves in at least one of the two payloads.

**8. Confidence weights (FR-009)** — asserted only indirectly. A table-driven test over known gate outcomes would pin the arithmetic.

---

## Test types not present

| Type | Status | Assessment |
|---|---|---|
| Unit | ✅ Strong | |
| Integration | ✅ Good (backend) | |
| E2E (backend) | ✅ One comprehensive test | |
| **Contract tests against the real vendor** | ❌ | The most valuable missing type — would have caught the envelope-shape uncertainty behind GAP-02 |
| Frontend / UI | ❌ | |
| Property-based | ❌ | |
| Load / stress | ❌ | Never tested beyond 2 sources |
| Security (SAST/DAST) | ❌ | `ruff` includes some `B` rules; no dedicated scanning |
| Dependency scanning | ❌ | |
| Mutation testing | ❌ | Would be genuinely informative on the classifier |

---

## Test infrastructure

`EngineTestCase` (`tests/helpers.py`) gives each test an isolated temp-directory database, a fresh `WorldState`, a `ReplayClient`, and seeded sources with no history.

```python
def setUp(self):
    self._tmp = tempfile.TemporaryDirectory()
    db.configure(str(Path(self._tmp.name) / "test.db"))
    seed.ensure_sources()
    ...

def tearDown(self):
    db.close()          # added this review — WAL handles block unlink on Windows
    self._tmp.cleanup()
```

**Complete isolation, no shared state, no ordering dependencies.** This is the right design and is why the suite runs in 0.4 s.

**Weakness:** `EngineTestCase` constructs `Settings(...)` directly rather than via `from_env()`, so environment parsing is never covered.

---

## Recommended roadmap

| Phase | Work | Effort | Result |
|---|---|---|---|
| 1 | Audit integrity + reliability injection (5 tests) | 3 h | Closes both CRITICAL gaps |
| 2 | API route coverage (~12 tests) | 3 h | Every state-changing route tested |
| 3 | Frontend smoke tests | 3 h | Closes the empty layer |
| 4 | `coverage.py` in CI with a threshold | 1 h | Coverage becomes measured |
| 5 | Property-based differ tests | 2 h | Structural confidence |
| 6 | Live contract tests (needs GAP-02) | 4 h | Validates envelope shapes |

Phases 1–2 (6 hours) would raise requirement-to-test traceability from 52% to roughly 75%.

---

**Next:** [Test Cases](Test_Cases.md) · [Performance Validation](Performance_Validation.md)
