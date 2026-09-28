---
title: '69.1: The switch script runs where it is documented to run'
type: 'fix'
created: '2026-09-28'
status: 'backlog'
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - docs/dreams/pyforge-marshal.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Every document names the bare form — `scripts/bmad-switch <slug>` and `scripts/bmad-switch --current` in AGENTS.md, the pre-shell hook's `bmad-switch-unsafe` denial in `docs/governance/guild-roster.json`, and 326 tracked Markdown files, none with an interpreter prefix. The script's shebang is `#!/usr/bin/env python3`, which on this machine is the system Python 3.12.3. There `--current` crashes with a chained traceback:
- `_load_verify_scope` (`scripts/bmad-switch:45-62`) first imports `pyforge.marshal.scope` (`:48`); the system interpreter has no `pyforge`, so it raises `ModuleNotFoundError: No module named 'pyforge'`.
- The fallback puts `src/shared/packages/pyforge-marshal/src` on `sys.path` (`:54-60`) and imports again (`:61`). `scope.py:60` reads `except OSError, UnicodeDecodeError:` — the parenthesis-less form valid only from Python 3.14, written by `ruff format` under the package's py314 target in `6352cc067e` (2026-09-20) — so the import raises `SyntaxError: multiple exception types must be parenthesized`.

`--list` crashes the same way once a marker exists (`:207`). The switch (`cmd_switch`) and `--clear` never load the primitive and still run. The read verbs work only as `pixi run -e pyforge-guild python scripts/bmad-switch …`, which no document names.

**Approach:**
- `_load_verify_scope` reports a load failure instead of raising it: an `ImportError` or `SyntaxError` from both the installed import and the source-tree fallback is caught and returned as "not loadable" (the fallback order, and the Story 20.7 fixture fallback to the checkout the script sits in, are unchanged).
- `main()`, after parsing arguments and before any output, checks that the primitive loads for `--current` and `--list`. `<slug>` and `--clear` skip the check.
- When it does not load and the guard variable (for example `PYFORGE_BMAD_SWITCH_REEXEC`) is unset, the script re-executes itself exactly once: `pixi run --manifest-path <repo>/pixi.toml --frozen -e pyforge-guild python <this script> <original argv>`, with the guard set in the child's environment, and exits with the child's exit code. The child's stdout and stderr reach the caller unchanged.
- When `pixi` is not on `PATH` (`shutil.which`), or the guard is already set (the re-executed run still cannot load the primitive), the script exits 8 — the script's codes 1-7 are taken — with one stderr line naming the interpreter it ran under (`sys.executable` and its version), the requirement (Python 3.14 with `pyforge-marshal` importable) and the exact command `pixi run -e pyforge-guild python scripts/bmad-switch <argv>`.
- The module docstring's Usage names the requirement and the re-execution.

Ledger key: `69-1-the-switch-script-runs-where-it-is-documented-to-run`.
Ledger status (do not edit the ledger): `backlog`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-278 (FR-224).
- Kinship: `spec-pyforge-marshal` CAP-75..77 (the primitive and its hard fail, Stories 20.6 / 20.7, absorbed from `spec-bmad-switch-scope-enforcement`); CAP-201 (the worktree-aware switch, absorbed from `spec-multi-loop-isolation`).

## Acceptance Criteria

- Given the script loaded with `SourceFileLoader` and `_load_verify_scope`'s imports forced to fail, a fake `pixi` on `PATH` that records its argv and exits 0, and the guard unset When `main()` runs with `--current` Then the fake `pixi` is called once with `run --manifest-path <repo>/pixi.toml --frozen -e pyforge-guild python <script path> --current`, the child environment carries the guard, nothing was printed before the call, and `main()` returns the fake's exit code
- Given the same setup with the fake exiting 2 When `main()` runs with `--list` Then it returns 2 and the project table is not printed by the parent
- Given the imports forced to fail and no `pixi` on `PATH` When `main()` runs with `--current` Then it returns 8 and stderr is one line naming the running interpreter, the requirement and `pixi run -e pyforge-guild python scripts/bmad-switch --current`
- Given the imports forced to fail and the guard already set When `main()` runs with `--current` Then it returns 8 without calling `pixi`
- Given the imports forced to fail When `main()` runs with `<slug>` or `--clear` against a fixture tree Then `pixi` is never called and the verb behaves as today
- Given the primitive loads When `--current` runs Then no re-execution happens and the Story 20.7 behaviour is unchanged (`tests/scripts/test_bmad_switch_hard_fail.py` passes unchanged)
- Given the load-check removed from `main()` When the forced-failure `--current` case runs Then it raises instead of re-executing and the test fails (mutation)

## Boundaries & Constraints

**Always:** Implement only the Surface named in `epics.md` Story 69.1. Keep `pyforge.marshal.scope` the sole implementation of the scope check (CAP-76): the re-executed run calls the same `verify_scope`. Check the primitive before any output. Re-execute at most once. Keep every documented form working: `scripts/bmad-switch <slug>|--current|--list|--clear` and `pixi run -e pyforge-guild python scripts/bmad-switch …`.

**Never:**
- Do not rewrite `scope.py` into a Python 3.12-parseable form, or copy its check into the script.
- Do not change `cmd_switch`, `cmd_clear`, `repoint_links`, `ensure_tier3_backlink` or the marker-last ordering.
- Do not re-execute on any failure other than the primitive failing to load (a scope drift is exit 2, as today).
- Do not change `.claude/hooks/pre-shell.py` or `docs/governance/guild-roster.json`; the `bmad-switch-unsafe` denial already matches both forms.
- Do not run `scripts/bmad-switch` from a worktree or a parallel agent while testing; drive `main()` in-process against `tmp_path` fixtures.
- Do not hand-edit `sprint-status-ledger.yaml` or `SPEC.md`.

Co-governing Specs of `scripts/bmad-switch` in the spec-surface baseline: `spec-pyforge-marshal` (owner), `spec-bmad-switch-scope-enforcement` and `spec-multi-loop-isolation` (both absorbed into it) — reconcile each one the detector names.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Guild env | primitive loads | runs as today | as today (drift → exit 2) |
| system Python 3.12, `pixi` present | `--current` or `--list` | one re-execution under `-e pyforge-guild`; child's exit code | none |
| no `pixi` | `--current` or `--list` | exit 8, one stderr line naming the command | no traceback |
| re-executed run still fails | guard set | exit 8, one stderr line | never a second re-execution |
| switch or clear | `<slug>` / `--clear` under 3.12 | unchanged; no re-execution | as today |
| scope drift under the Guild env | desynced triangle | exit 2 naming the drift, as today | no re-execution |

</intent-contract>

## Source

Contract authored from the operator's 2026-09-28 direction and `docs/dreams/pyforge-marshal.md`'s 2026-09-28 entry under the bmad-switch-scope-enforcement fold (*the switch script runs where it is documented to run*), and `spec-pyforge-marshal` CAP-278 with its 2026-09-28 direction entry in the Spec's `.memlog.md` (the file:line evidence), decomposed the same session as Epic 69's mint.

## Binding

Parent Spec capability: `spec-pyforge-marshal` CAP-278 (FR-224).
Ledger key: `69-1-the-switch-script-runs-where-it-is-documented-to-run`.
Ledger status at mint: `backlog`.
Policy: `marshal-policy.toml` `[epic_surfaces]` `"69"` admits `scripts/bmad-switch` beside the default surface.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

**Manual checks:**
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass (`tests/scripts/test_bmad_switch_hard_fail.py` unchanged).
- On the primary checkout (never a worktree), `/usr/bin/python3 scripts/bmad-switch --current` prints the active project and exits 0 through the re-execution; with `pixi` removed from `PATH` it exits 8 with the one-line message.
