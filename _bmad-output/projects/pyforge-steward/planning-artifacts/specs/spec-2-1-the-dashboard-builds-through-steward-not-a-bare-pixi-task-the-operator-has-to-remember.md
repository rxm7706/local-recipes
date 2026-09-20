---
title: 'Story 2.1: The dashboard builds through Steward, not a bare pixi task the operator has to remember'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** `docs/dashboard/data.js` today is only refreshed by an operator remembering to run `retired-console-check` (or the raw `Lane 1 /console/ (Guildhall generator retired)`) by hand — there is no Steward-owned entrypoint for the first duty (`deploy`) at all; `resolve_duty("deploy")` still returns `NullDuty`.

**Approach:** Add `deploy.py`, this epic's single file (mirrors `keys.py`'s precedent), with a `build_dashboard()` primitive that invokes the exact `dashboard-gen` pixi task (`retired-console-check`) as a subprocess — AD-1: wrap, never reimplement `pyforge.doctor.sources.fleet_scan`'s logic. Wire a `DeployDuty` (`Duty`-conforming, mirrors `KeysDuty`) that `resolve_duty("deploy")` now returns, and a `steward deploy dashboard --build` CLI verb. A non-zero `dashboard-gen` exit is caught at the `DeployDuty` boundary and reported as a `DutyResult(ok=False, ...)`, never a crash (AD-8).

## Boundaries & Constraints

**Always:**
- `build_dashboard` shells out to `["pixi", "run", "-e", "local-recipes", "dashboard-gen"]` — the exact pixi task named in `pixi.toml`'s `[feature.local-recipes.tasks.dashboard-gen]` — never a reimplementation of `pyforge.doctor.sources.fleet_scan`'s own logic (AD-1). The command is injectable (`cmd: Sequence[str] | None = None`, defaulting to the real pixi invocation) so tests can substitute a fast fixture command without installing the 1102-package `local-recipes` env — the same "subprocess boundary mocked or run for real" latitude `test-architecture.md` already calls out for this story.
- `build_dashboard` uses `subprocess.run(..., check=True, capture_output=True, text=True)` — a non-zero exit raises `subprocess.CalledProcessError`, propagated (not swallowed) to `DeployDuty.run`'s boundary catch, mirroring `KeysDuty`'s existing `age`-failure handling.
- `resolve_duty("deploy")` returns a real `DeployDuty` (lazy-imported inside `resolve_duty`, matching the `keys` precedent's import-time-isolation rationale, even though `deploy.py` has no fragile import-time bridge today — consistent dispatch shape).
- `steward deploy` with no verb still degrades to `DutyResult(ok=True, ...)` naming available verbs (AD-7) — required for `test_cli.py`'s existing `test_each_duty_dispatches_and_succeeds` parametrization over all four `DUTIES` to keep passing unchanged.
- `repo_root()` in `deploy.py` is a self-contained walk-up search (mirrors `keys.py`'s `locate_http_module`/`repo_root`, but keyed on `pyforge.doctor.sources.fleet_scan` rather than `_http.py` — `deploy.py` has no reason to import `keys.py`'s conda-forge-expert bridge).

**Block If:** none.

**Never:**
- No diff/commit/push logic yet — that is Story 2.2. `--build` only refreshes `docs/dashboard/` on disk.
- No reimplementation of `generate.py`'s sprint-status parsing, git-log scanning, or dream-frontmatter scanning inside `deploy.py` — `build_dashboard` never imports or duplicates any of that; it only invokes the pixi task as an opaque subprocess.
- No new GitHub Actions workflow, no daemon (AD-4/NFR-2) — this story is a CLI-invoked, one-shot subprocess call.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Happy path | `dashboard-gen` (or its test substitute) exits 0 | `docs/dashboard/` reflects the freshly generated output; `DutyResult(ok=True, ...)` | No error |
| Underlying task fails | `dashboard-gen`'s subprocess exits non-zero | Nothing else runs | `subprocess.CalledProcessError` → `DutyResult(ok=False, summary="deploy dashboard: pixi exited N: <stderr>")` |
| `steward deploy` (no verb) | — | Names the available verbs | `DutyResult(ok=True, ...)`, matches `test_each_duty_dispatches_and_succeeds` |
| `steward deploy dashboard` (no flags) | — | Story 2.2's territory; this story only wires `--build` | N/A this story — deferred |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py` -- NEW: `repo_root()`, `build_dashboard(*, cwd, cmd=None)`, `DeployDuty`
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- add `_add_deploy_subparsers`; `resolve_duty("deploy")` now returns a real `DeployDuty`
- `src/shared/packages/pyforge-steward/tests/conformance/test_deploy_build.py` -- NEW: covers the I/O matrix

## Tasks & Acceptance

**Execution:**
- [x] `deploy.py` -- `repo_root()` (walk-up search keyed on `pyforge.doctor.sources.fleet_scan`)
- [x] `deploy.py` -- `build_dashboard(*, cwd, cmd=None)` -- subprocess wrap, `check=True`
- [x] `deploy.py` -- `DeployDuty` (`name = "deploy"`, dispatches on `deploy_verb`, degrades on no/unknown verb per AD-7)
- [x] `cli.py` -- `_add_deploy_subparsers` wiring `deploy dashboard --build`; `resolve_duty` returns `DeployDuty`
- [x] `tests/conformance/test_deploy_build.py` -- I/O matrix coverage, CLI + primitive level

**Acceptance Criteria:**
- Given the existing `dashboard-gen` pixi task, when `steward deploy dashboard --build` is run, then it invokes that exact task (subprocess, per AD-1) and `docs/dashboard/` reflects freshly generated output.
- Given a failure in the underlying task (non-zero exit), when `steward deploy dashboard --build` is run, then it surfaces as a clear Steward-level error (`DutyResult(ok=False, ...)`), not a silent success.

## Spec Change Log

## Review Triage Log

### 2026-08-07 — Self-review (adversarial re-read before marking done)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- No file-write/state races: this story reads/writes nothing shared (no
  inventory-like store); `build_dashboard` is a single stateless subprocess
  call, so the "read-merge-write race" class the prompt flagged as a
  plausible risk (by analogy with `keys-inventory.yaml`) does not apply
  until Story 2.2 introduces a commit — deferred there, not swallowed here.
- Verified `_run_dashboard` does not silently branch on `ns.build` in a way
  that could diverge from its own docstring: bare `deploy dashboard` and
  `deploy dashboard --build` are currently IDENTICAL (both build-only) —
  intentional per this story's own scope (Story 2.2 adds the branch), and
  the docstring says so explicitly rather than implying `--build` does
  something `bare dashboard` doesn't yet.
- Exception handling checked for over/under-broadness: `DeployDuty.run`
  catches exactly `subprocess.CalledProcessError` (not a bare `Exception`),
  matching `KeysDuty`'s existing boundary discipline — an unrelated bug
  (e.g. a `TypeError` in this module) still propagates to `cli.main()`'s
  own `EXIT_INTERNAL` handler rather than being misreported as a duty
  failure.

## Design Notes

**Why the pixi task, not `Lane 1 /console/ (Guildhall generator retired)` directly:** the AC names the pixi task explicitly (`[feature.local-recipes.tasks.dashboard-gen]`), and going through `pixi run -e local-recipes` keeps this wrapper honest to "wrap, never reimplement" even though `generate.py` itself is stdlib-only — a future change to the task's own command (flags, env) is picked up automatically rather than needing a second edit in `deploy.py`.

**Why `cmd` is injectable:** the real `local-recipes` env is ~9.8GB (per `.github/workflows/dashboard.yml`'s own comment) — a conformance test that had to `pixi install -e local-recipes` before every run would be prohibitively slow for a CLI wrapper this thin. The default remains the real invocation; only tests override it.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (station policy verify command; reconciled 2026-08-30 after policy drifted from this spec's original declaration).

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** landed on `main` as `2221e12892` (2026-09-18, "Rename scribe Story 2.1 spec to match the ledger key"); also `a0ef150159` (2026-08-07, "herald: Story 2.1 — herald deck pull <slug> with etag short-circuit"); also `2ad677d0de` (2026-08-07, "scribe: Story 2.1 — GraphStore port + flat-file v1 adapter"). Ledger row `2-1-the-dashboard-builds-through-steward-not-a-bare-pixi-task-the-operator-has-to-remember: done`.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** `_bmad-output/projects/pyforge-scribe/planning-artifacts/change-history/sprint-change-proposal-2026-08-24-canopy.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/deferred-work-ledger.md`, `_bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-2-1-graphstore-port-flat-file-v1-adapter.md`
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- `## Auto Run Result` reconstructed from git (none survived).
