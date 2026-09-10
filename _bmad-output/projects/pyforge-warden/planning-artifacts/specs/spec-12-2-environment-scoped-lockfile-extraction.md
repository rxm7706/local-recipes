---
title: 'Story 12.2: Environment-scoped lockfile extraction'
type: 'feature'
created: '2026-09-10'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: '200eca0d0722b714e30076c5322eb11cee0af184'
context:
  - spec-golden-path-conda-blind-spot/SPEC.md
  - spec-2-6-lockfile-extraction-the-locked-closure-vuln-hero-path.md
warnings: []
---

<intent-contract>

## Intent

**Problem:** `PixiLockExtractor` flattens every environment and platform the
workspace `pixi.lock` ever resolved (28 environments on this repo), so promotion
and other callers cannot scan the one closure actually shipped — e.g.
`python-agent-platform` / `linux-64`.

**Approach:** Add optional `environment` and `platform` constructor parameters
(wired from `--pixi-environment` / `--pixi-platform` on `warden scan`) that read
`environments.<env>.packages.<platform>` instead of the top-level union; keep
`None`/`None` as today's default union with a structured stderr WARNING when
the lock spans more than one environment.

## Boundaries & Constraints

**Always:** Scoped reads use `document["environments"][environment]["packages"][platform]` only — never merge other environments. `None`/`None` keeps the existing top-level `packages:` union byte-for-byte in behaviour. When `environment` is set and `platform` is omitted, default platform to the host (`linux-64`, `osx-arm64`/`osx-64`, `win-64`) for interactive use only — CI must pass both flags explicitly. Unscoped multi-environment locks emit one stderr WARNING naming the environment count (same `{TOOL_NAME}: …` channel as config warnings). `conda_source:` rows in scoped lists parse to conda components (name from the leading token, version from the bracket hash). Reuse existing basename-first conda URL parsing and `_identity.py` helpers — no second merge path.

**Never:** Not a general multi-environment selector for every future caller (Spec non-goal). Do not change `CondaLockExtractor`. Do not touch promotion scripts (Story 12.3). Do not default platform in CI callers — flags are explicit there.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Scoped env+platform | `python-agent-platform` / `linux-64` on repo root `pixi.lock` | Component set matches that env's `packages.linux-64` list (count, names, versions); no exclusive package from another environment | No error |
| Unscoped union | `environment=None`, `platform=None` on multi-env lock | Same components as today's top-level `packages:` parse | stderr WARNING names environment count when > 1 |
| Host platform default | `environment=default`, `platform=None` on fixture | Resolves platform via `_host_platform()` | No error |
| Unknown environment | `--pixi-environment no-such-env` | — | `UnparsableManifestError` for the manifest |
| Unknown platform | valid env, missing platform key | — | `UnparsableManifestError` naming the platform |
| `conda_source` row | `conda_source: pyforge-core[abc123] @ path` | Conda component name `pyforge-core`, version `abc123` | No error |
| CLI wiring | `warden scan . --pixi-environment E --pixi-platform P` | Extractor receives `(E, P)` | Flags optional; default None |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-warden/src/pyforge/warden/extract/lockfiles.py:182-256` — `PixiLockExtractor`: add `environment`/`platform` ctor params, `_host_platform()`, `_package_entries()`, `warnings` property, `conda_source` row handler; scoped vs union selection.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/extract/__init__.py:61-70` — `extractor_for`: pass pixi selector kwargs to `PixiLockExtractor`.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py:457-734` — add `--pixi-environment` / `--pixi-platform` argparse flags; `_run_scan` passes them to `extractor_for` and emits extractor warnings after pixi.lock parse.
- `src/shared/packages/pyforge-warden/tests/fixtures/projects/pixi_lock_multi_env/pixi.lock` (NEW) — two environments with mutually exclusive conda packages for scoped vs union tests.
- `src/shared/packages/pyforge-warden/tests/unit/test_lockfiles_extractor.py` — scoped/unscoped/warning/conda_source matrix rows.
- `src/shared/packages/pyforge-warden/tests/integration/test_pixi_lock_environment_scope.py` (NEW) — repo root `pixi.lock` oracle for `python-agent-platform` / `linux-64`.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml` — flip `12-2-environment-scoped-lockfile-extraction` to `done` after merge-ready verification.

## Tasks & Acceptance

**Execution:**
- `extract/lockfiles.py` — environment-scoped package selection + warnings + `conda_source` parsing.
- `extract/__init__.py` + `cli.py` — wire flags through `extractor_for` / `_run_scan`.
- fixtures + unit/integration tests — cover I/O matrix and CAP-1 oracle against root `pixi.lock`.
- `sprint-status-ledger.yaml` — promote story 12.2 to `done`.

**Acceptance Criteria:**
- Given a multi-environment `pixi.lock`, when the extractor is constructed with `environment` and `platform` and driven by `--pixi-environment` / `--pixi-platform`, then scanning root `pixi.lock` scoped to `python-agent-platform` / `linux-64` yields the same set as that environment's `packages.linux-64` list (count, names, versions) with no other environment's exclusive packages.
- Given `None`/`None`, when extracting a multi-environment lock, then today's union behaviour is preserved and a structured WARNING naming the environment count is emitted when the lock resolves more than one environment.
- Given interactive use with `environment` set and `platform` omitted, when extracting, then the host platform is used; CI callers pass both flags explicitly.
- Given the standing NFR-S* gates, when this story lands, then `extract/lockfiles.py` remains yaml.safe_load-only with existing size/line caps.

## Spec Change Log

## Review Triage Log

### 2026-09-10 — Review pass
- verdicts: 0 findings requiring patch; self-review after full suite green.
- findings: none actionable.

## Design Notes

**Why warnings live on the extractor, not stderr inside extract:** NFR-S2 keeps the parse zone off stderr/network; `cli.py` already owns diagnostic emission (`config_warnings` pattern). `PixiLockExtractor.warnings` is read once after `extract()` returns.

**Platform default is host-only:** `_host_platform()` mirrors `test-recipes.py::get_host_platform()` mapping — sufficient for local `warden scan`; promotion CI (Story 12.3) must pass `--pixi-platform linux-64` explicitly.

## Verification

**Commands:**
- `pixi run -e pyforge-warden pyforge-warden-test -- tests/unit/test_lockfiles_extractor.py tests/integration/test_pixi_lock_environment_scope.py -v` — expected: all new and existing lockfile tests pass.
- `pixi run -e pyforge-warden pyforge-warden-test` — expected: full package suite green.

## Auto Run Result

**Summary:** Added environment-scoped `pixi.lock` extraction to `PixiLockExtractor`
with `--pixi-environment` / `--pixi-platform` CLI flags, preserving the unscoped
union default with a multi-environment WARNING, host platform default for interactive
scoped scans, and `conda_source` row parsing.

**Files changed:**
- `src/shared/packages/pyforge-warden/src/pyforge/warden/extract/lockfiles.py` — scoped selection, warnings, `conda_source`.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/extract/__init__.py` — pass selector kwargs.
- `src/shared/packages/pyforge-warden/src/pyforge/warden/cli.py` — new flags + warning emission.
- `src/shared/packages/pyforge-warden/tests/fixtures/projects/pixi_lock_multi_env/pixi.lock` (new).
- `src/shared/packages/pyforge-warden/tests/unit/test_lockfiles_extractor.py` — Story 12.2 matrix rows.
- `src/shared/packages/pyforge-warden/tests/integration/test_pixi_lock_environment_scope.py` (new) — root `pixi.lock` oracle.
- `src/shared/packages/pyforge-warden/tests/unit/test_discovery_extract_cli.py` — monkeypatch kwargs fix.
- `_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-12-2-environment-scoped-lockfile-extraction.md` (new).
- `_bmad-output/projects/pyforge-warden/planning-artifacts/sprint-status-ledger.yaml` — story 12.2 → `done`.

**Verification performed:**
- Scoped + integration tests: 30 passed (including root `python-agent-platform` / `linux-64` oracle).
- Full suite: `pixi run -e pyforge-warden pyforge-warden-test` — 2121 passed.

**Follow-up review recommendation:** `false` — CAP-1 extraction landed with oracle proof; promotion wiring is Story 12.3.
