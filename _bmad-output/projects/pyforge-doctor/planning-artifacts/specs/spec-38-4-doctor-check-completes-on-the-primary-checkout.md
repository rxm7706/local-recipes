---
title: "38.4: `doctor check .` completes on the primary checkout"
type: 'fix'
created: '2026-10-01'
status: 'in-progress'
baseline_revision: 'd6b0a85992a698f49ab2a3158c1a24b06ecbd7d6'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - docs/dreams/pyforge-doctor.md
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/env_hygiene.py
warnings:
  - oversized
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

## Code Map

- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/env_hygiene.py` -- `_discover_python_files` (L207-251) is the walk; `_DISCOVERY_ENTRY_CAP` (L202, 50_000) counts dir names plus files; `_PRUNED_DIR_NAMES` (L153) is the by-name prune; the module docstring (L103) says "no subprocess", which goes stale.
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/cli_bridge.py` -- `run_git(cwd, args, *, timeout=30.0, ok_exit_codes)` (L71-126) raises `CliBridgeError` on every failure. AD-5: the sole subprocess site (`tests/meta/test_cli_bridge_sole_subprocess.py`), so the walk calls it, never `subprocess`. Sources import `from ..cli_bridge import CliBridgeError, run_git`.
- `src/shared/packages/pyforge-doctor/tests/unit/test_checks_env_hygiene.py` -- walk tests at L331-454 (`_write`, non-git `tmp_path`, `_DISCOVERY_ENTRY_CAP` monkeypatch); the new matrix tests go beside them.
- `src/shared/packages/pyforge-doctor/tests/unit/test_sources_frozen_path.py` -- L25-64: the `_LEAKY_GIT_VARS` env scrub and `_init_repo` idiom to copy (a hook-set `GIT_DIR` would retarget `git`).
- `src/shared/packages/pyforge-doctor/tests/meta/test_env_hygiene_no_execution.py` -- pins exec/eval/importlib only; read-only here.
- Git probe, measured 2026-10-01 in a scratch repo: `git ls-files --others --ignored --exclude-standard --directory -z` lists a wholly ignored dir as `dir/` (one entry, no descent), omits a dir holding a tracked file (lists its ignored children instead), and exits 128 (`fatal`) both outside a work tree and when run from inside an ignored dir. `var/` and `.cursor/` are gitignored (`git check-ignore -v`).

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-doctor/src/pyforge/doctor/checks/env_hygiene.py` -- add `_git_ignored_dirs(target)`: one `run_git(target, [...], -z)` per walk, keep entries ending `/`, return normalized absolute paths; `CliBridgeError` returns an empty set. `_discover_python_files` skips those dirs in `dirnames` before counting. Fix the L103 docstring line.
- `src/shared/packages/pyforge-doctor/tests/unit/test_checks_env_hygiene.py` -- one test per I/O matrix row in throwaway `tmp_path` git repos, plus a one-call-per-run pin and a mutation check on the pruning.

**Acceptance Criteria:**
- Given the intent-contract matrix and ACs above, when the new tests run, then each row passes and each fails with the pruning removed.
- Given this checkout's three gitignored dirs filled past the cap, when `doctor check .` runs, then env-hygiene reports complete.

## Spec Change Log

## Design Notes

Prune only what git IGNORES, not what it merely does not track: a new, not-yet-added source directory is first-party code the scan must still reach. Directories only, so an ignored `.py` file inside a mixed directory is still scanned. A target inside an ignored directory makes git exit 128; that falls back to today's walk.

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
- `pixi run -e pyforge-guild lint-types` — expected: exit 0 (a dispatch landing can red it; it is not in the merge gate's `verify_commands`).
- `python scripts/spec_surface_reconcile.py` — expected: exit 0, after naming every governed path on the owning Spec's `.memlog.md` and each co-governor's.

**Manual checks (if no CLI):**
- Fill this worktree's gitignored `var/scribe-pg`, `var/platform-local` and `.cursor/cdao-p15-noarch-build` past the cap, run `doctor check .`, and read the exit code and the env-hygiene finding; remove the fill afterwards.

## Review Triage Log

- No independent review has run yet (implementation and review stay separate).
