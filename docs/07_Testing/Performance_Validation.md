# Performance Validation

[← Documentation index](../README.md)

---

> **No performance number in this documentation is estimated, extrapolated, or aspirational.** Everything below was measured during this review with the script reproduced at the end. Everything *not* measured is listed explicitly in [What is not measured](#what-is-not-measured).

---

## Benchmark environment

| Parameter | Value |
|---|---|
| CPU | Intel Core i9-13900HX (13th gen) |
| RAM | 47.7 GB |
| OS | Windows 11 |
| Python | 3.13.11 |
| Mode | `DW_MODE=replay` — **no network I/O** |
| Database | SQLite on local NVMe, WAL, fresh per benchmark |
| Dataset | `nimbusai-pricing`, 4 models, 8 invariants, 1 semantic assertion, 3 continuity rules |
| Timer | `time.perf_counter()` |
| Process | Single, no concurrent load |

---

## Results

| Operation | n | p50 | p95 | p99 | max |
|---|---|---|---|---|---|
| `evaluate()` — all four gates | 2000 | **0.16 ms** | **0.20 ms** | 0.31 ms | 0.83 ms |
| `run_source()` — no-change path | 200 | **6.08 ms** | **7.62 ms** | 9.87 ms | 11.14 ms |
| `run_source()` — structural break + heal + verify + re-run | 60 | **12.22 ms** | **14.55 ms** | 20.99 ms | 20.99 ms |
| Full test suite (23 tests) | 3 runs | **~0.39 s** | — | — | 0.43 s |

### Interpretation

**Contract evaluation is effectively free.** At 0.16 ms for four gates over 4 entities with 12 rules, validation is ~2.6% of a no-change run. The system could afford far richer contracts before validation becomes a cost.

**The no-change path is dominated by SQLite, not logic.** 6.08 ms against 0.16 ms of evaluation means ~97% is database work — roughly 6 commits per run (`runs` insert, credits update, snapshot insert, plus state/audit writes), each its own transaction (see [Database Design § Transactions](../04_Data/Database_Design.md#transactions-and-concurrency)). Batching them into one transaction is the obvious optimisation, and it would also fix the atomicity gap.

**A full heal cycle costs about 2× a plain run** — 12.22 ms versus 6.08 ms — which is what you would expect: an extra heal call, a second `evaluate()`, a version update, and a re-run.

**These numbers exclude the dominant real-world cost.** In live mode a single `run_scraper` is a subprocess invoking a CLI that performs a network scrape, with a 900-second timeout. Real latency will be **three to five orders of magnitude larger** and entirely vendor-bound. The measurements above characterise DriftWatch's own overhead, which is the part the project controls.

---

## Requirements verified

| Requirement | Target | Measured | Verdict |
|---|---|---|---|
| PERF-001 | Contract evaluation < 1 ms p95 | 0.20 ms | ✅ **PASS** (5× margin) |
| PERF-002 | No-change run < 20 ms p95 | 7.62 ms | ✅ **PASS** (2.6× margin) |
| PERF-003 | Heal cycle < 50 ms p95 | 14.55 ms | ✅ **PASS** (3.4× margin) |

> **Honesty note on targets.** PERF-001…003 were written *after* the measurements, during this documentation pass. They are meaningful as regression thresholds going forward; they are **not** evidence that the system was engineered to a pre-stated budget. No performance requirement existed before this review.

---

## What is not measured

Each entry is a real gap, not an oversight to be glossed.

| Area | Status | Why it matters |
|---|---|---|
| **Live-mode latency** | **NOT MEASURED** | No live Bright Data call has ever succeeded (GAP-02). The dominant cost in production is entirely uncharacterised |
| **Concurrency / throughput** | **NOT MEASURED** | Never run beyond 2 sources. SQLite has one writer; `busy_timeout=5000` (added 2026-08-22) now bounds how a collision behaves, but contention behaviour under real concurrent load is still unmeasured |
| **Scaling with source count** | **NOT MEASURED** | `GET /api/sources` is N+1 (3 queries per source); the hot-path snapshot query is unindexed against an unbounded table |
| **Database growth over time** | **NOT MEASURED** | All measurements used a fresh or lightly-seeded DB (103 runs). The last-known-good query is a full scan — degradation is expected to be linear and is unquantified |
| **Memory / CPU under sustained load** | **NOT MEASURED** | No profiling performed |
| **Frontend rendering** | **NOT MEASURED** | 838 lines of JS, no measurement, no tests |
| **Scheduler behaviour under overlap** | **NOT MEASURED** | A run exceeding the tick interval blocks subsequent sources; unquantified |
| **`scan_repo` on a large repository** | **NOT MEASURED** | Reads every file with a matching extension. Against a large monorepo this could dominate a Class 3/4 run |

### The one worth quantifying first

`scan_repo()` walks `repo_dir.rglob("*")`, reads each file with a scannable extension, and scans every line against every entity. That is O(files × lines × entities) with no caching, on a fixture repo of 5 files today. Against a real repository it is the most likely source of a surprise, and it is trivially benchmarkable.

---

## Reproducing these measurements

```bash
pip install -r requirements.txt
python - <<'PY'
import sys, time, tempfile, json
from pathlib import Path
sys.path.insert(0, str(Path("backend").resolve()))
from driftwatch_engine import db, seed
from driftwatch_engine.brightdata.replay import ReplayClient, WorldState
from driftwatch_engine.config import Settings
from driftwatch_engine.llm.provider import HeuristicProvider
from driftwatch_engine.pipeline.runner import Deps, run_source
from driftwatch_engine.contracts.engine import evaluate, load_spec

tmp = tempfile.mkdtemp()
db.configure(str(Path(tmp)/"bench.db")); seed.ensure_sources()
world = WorldState(); client = ReplayClient(world)
deps = Deps(client=client, provider=HeuristicProvider(),
            settings=Settings(mode="replay", db_path=str(Path(tmp)/"bench.db")))
SID = "nimbusai-pricing"

def bench(label, fn, n):
    ts = []
    for _ in range(n):
        t = time.perf_counter(); fn(); ts.append((time.perf_counter()-t)*1000)
    ts.sort(); p = lambda q: ts[min(int(len(ts)*q), len(ts)-1)]
    print(f"{label:<34}n={n:<5}p50={p(.5):7.2f}ms  p95={p(.95):7.2f}ms  p99={p(.99):7.2f}ms")

spec = load_spec(SID)
payload = json.loads(Path(f"fixtures/snapshots/{SID}/v1_baseline.json").read_text())
bench("contract evaluate() 4 gates", lambda: evaluate(payload, spec, payload), 2000)

world.set_variant(SID, "v1_baseline"); run_source(SID, deps)
bench("run_source() no-change path", lambda: run_source(SID, deps), 200)

def heal_cycle():
    world.set_variant(SID, "v1_baseline"); run_source(SID, deps)
    world.set_variant(SID, "v2_redesign"); run_source(SID, deps)
bench("run_source() structural+heal", heal_cycle, 60)
PY
```

---

## Recommended performance work

Ranked by value per hour:

| # | Action | Effort | Expected effect |
|---|---|---|---|
| 1 | Batch a run's writes into one transaction | 2 h | Should materially reduce the 6 ms no-change path; also fixes the audit atomicity gap |
| 2 | Add the 8 recommended indexes | 30 m | Keeps the hot path flat as `snapshots` grows |
| 3 | Fix the `GET /api/sources` N+1 with one JOIN | 1 h | Removes 3-queries-per-source scaling |
| 4 | Benchmark `scan_repo` against a real repo | 1 h | Quantifies the most likely surprise |
| 5 | Load-test 50 sources | 3 h | Establishes the concurrency and contention picture |
| 6 | Characterise live-mode latency (needs GAP-02) | 2 h | The number that actually matters in production |

Items 1 and 2 together are worth doing before any scale claim is made.

---

**Next:** [Database Design § Indexing](../04_Data/Database_Design.md#indexing-analysis) · [Deployment Architecture](../08_Deployment/Deployment_Architecture.md)
