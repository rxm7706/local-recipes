---
title: "38.4: `doctor check .` completes on the primary checkout"
type: 'fix'
created: '2026-10-01'
status: 'in-review'
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

### 2026-10-01 — Review pass
- verdicts: 25 findings — high 4, medium 0, low 19, false 2, maybe-false 0
- findings:
  - `[high]` `[patch]` Blind Hunter 1: a non-UTF-8 name under the target crashes the new git call — reproduced here: an ignored file `bad\xff.log` makes `_git_ignored_dirs` raise `UnicodeDecodeError` out of `_discover_python_files`; the old walk tolerated such names. Fixed at the root (`cli_bridge.run_git` raises `CliBridgeError` from the decode error), with a `run_git` test and a real-file walk test.
  - `[low]` `[reject]` Blind Hunter 2: git failure falls back silently / the 30 s default timeout — the fallback is what the intent specifies ("when git fails, the walk is unchanged"); the call measured 0.142 s here; a failure reason in the INCOMPLETE finding or a tuned timeout adds report surface with no measurement behind it.
  - `[low]` `[reject]` Blind Hunter 3: coverage loss undisclosed, and the Charter §6 comment contradicts it — pruning git-ignored directories is what the intent asks for; the Charter §6 sentence belongs to the by-name list (Story 6.1); the trade-off is stated in the new `_git_ignored_dirs` and `_discover_python_files` docstrings and in Design Notes.
  - `[low]` `[reject]` Blind Hunter 4: the Approach says "ignores or does not track" but the code prunes only ignored directories; Spec Change Log empty; Code Map line numbers stale — the intent's example command (`--ignored`), its ACs and its matrix all name ignored directories, and the narrower reading never hides untracked first-party code; the fix is to edit this build's spec, and the Spec Change Log records bad_spec loopbacks only. Code Map lines are pre-change anchors by design. Recorded as a residual risk in Auto Run Result.
  - `[low]` `[patch]` Blind Hunter 5: the test fixture does not stop git reading its default global ignore file — measured: with `XDG_CONFIG_HOME` holding `git/ignore` the ignore applies, with `XDG_CONFIG_HOME=/dev/null` git exits 0 and lists nothing. Fixed: the fixture sets `XDG_CONFIG_HOME` to `os.devnull` and its comment says what it neutralises.
  - `[low]` `[reject]` Blind Hunter 6: the "mutation check" test does not mutate the pruning — it is a control showing the unpruned walk; the production mutation was measured: deleting the prune filter in `_discover_python_files` fails 5 other new tests (`does_not_enter_a_git_ignored_directory`, `still_scans_a_tracked_file_under_an_ignored_directory`, `prunes_for_a_subdirectory_target`, `prunes_for_a_relative_target`, `gather_completes_when_the_only_bulk_is_a_git_ignored_directory`).
  - `[low]` `[reject]` Blind Hunter 7: the gather-completes test has no positive control — the sibling walk tests assert the exact file list, so a walk that scanned nothing fails them; this test's purpose is completeness under the cap.
  - `[low]` `[patch]` Blind Hunter 8: test and evidence gaps — the one real gap was that `DW-OPS-2026-10-01-3` stayed `open`: patched (row closed with the measured evidence). Probed and refuted: directory names with spaces and unicode prune correctly; AC 5 re-measured on the real primary checkout (`doctor check <primary> --env --json` exit 0, no INCOMPLETE finding); this worktree's `.git` file case is the checkout the manual fill ran in; negated patterns and nested `.gitignore` files are git's own semantics with no counter-example shown.
  - `[false]` `[reject]` Blind Hunter 9: path matching fragile, no `normcase` — both the stored entries and the walked paths go through `os.path.normpath`, and both take their case from the filesystem listing, so they cannot disagree; the per-directory `abspath` and one extra git spawn in non-git tests cost microseconds to milliseconds.
  - `[low]` `[patch]` Blind Hunter 10: `_spy_walk` patches the global `os.walk`; the test module docstring lists only Story 1.4 cases — the spy is the idiom the existing `onerror` test already uses and `monkeypatch` restores it (rejected); the docstring was patched to name the discovery-walk pruning.
  - `[high]` `[patch]` Edge Case Hunter 1: `UnicodeDecodeError` escapes `gather` on a non-UTF-8 ignored path — same root cause as Blind Hunter 1; patched with it.
  - `[low]` `[reject]` Edge Case Hunter 2: a hook-exported `GIT_DIR` / `GIT_INDEX_FILE` retargets the production call — every `run_git` caller inherits the environment the same way, the target is normally the repository the hook runs in, and a scrub is a new `run_git` parameter.
  - `[low]` `[reject]` Edge Case Hunter 3: the 30 s `run_git` timeout against a 5 s check budget — hypothetical; the call measured 0.142 s on this repository, and a timeout falls back to the unchanged walk.
  - `[low]` `[reject]` Edge Case Hunter 4: a nested repository's own ignore rules are not applied — the fix needs one git call per nested repository, which "one git call per run" forbids; the outcome is an honest INCOMPLETE report, not a missed finding; no such tree is shown here.
  - `[false]` `[reject]` Edge Case Hunter 5: case-insensitive filesystem mismatch — as Blind Hunter 9: both sides normalise through `normpath` and take their case from the filesystem.
  - `[high]` `[patch]` Edge Case Hunter 6 (claim): `run_git` "raises CliBridgeError on every failure" is false for non-UTF-8 stdout — same root cause as Blind Hunter 1; its docstring now names the case and the contract holds.
  - `[low]` `[reject]` Edge Case Hunter 7 (claim): the Intent says "ignores or does not track", the code prunes only ignored directories — same as Blind Hunter 4.
  - `[high]` `[patch]` Verification Gap, Other findings: `_git_ignored_dirs` crashes `doctor check` on a non-UTF-8 ignored path (reviewer reproduced `doctor check <repo> --env` printing "internal error" and exiting 2) — same root cause as Blind Hunter 1; patched with it.
  - `[low]` `[reject]` Intent Alignment 1: AC 5 is a manual check and its recorded evidence was one memlog sentence — the spec's own Verification lists it as a manual check; re-measured here on the real primary checkout (exit 0, 4 findings, no INCOMPLETE) and now carried on the closed ledger row.
  - `[low]` `[reject]` Intent Alignment 2: readings A (ignored only) and B (ignored and untracked) of the intent differ — as Blind Hunter 4; reading A is the one the example command, the ACs and the matrix select.
  - `[low]` `[reject]` Intent Alignment 3: the huge-tracked-tree row calls `git add -A` but the walk never consults tracked status — by design the cap counts every entry not pruned; the `git add` is incidental and the row's behaviour is right.
  - `[low]` `[reject]` Intent Alignment 4: the not-a-work-tree, git-failure and over-cap rows pass with or without the pruning — they are preservation rows (the matrix says "unchanged"); the mutation AC applies to the pruning rows, 5 of which fail under mutation.
  - `[low]` `[reject]` Intent Alignment 5: tracked-under-ignored is tested at one nesting level — git omits any directory holding a tracked file from the wholly-ignored listing (measured in the Code Map probe); no counter-example at greater depth was shown.
  - `[low]` `[reject]` Intent Alignment 6: the production `run_git` call does not scrub the environment, only the tests do — as Edge Case Hunter 2.
  - `[low]` `[reject]` Intent Alignment 7: the production-mutation measurement existed only as memlog prose — measured now (Blind Hunter 6 row) and recorded in this log and in Auto Run Result; nothing to change in code.
