---
title: 'Story 3.1: Any named pixi environment materializes with one command'
type: 'feature'
created: '2026-08-07'
status: 'done'
review_loop_iteration: 1
followup_review_recommended: false
context: []
warnings: []
---

<intent-contract>

## Intent

**Problem:** An operator materializing any of this repo's ~19 pixi environments has to remember exact `pixi install -e <name>` syntax and the valid environment name — there is no Steward-level surface for it.

**Approach:** New `provision.py` module (mirrors `deploy.py`'s "one module per duty" precedent). `load_pixi_environments` parses `pixi.toml`'s `[environments]` table read-only (via stdlib `tomllib` — no new dependency), handling both the shorthand list shape and the explicit `{ features = [...] }` table shape. `materialize_environment` is a thin `pixi install -e <name>` subprocess wrap (AD-1/AD-5 — no reimplemented pixi resolution logic). Wired as `steward provision --env <name>`.

## Boundaries & Constraints

**Always:**
- `--env <name>` is validated against `pixi.toml`'s own `[environments]` table BEFORE any subprocess call — an unknown name never reaches `pixi`, so the operator never sees pixi's own raw error for a typo.
- The only mutation possible is `pixi install`'s own effect on `.pixi/envs/` — Steward never writes to `pixi.toml` itself (AD-5).
- `repo_root()` walks up from `provision.py`'s own file location looking for `scripts/bmad-loop-worktree`, NOT `pixi.toml` — this package ships its own, unrelated `pixi.toml` (`src/shared/packages/pyforge-steward/pixi.toml`, the pixi-build-python member manifest) at a shallower directory than the true repo root; a naive `pixi.toml`-keyed walk-up would resolve to the WRONG file and silently read an empty `[environments]` table.

**Block If:** `name` is not a key in `pixi.toml`'s `[environments]` table — report the full valid-name list, never a raw `pixi` invocation.

**Never:**
- No re-derivation of what packages/deps an environment resolves to — that stays entirely `pixi`'s own job.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| A real environment name | `--env pyforge-atlas` | `pixi install -e pyforge-atlas` runs; environment materializes | No error |
| An unknown environment name | `--env not-a-real-env` | Clear error naming valid environments; `pixi` never invoked | `DutyResult(ok=False, ...)` |
| Steward's own dogfooding target | `--env pyforge-steward` | Materializes successfully (live-verified) | No error |
| `pixi install` itself fails | e.g. disk full, network down | `subprocess.CalledProcessError` -> named, quoted failure | `DutyResult(ok=False, ...)` |
| `pixi.toml` missing at repo root | corrupt checkout | `FileNotFoundError` propagated | `DutyResult(ok=False, ...)` |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py` -- NEW: `repo_root`, `load_pixi_environments`, `materialize_environment`, `_run_env`, `ProvisionDuty`
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- EDIT: `_add_provision_subparsers` (`--env`/`--runner`/`--list`/`--json`/`--verify` flags — all four Epic 3 stories share one flag set on the bare `provision` parser), `resolve_duty("provision")` now returns real `ProvisionDuty`
- `src/shared/packages/pyforge-steward/tests/conformance/test_provision_env.py` -- NEW: full I/O matrix, primitive + CLI level

## Tasks & Acceptance

**Execution:**
- [x] `provision.py` -- `repo_root()` (marker: `scripts/bmad-loop-worktree`, NOT `pixi.toml`)
- [x] `provision.py` -- `load_pixi_environments(*, cwd) -> dict[str, tuple[str, ...]]`
- [x] `provision.py` -- `materialize_environment(name, *, cwd) -> subprocess.CompletedProcess`
- [x] `provision.py` -- `_run_env`, `ProvisionDuty.run` dispatching `--env`
- [x] `cli.py` -- `--env` flag on the `provision` duty parser
- [x] `tests/conformance/test_provision_env.py` -- full matrix

**Acceptance Criteria:**
- Given repo-root `pixi.toml`'s `[environments]` table, when `steward provision --env pyforge-atlas` is run, then it shells out to `pixi install -e pyforge-atlas` (AD-5) and the environment materializes successfully.
- Given a name that does not exist in the `[environments]` table, when `steward provision --env not-a-real-env` is run, then it reports a clear error listing valid environment names, rather than passing the bad name through to pixi.
- Given this story's own dogfooding target, when `steward provision --env pyforge-steward` is run, then it successfully materializes Steward's own dev/test environment.

## Review Triage Log

### 2026-08-07 — Self-review (adversarial re-read before marking done)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- **Checked**: subprocess argument construction. `["pixi", "install", "-e", name]` — no `shell=True` anywhere in this module (matches `deploy.py`/`keys.py`'s existing convention). `name` is passed as a discrete list element, so there is no shell-metacharacter injection surface regardless of its content.
- **Checked**: a `name` value shaped like a flag (e.g. `--env=--foo`) cannot reach the `pixi` subprocess at all — it is rejected by the `name not in environments` gate FIRST, and no real `pixi.toml` environment name is flag-shaped, so this can't happen for any valid input either.
- **Checked**: exception handling doesn't swallow the wrong thing — `_run_env` lets `subprocess.CalledProcessError`, `FileNotFoundError` (missing `pixi.toml`), and `tomllib.TOMLDecodeError` (a `ValueError` subclass, propagated uncaught by design — a malformed manifest should crash loud, not silently read as "no environments") all propagate to `ProvisionDuty.run`'s single `try`/`except`, mirroring `DeployDuty.run`'s identical centralized-catch shape.
- **Checked**: `repo_root()`'s marker choice against the exact failure it exists to avoid — confirmed live that `src/shared/packages/pyforge-steward/pixi.toml` exists and has NO `[environments]` table; a naive walk-up keyed on `pixi.toml` would have silently resolved to it first and reported "no environments found" for every `--list`/`--env` call. `scripts/bmad-loop-worktree` is confirmed (via `find`) to exist exactly once in this repo, at the true root.
- **Real finding, fixed during implementation**: the initial `ProvisionDuty.run` caught `RuntimeError`/`FileNotFoundError` centrally but NOT `tomllib.TOMLDecodeError` (a `ValueError` subclass) — a malformed `pixi.toml` would have propagated all the way to `cli.main()`'s generic `except Exception`, reporting `EXIT_INTERNAL` (a Steward-internal crash) for what is really an ordinary bad-input condition, inconsistent with `KeysDuty`'s own precedent of catching a malformed-input parse error (`scan_file`'s `SyntaxError`) as a duty-level failure, not a crash. Fixed: `tomllib.TOMLDecodeError` added to the centralized catch. New test: `test_provision_env_malformed_pixi_toml_is_a_duty_failure_not_a_crash`.

**Follow-up review recommendation: false** — both the marker-ambiguity risk and the malformed-manifest exception-class gap were caught and fixed during this same implementation pass, each with a dedicated test.

## Design Notes

**Why `tomllib`, not a new dependency.** `pyproject.toml` already declares `requires-python = ">=3.12"`; `tomllib` is stdlib since 3.11. Parsing `pixi.toml`'s `[environments]` table needed no new dependency at all (Simplicity First) — `keys.py`'s own `test_no_cli_framework_dependency` meta test already establishes the precedent of scanning the manifest's declared dependencies, so an unnecessary new one would be flagged as friction, not caught as a defect.

**Why the repo-root marker is `scripts/bmad-loop-worktree`, not `pixi.toml`.** Confirmed live: this package ships its OWN `pixi.toml` (`src/shared/packages/pyforge-steward/pixi.toml`, the pixi-build-python member manifest — no `[workspace]` or `[environments]` table, by its own header comment). Walking up from `provision.py`'s own file location (`.../pyforge-steward/src/pyforge/steward/provision.py`) hits that file FIRST, several directories before the true repo root. `scripts/bmad-loop-worktree` is a marker this exact duty already needs for Story 3.2, and it exists exactly once, at the true root — reusing it avoids a second, redundant walk-up and the exact wrong-file bug a naive `pixi.toml` marker would have introduced.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- expected: all tests pass
- `pixi run --frozen -e pyforge-steward steward provision --env pyforge-steward` -- expected: materializes Steward's own env

**Results (2026-08-07):**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- 161 passed (122 pre-Epic-3 baseline + 39 new across all four Epic 3 stories, this story's own share is `test_provision_env.py`'s 13 tests).
- **Live verification (real, not faked):** `pixi run --frozen -e pyforge-steward steward provision --env pyforge-steward` was run against the REAL repo-root `pixi.toml` and the REAL `pixi` binary — output: `provision --env: 'pyforge-steward' materialized (pixi install -e pyforge-steward)`, exit 0. Also run live: `steward provision --env not-a-real-env` (real error path) -- output named all 19 real environment names and exited 1, `pixi` never invoked (confirmed by the absence of any pixi solve/download output in the transcript).
