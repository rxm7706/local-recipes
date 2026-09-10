---
title: '`verify_scope` guards `marshal factory dispatch`'
type: 'feature'
created: '2026-09-09'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'e15c12a98a4fd3e76466b39e48ba2dd0cdbc56fc'
context:
  - spec-bmad-switch-scope-enforcement/SPEC.md
  - spec-20-7-both-guards-hard-fail-on-drift.md
warnings: []
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Story 20.7 wired `verify_scope` at `scripts/bmad-switch` and `marshal init`
only. Every parallel BMAD write enters through `marshal factory dispatch`, which stamps
`BMAD_ACTIVE_PROJECT` per invocation but never checks the repo triangle against the
resolved project — so a desynced marker/symlink home still launches.

**Approach:** Call the sole S-20.6 `verify_scope` primitive at the `dispatch_once`
boundary (before spec/harness/worktree work), hard-refusing with `MRS-DISP-041` and a
message naming expected vs marker vs both artifact symlinks. Also refuse when
`BMAD_ACTIVE_PROJECT` is set in the parent env and disagrees with the dispatch slug.
Export `format_scope_drift` from `scope.py` so dispatch and bmad-switch share one
wording shape (dispatch imports it; bmad-switch unchanged this story).

## Boundaries & Constraints

**Always:** One shared `verify_scope` implementation — import `pyforge.marshal.scope`,
never a second triangle check body. Hard-fail (ERROR), never advisory. Check runs on
`repo_root` against the dispatch `slug` before provisioning. Tests seed a real triangle
when exercising dispatch in tmp repos.

**Never:** No skill-injection mechanism. No `scripts/bmad-switch` edits. No change to
`verify_scope` semantics. No `bmad-project-context` / AGENTS.md refresh in this story.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Triangle agrees | marker + both symlinks point at dispatch slug | dispatch proceeds unchanged | No error |
| Triangle drift | marker/symlinks disagree with dispatch slug | `MRS-DISP-041` ERROR, message names all corners | No launch |
| Env disagrees | `BMAD_ACTIVE_PROJECT` set and ≠ dispatch slug | `MRS-DISP-041` ERROR naming env vs slug | No launch |
| Empty env | `BMAD_ACTIVE_PROJECT` unset or whitespace-only | only triangle check applies | per triangle row |

</intent-contract>

## Code Map

- `src/pyforge/marshal/scope.py` — add `format_scope_drift(ScopeDrift) -> str` (shared stderr/message shape)
- `cli/dispatch.py:1318+` — `dispatch_once`: after `repo_root` resolution, before spec lookup; new `_dispatch_scope_refusal(repo_root, slug) -> Finding | None`
- `core/findings.py` — register `MRS-DISP-041` (Story 33.9 / spec-bmad-switch-scope-enforcement CAP-1 third call site)
- `core/verdict.py` — `MRS-DISP-041`: `Verdict.ERROR`
- `tests/unit/test_dispatch.py` — drift/env refuse + happy path with seeded triangle
- `tests/unit/scope_triangle.py` — shared `point_scope_triangle(root, slug)` for dispatch tests
- `tests/unit/test_findings.py` — registry includes `MRS-DISP-041`
- `planning-artifacts/sprint-status-ledger.yaml` — flip `33-9-verify_scope-guards-marshal-factory-dispatch` to `done` via sprint-ledger-sync

## Tasks & Acceptance

**Execution:**
- `scope.py` — export `format_scope_drift`
- `cli/dispatch.py` — `_dispatch_scope_refusal` + call in `dispatch_once`
- `core/findings.py` + `core/verdict.py` — register `MRS-DISP-041` as ERROR
- `tests/unit/scope_triangle.py` — shared triangle seeder for tmp repos
- `tests/unit/test_dispatch.py` — matrix rows + fix existing dispatch tests to seed triangle
- other dispatch test modules — seed triangle where `dispatch_once`/`run_dispatch` uses tmp_path
- `planning-artifacts/sprint-status-ledger.yaml` — sync story to `done`

**Acceptance Criteria:**
- Given marker and both symlinks agree on slug B but dispatch targets slug A, when `dispatch_once` runs, then it returns `MRS-DISP-041` ERROR naming expected A and found B on each corner
- Given `BMAD_ACTIVE_PROJECT=pyforge-atlas` and dispatch slug `pyforge-marshal`, when `dispatch_once` runs, then it returns `MRS-DISP-041` ERROR naming both values and does not launch
- Given a seeded aligned triangle for the dispatch slug, when `dispatch_once` runs, then scope check passes and behavior matches the pre-33.9 happy path

## Spec Change Log

## Review Triage Log

### 2026-09-09 — Review pass
- verdicts: 0 findings — high 0, medium 0, low 0, false 0, maybe-false 0
- findings: (none — implementation matched intent on first pass)

## Auto Run Result

Status: done

**Summary:** Wired the sole `verify_scope` primitive at the `dispatch_once` boundary
(`MRS-DISP-041` ERROR). Dispatch now refuses when the repo triangle or parent
`BMAD_ACTIVE_PROJECT` disagrees with the resolved slug, before spec/harness/worktree
work. Added `format_scope_drift` to `scope.py` for shared message shape.

**Files changed:**
- `scope.py` — `format_scope_drift` export
- `cli/dispatch.py` — `_dispatch_scope_refusal` + preflight in `dispatch_once`
- `core/findings.py`, `core/verdict.py` — register `MRS-DISP-041` as ERROR
- `tests/unit/scope_triangle.py` — shared triangle seeder for dispatch tests
- `tests/unit/test_dispatch.py` — scope matrix tests + triangle/env seeding
- `tests/unit/test_dispatch_fleet.py`, `test_dispatch_station_guard.py` — scope seeding
- `tests/unit/test_findings.py` — registry entry
- `planning-artifacts/specs/spec-33-9-*.md` — story spec (this file)
- `planning-artifacts/sprint-status-ledger.yaml` — story 33.9 → done

**Review:** 0 patches; no deferrals.

**Follow-up review recommended:** false

**Verification:** `pixi run -e pyforge-marshal pytest` on verify_scope + dispatch +
dispatch_station_guard + dispatch_fleet + findings — 174 passed.

## Verification

**Commands:**
- `pixi run -e pyforge-marshal pyforge-marshal-test -- tests/unit/test_verify_scope.py tests/unit/test_dispatch.py tests/unit/test_dispatch_station_guard.py tests/unit/test_dispatch_fleet.py tests/unit/test_findings.py -q` — expected: all pass
- `pixi run -e pyforge-marshal pytest src/shared/packages/pyforge-marshal/tests/unit/test_dispatch.py -k scope -q` — expected: new scope guard tests pass
