---
title: "38.4: `doctor check .` completes on the primary checkout"
type: 'fix'
created: '2026-10-01'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - docs/dreams/pyforge-doctor.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/env_hygiene.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** On the primary checkout `doctor check .` always reports the env-hygiene check incomplete: `_discover_python_files`
walks untracked local directories (`.cursor/cdao-p15-noarch-build`, `var/scribe-pg`, `var/platform-local`) and stops at
`_DISCOVERY_ENTRY_CAP` (57,142 entries against 50,000), so it may miss findings (DW-OPS-2026-10-01-3).

**Approach:**

- In a git work tree, prune directories git ignores or does not track: ask git once per run (for example
  `git ls-files --others --ignored --exclude-standard --directory`), never once per directory, and skip those directories in
  the walk.
- The cap and its incomplete report stay for a truly huge tracked tree. Outside a git work tree, or when git fails, the
  walk is unchanged.

Ledger key: `38-4-doctor-check-completes-on-the-primary-checkout`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- CAP-1 (FR-3, the credential/env-hygiene check). A defect, so no new CAP; `spec-feature-flag-governance` Q1: a `fix`
  needs no flag.

## Acceptance Criteria

- Given an ignored directory full of files in a git work tree When the walk runs Then it is not entered
- Given a tracked file whose parent is otherwise ignored When the walk runs Then the tracked file is still scanned
- Given a target that is not a git work tree When the walk runs Then it walks as today
- Given a tracked tree larger than the cap When the walk runs Then it still reports incomplete
- Given the primary checkout When `doctor check .` runs Then env-hygiene reports complete
- Given the pruning is removed When the new tests run Then they fail (mutation)

## Tasks

1. Read `checks/env_hygiene.py` (`_discover_python_files`, `_DISCOVERY_ENTRY_CAP`).
2. Add one git call per run to list ignored and untracked directories; prune them in the walk.
3. Tests for each matrix row in `tmp_path` git repos; run `doctor check .` on the primary checkout.

## Boundaries & Constraints

**Always:**
- One git call per run.
- Read every verdict from the exit code, never through a pipe.

**Never:**
- Do not raise the cap to hide the problem.
- Do not skip a tracked file.
- Do not hand-edit any `SPEC.md`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| ignored dir | git work tree | pruned | — |
| tracked under ignored | tracked file | scanned | — |
| not a work tree | plain directory | walk unchanged | git failure → unchanged |
| huge tracked tree | over the cap | incomplete | — |

</intent-contract>

## Binding

Parent capability: CAP-1 (FR-3; defect, no new CAP). DW-OPS-2026-10-01-3.
Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-10-01 entry.
Ledger key: `38-4-doctor-check-completes-on-the-primary-checkout`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-01 by operator ruling: the deferral burn-down's "stop the inflow" changes run before its Phase 2.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-doctor pyforge-doctor-test` — expected: pass (the station's `verify_commands`).

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
