# CI/CD

[← Documentation index](../README.md) · [← Deployment Architecture](Deployment_Architecture.md)

---

## 1. The real pipeline

One workflow, one job, no deployment step.
Evidence: `.github/workflows/ci.yml`

```mermaid
flowchart LR
  T[push or pull_request<br/>any branch] --> CO[actions/checkout@v4]
  CO --> PY[actions/setup-python@v5<br/>python 3.11]
  PY --> DEPS[pip install flask, pydantic>=2,<br/>jsonschema, pyyaml, httpx, ruff]
  DEPS --> LINT[ruff check apps/engine]
  LINT --> TEST[python -m unittest discover -s tests -v]
```

| Step | What it does | What it does NOT do |
|---|---|---|
| `actions/checkout@v4` | Clones the repo | — |
| `actions/setup-python@v5` | Installs Python 3.11 only | No matrix; 3.13 is exercised locally (both `cpython-311` and `cpython-313` `.pyc` caches exist in the repo) but never in CI |
| Install dependencies | `pip install flask "pydantic>=2" jsonschema pyyaml httpx ruff` | **Does not run `pip install -r requirements.txt`** — the package list is duplicated inline in the workflow file. See the finding below |
| Lint | `ruff check apps/engine` | Does not lint `apps/web` (there is no linter configured for the vanilla-JS frontend at all) |
| Tests | `python -m unittest discover -s tests -v` from `apps/engine`, runs all 23 tests | No coverage measurement, no coverage gate, no JUnit/XML report artifact |

**CI runs on every push and every pull request, with no branch filter and no path filter.** There is no separate workflow for docs-only changes.

## 2. What CI does not do

Stated plainly, because a reviewer will check:

- **No build step.** There is nothing to build — no bundler, no compiled artifact, no Docker image.
- **No artifact publishing.** Nothing is uploaded (no wheel, no image, no release asset).
- **No deployment.** There is no CD. Merging to `main` has no effect beyond the merge itself. **NOT IMPLEMENTED.**
- **No security scanning.** No `pip-audit`, no `safety`, no Dependabot alerts wired into a required check, no SAST. `requirements.txt` pins no versions beyond a floor (`>=`) — see finding below.
- **No frontend testing.** Consistent with [ADR-011](../03_Architecture/ADRs/README.md#adr-011--zero-build-vanilla-es-module-frontend): `apps/web` has zero tests, and CI does not attempt to add any.
- **No branch protection evidence in-repo.** Whether `main` requires the `engine` check to pass before merge is a GitHub repository setting, not something visible in the workflow file itself — **UNKNOWN**, not claimed either way.
- **No dependency caching.** Every run does a cold `pip install`; harmless at this scale, but adds avoidable minutes as the suite grows.
- **No release process.** No tags, no changelog generation, no version stamping anywhere in the codebase.

## 3. Finding — the dependency list is duplicated, not sourced from `requirements.txt`

`requirements.txt` (repo root) declares:

```
flask>=3
pydantic>=2
jsonschema>=4
pyyaml>=6
httpx>=0.27
```

The workflow's `pip install` line hand-lists the same five packages (plus `ruff`, which is CI/dev-only and correctly absent from `requirements.txt`) rather than running `pip install -r requirements.txt`. Today the two lists agree. **They have no mechanism keeping them in sync** — a developer who bumps a floor in `requirements.txt` (e.g. to require `flask>=3.1` for a bug fix) will not see that reflected in CI unless they remember to edit the workflow file too. This is a real, low-severity engineering inconsistency: one canonical source of truth (`requirements.txt`) exists, and CI does not use it.

**RECOMMENDED:** `pip install -r requirements.txt ruff`. ~5 minutes.

## 4. RECOMMENDED — production-grade pipeline

None of this exists; it is a recommendation, ranked by value against effort.

| # | Addition | Effort | Value |
|---|---|---|---|
| 1 | `pip install -r requirements.txt` instead of the duplicated list | 5 min | Removes a drift source |
| 2 | Cache `~/.cache/pip` keyed on `requirements.txt` hash | 15 min | Faster CI as the suite grows |
| 3 | Matrix Python 3.11 **and** 3.13, matching what is actually exercised locally | 15 min | Catches version-specific regressions before they ship |
| 4 | `pip-audit` (or Dependabot security alerts as a required check) | 30 min | Every dependency has an unpinned floor; a known-CVE transitive update currently ships silently |
| 5 | Coverage measurement (`coverage run -m unittest discover`) reported in the job summary | 30 min | Makes the "23 tests pass" claim quantifiable as a percentage, not just a count |
| 6 | A frontend check — even a syntax/lint pass with a zero-config tool — once `apps/web` has any tests to run | 1–2 h | Closes the biggest testing gap in the system ([Gap Report](../11_Assessment/Engineering_Gap_Report.md)) |
| 7 | Require the `engine` check on branch protection for `main` (a repository setting, not a workflow change) | 5 min | Makes CI advisory-only vs. actually gating |
| 8 | A second workflow: build + push a container image on tag (after [Deployment Architecture § Containerise](Deployment_Architecture.md#9-recommended--production-deployment-shape) exists) | 2–3 h | First real CD step |
| 9 | Staged CD: deploy to a staging target, smoke-test against `/api/stats`, promote on green | Half day+ | Out of scope until an actual staging environment exists |

Items 1–5 are same-day, no-new-infrastructure improvements. Items 6–9 depend on prerequisites documented elsewhere ([Test Strategy](../07_Testing/Test_Strategy.md), [Deployment Architecture](Deployment_Architecture.md)) and are correctly out of scope for this build's 7-day window.

---

**Next:** [AI Architecture](../09_AI_ML/AI_Architecture.md) · [Engineering Gap Report](../11_Assessment/Engineering_Gap_Report.md)
