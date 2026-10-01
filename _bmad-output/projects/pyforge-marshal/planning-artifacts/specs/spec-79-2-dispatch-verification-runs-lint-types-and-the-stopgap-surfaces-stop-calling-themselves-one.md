---
title: "79.2: Dispatch verification runs `lint-types`, and the \"stopgap\" surfaces stop calling themselves one"
type: 'fix'
created: '2026-10-01'
status: 'in-progress'
baseline_revision: '6701b2b15a70fa9df0f8ea0287e2edc4fbeca66a'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - docs/dreams/pyforge-marshal.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `dispatch/*` branches skip `pr-preflight` because the dispatch supervisor gates them, but the supervisor's verification
runs only the station's `verify_commands` plus the derived surface-reconcile guard (Story 53.1). `lint-types` is in
neither and is outside the `detectors-ci` merge gate, so scribe Story 25.1 landed `except (OSError,
subprocess.TimeoutExpired):`, which `ruff format` (py314, PEP 758) rewrites, and `lint-types` stayed red on `main` from
`a1dbda7915` until #1690 (DW-OPS-2026-10-01-2). Separately, marshal's `"22"` and `"28"` `epic_surfaces` entries still
say they are a stopgap until Story 28.15 ships; 28.15 is `done` (DW-FU-28-14-4, DW-OPS-2026-10-01-3).

**Approach:**

- **lint-types:** derive `pixi run --frozen -e pyforge-guild lint-types` in one place beside
  `_verify_commands_with_surface_guard`, so every station's dispatch verification runs it exactly once whatever its own
  `verify_commands` say; never by editing eight `verify_commands` lists. A red result refuses the landing with a finding
  that names `lint-types`. `gate.check_spec_binding` is one-directional (an extra policy command is never a finding), so
  no tracked spec's binding changes.
- **The "22"/"28" entries stay.** Their station-wide globs are the convention every later marshal epic declares, and Epic
  73's follow-up reviews of done 22.x/28.x stories dispatch against them. Only their comments change: they say the
  station-wide surface is the convention, not a stopgap. Their globs do not change.

Ledger key: `79-2-dispatch-verification-runs-lint-types-and-the-stopgap-surfaces-stop-calling-themselves-one`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- CAP-261 (a) (Story 53.1, the derived verification guard); `spec-marshal-token-economy` CAP-17 (Story 28.15, the
  scope-violation mode that ended the stopgap).
- A defect of the supervisor's verification gate, so no new CAP; `spec-feature-flag-governance` Q1: a `fix` needs no flag.

## Acceptance Criteria

- Given any station's dispatch When verification runs Then `pixi run --frozen -e pyforge-guild lint-types` runs exactly once, after the station's own `verify_commands`
- Given a change that fails `lint-types` When the dispatch verifies Then the landing is refused with a finding naming `lint-types`
- Given a station whose `verify_commands` already names `lint-types` When verification runs Then it still runs once
- Given every tracked story spec When `gate.check_spec_binding` runs against the widened commands Then no new finding appears
- Given marshal-policy.toml When it is read Then the `"22"` and `"28"` globs are unchanged and their comments no longer call them a stopgap
- Given the derived `lint-types` is removed When the new tests run Then they fail (mutation)

## Tasks

1. Read `dispatch_verify.py` (`_verify_commands_with_surface_guard` and its callers) and `core/gate.py::check_spec_binding`.
2. Derive the `lint-types` command beside the surface guard; dedupe against a station's own list.
3. Name the lane in the refusal finding.
4. Rewrite the `"22"`/`"28"` comments in marshal-policy.toml; leave the globs.
5. Tests: with and without the command in a station's list, a failing lint run refusing, the binding unchanged; run the mutation by hand.

## Boundaries & Constraints

**Always:**
- `lint-types` is added in one derived place for every station.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not edit any station's `verify_commands` list.
- Do not change the `"22"`/`"28"` globs or remove those entries.
- Do not hand-edit `sprint-status-ledger.yaml` or any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| clean change | lint-types green | verification passes | — |
| lint-red change | lint-types red | landing refused, `lint-types` named | — |
| already listed | station lists lint-types | runs once | — |
| binding | every tracked spec | no new MRS-GATE-011 | — |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/dispatch_verify.py` -- `_verify_commands_with_surface_guard` (the one derived-commands site: three callers, `run_verify_commands_only`, `evaluate_dispatch_verification`, `cli/drain_plan.py::verify_commands`); the guard constant is imported from `adapters/harness_bmadloop.py::_SURFACE_RECONCILE_COMMAND`.
- `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py` -- `classify_outcome` already emits `MRS-GATE-001` with `verify command '<command>' exited N`, so a red lane names `lint-types` with no new finding code; `check_spec_binding` is one-directional (read-only evidence).
- `src/shared/packages/pyforge-marshal/tests/unit/test_dispatch_verification.py`, `tests/unit/test_dispatch_verify_merge_tree.py` -- assert the exact derived command lists; both widen by one entry.
- `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml` -- the `"22"` (line ~107) and `"28"` (line ~129) comments; the `"79"` surface already lists this file.
- `pixi.toml` `[feature.guild-tasks.tasks.lint-types]` -- the task the derived command runs (read-only).

## Binding

Parent capabilities: CAP-261 (a); `spec-marshal-token-economy` CAP-17 (defects; no new CAP). DW-OPS-2026-10-01-2, DW-OPS-2026-10-01-3, DW-FU-28-14-4.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-01 entry.
Ledger key: `79-2-dispatch-verification-runs-lint-types-and-the-stopgap-surfaces-stop-calling-themselves-one`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-01 by operator ruling: the deferral burn-down's "stop the inflow" changes run before its Phase 2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`).

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
