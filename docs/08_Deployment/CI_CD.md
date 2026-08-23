# CI/CD

[← Documentation index](../README.md) · [← Deployment Architecture](Deployment_Architecture.md)

---

## 1. The real pipeline

One workflow, one matrixed job (4 cells), no deployment step.
Evidence: `.github/workflows/ci.yml`

```mermaid
flowchart LR
  T[push or pull_request<br/>any branch] --> CO[actions/checkout@v4<br/>matrix os: ubuntu-latest, windows-latest]
  CO --> PY[actions/setup-python@v5<br/>matrix: 3.10, 3.12]
  PY --> DEPS[pip install -r requirements.txt<br/>+ ruff]
  DEPS --> LINT[ruff check backend]
  LINT --> TEST[python -m unittest discover -s tests -v]
```

| Step | What it does | What it does NOT do |
|---|---|---|
| `actions/checkout@v4` | Clones the repo | — |
| `actions/setup-python@v5` | Installs Python 3.10 and 3.12, on both `ubuntu-latest` and `windows-latest` (4 cells, `fail-fast: false`) | Does not test 3.11 or 3.13 — the matrix pins the supported floor and a recent version, not every release in between |
| Install dependencies | `pip install -r requirements.txt`, then `pip install ruff` | Does not cache `~/.cache/pip`; `ruff` is dev-only so it stays out of `requirements.txt` |
| Lint | `ruff check backend` | Does not lint `frontend` (there is no linter configured for the vanilla-JS frontend at all) |
| Tests | `python -m unittest discover -s tests -v` from `backend`, runs all 23 tests | No coverage measurement, no coverage gate, no JUnit/XML report artifact |

**CI runs on every push and every pull request, with no branch filter and no path filter.** There is no separate workflow for docs-only changes.

## 2. What CI does not do

Stated plainly, because a reviewer will check:

- **No build step.** There is nothing to build — no bundler, no compiled artifact, no Docker image.
- **No artifact publishing.** Nothing is uploaded (no wheel, no image, no release asset).
- **No deployment.** There is no CD. Merging to `main` has no effect beyond the merge itself. **NOT IMPLEMENTED.**
- **No security scanning.** No `pip-audit`, no `safety`, no Dependabot alerts wired into a required check, no SAST. `requirements.txt` pins no versions beyond a floor (`>=`) — see finding below.
- **No frontend testing.** Consistent with [ADR-011](../03_Architecture/ADRs/README.md#adr-011--zero-build-vanilla-es-module-frontend): `frontend` has zero tests, and CI does not attempt to add any.
- **No branch protection evidence in-repo.** Whether `main` requires the `engine` check to pass before merge is a GitHub repository setting, not something visible in the workflow file itself — **UNKNOWN**, not claimed either way.
- **No dependency caching.** Every run does a cold `pip install`; harmless at this scale, but adds avoidable minutes as the suite grows.
- **No release process.** No tags, no changelog generation, no version stamping anywhere in the codebase.

## 3. RESOLVED — the dependency list is no longer duplicated

`requirements.txt` (repo root) declares:

```
flask>=3
pydantic>=2
jsonschema>=4
pyyaml>=6
httpx>=0.27
gunicorn>=22
```

The workflow used to hand-list the same packages inline, with no mechanism keeping the two in sync — a floor bumped in `requirements.txt` would not reach CI unless someone remembered to edit the workflow too. **Fixed:** the install step now runs `pip install -r requirements.txt`, with `ruff` installed separately because it is CI/dev-only and correctly absent from `requirements.txt`. `requirements.txt` is the single source of truth.

## 4. RECOMMENDED — production-grade pipeline

None of this exists; it is a recommendation, ranked by value against effort.

| # | Addition | Effort | Value |
|---|---|---|---|
| 1 | Cache `~/.cache/pip` keyed on `requirements.txt` hash | 15 min | Faster CI as the suite grows |
| 2 | `pip-audit` (or Dependabot security alerts as a required check) | 30 min | Every dependency has an unpinned floor; a known-CVE transitive update currently ships silently |
| 3 | Coverage measurement (`coverage run -m unittest discover`) reported in the job summary | 30 min | Makes the "23 tests pass" claim quantifiable as a percentage, not just a count |
| 4 | A frontend check — even a syntax/lint pass with a zero-config tool — once `frontend` has any tests to run | 1–2 h | Closes the biggest testing gap in the system ([Gap Report](../11_Assessment/Engineering_Gap_Report.md)) |
| 5 | Require the `engine` check on branch protection for `main` (a repository setting, not a workflow change) | 5 min | Makes CI advisory-only vs. actually gating |
| 6 | A second workflow: build + push a container image on tag (after [Deployment Architecture § Containerise](Deployment_Architecture.md#9-recommended--production-deployment-shape) exists) | 2–3 h | First real CD step |
| 7 | Staged CD: deploy to a staging target, smoke-test against `/api/stats`, promote on green | Half day+ | Out of scope until an actual staging environment exists |

Items 1–5 are same-day, no-new-infrastructure improvements. Items 6–9 depend on prerequisites documented elsewhere ([Test Strategy](../07_Testing/Test_Strategy.md), [Deployment Architecture](Deployment_Architecture.md)) and are correctly out of scope for this build's 7-day window.

---

**Next:** [AI Architecture](../09_AI_ML/AI_Architecture.md) · [Engineering Gap Report](../11_Assessment/Engineering_Gap_Report.md)
