---
title: 'Story 3.4: The environment.yaml sync gate is one command away, not a remembered incantation'
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

**Problem:** This repo's own CLAUDE.md § "PR CI gates" documents an UNGATED sync check between `environment.yaml` and `pixi.toml` that every `pixi.toml`-touching PR must pass — today the operator has to remember `pixi project export conda-environment -e build` and diff it by hand.

**Approach:** `check_environment_sync` wraps the EXACT comparison `.github/workflows/scripts/linter.py` already runs on every PR (read `environment.yaml`, run `pixi project export conda-environment -e build`, compare both `.rstrip()`'d) — confirmed live by reading the linter script's own source (`.github/workflows/scripts/linter.py` lines 64-80) rather than re-deriving the comparison from CLAUDE.md's prose description (AD-1: reuse the SAME logic, never reimplement it a second, possibly-diverging way). Wired as `steward provision --verify`.

## Boundaries & Constraints

**Always:**
- The comparison is byte-for-byte identical to the linter's own: `environment.yaml`'s content and the `pixi project export conda-environment -e build` stdout are each `.rstrip()`'d, then compared for exact string equality — no normalization beyond what the linter itself does (no YAML re-parse, no semantic diff).
- `--verify` is a pure read — no write to `environment.yaml` or `pixi.toml` under any outcome, proven by a dedicated test.
- Exit code follows `DutyResult.ok` through `cli.main()`'s existing projection (AD-8) — clean is `ok=True`/exit 0, drift is `ok=False`/exit 1 (`EXIT_FAILED`), matching the AC's own "exits non-zero" wording exactly (`EXIT_FAILED` == 1, not some other non-zero code — this repo's own exit-code contract does not distinguish "drift" from any other duty-level failure by code, only by the printed summary text).

**Block If:** `environment.yaml` does not exist at the repo root, or the `pixi project export` subprocess itself fails — both propagate as duty-level failures, never silently read as "in sync."

**Never:**
- No second sync-comparison implementation anywhere in this package — `check_environment_sync` IS the comparison; there is no parallel/simplified version.
- No auto-fix — `--verify` reports drift, it never regenerates `environment.yaml` on the operator's behalf (out of this story's own AC scope; the fix command is named in the reported message, matching the linter's own hint text).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| `environment.yaml` in sync with `pixi.toml` | ordinary clean repo state | "in sync" report, exit 0 | No error |
| `pixi.toml` changed, `environment.yaml` not regenerated | drifted repo state | Drift report + unified diff, exit non-zero (`EXIT_FAILED`) | `DutyResult(ok=False, ...)` |
| `environment.yaml` missing entirely | corrupt/incomplete checkout | Clear error, never silently "in sync" | `DutyResult(ok=False, ...)` via `FileNotFoundError` |
| `pixi project export` itself fails (e.g. `-e build` no longer resolves) | broken `pixi.toml` | The export command's own stderr surfaces | `DutyResult(ok=False, ...)` via `subprocess.CalledProcessError` |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/provision.py` -- EDIT: `check_environment_sync`, `_run_verify`, `ProvisionDuty.run` gains the `--verify` branch (highest dispatch precedence)
- `src/shared/packages/pyforge-steward/src/pyforge/steward/cli.py` -- EDIT: `--verify` flag (declared alongside `--env`/`--runner`/`--list` in Story 3.1's `_add_provision_subparsers` edit)
- `src/shared/packages/pyforge-steward/tests/conformance/test_provision_verify.py` -- NEW: full I/O matrix, primitive + CLI level, incl. a read-only proof

## Tasks & Acceptance

**Execution:**
- [x] `provision.py` -- `check_environment_sync(*, cwd) -> tuple[bool, str]`
- [x] `provision.py` -- `_run_verify`; `ProvisionDuty.run` dispatches `--verify` (precedence: `--verify` > `--list` > `--runner` > `--env`, see Design Notes)
- [x] `cli.py` -- `--verify` flag
- [x] `tests/conformance/test_provision_verify.py` -- full matrix incl. `test_provision_verify_never_writes_environment_yaml`

**Acceptance Criteria:**
- Given the existing sync-gate check this repo's CI already enforces, when `steward provision --verify` is run against a repo state where `environment.yaml` is in sync with `pixi.toml`, then it reports clean and exits 0.
- Given a repo state where `pixi.toml` changed but `environment.yaml` was not regenerated, when `steward provision --verify` is run, then it reports drift and exits non-zero, wrapping the existing check's logic rather than reimplementing the comparison.

## Review Triage Log

### 2026-08-07 — Self-review (adversarial re-read before marking done)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- **Checked**: the `.rstrip()`-then-compare shape against the linter's own source line-by-line (`.github/workflows/scripts/linter.py:65-70`) rather than the CLAUDE.md prose summary — the docstring in `check_environment_sync` cites the exact line range read, so a future drift in the linter's own comparison logic is discoverable by re-reading that citation, not by re-deriving from memory.
- **Checked**: `test_check_environment_sync_ignores_trailing_whitespace_like_the_linter_does` proves the `.rstrip()` behavior by construction (extra trailing blank lines in the fixture `environment.yaml`) rather than trusting the docstring's claim on faith — mirrors this codebase's own `test_only_the_most_recent_dashboard_touching_commit_is_reported` precedent (spec-2-4) of proving an ordering/normalization claim by execution.
- **Checked**: dispatch precedence. `ProvisionDuty.run` checks `--verify` FIRST, before `--list`/`--runner`/`--env` — a documented judgment call (no AC defines combining flags), matching `DeployDuty`'s own `--build`-wins-over-`--dry-run` precedent for the identical "undefined combination, pick loudly" situation.
- **Checked**: `check_environment_sync` never opens `environment.yaml` for writing anywhere in its own body (`read_text` only) — confirmed by inspection, and independently proven by execution via `test_provision_verify_never_writes_environment_yaml`'s before/after byte comparison, in the DRIFT case specifically (the case most likely to tempt an auto-fix).

**Follow-up review recommendation: false** — a straightforward wrap of an already-existing, already-tested comparison; no new comparison semantics were invented.

## Design Notes

**Why the comparison is read from the linter's OWN source, not re-derived from CLAUDE.md's prose.** CLAUDE.md § "PR CI gates" describes the gate ("regenerate + commit `environment.yaml`... this sync check is UNGATED") but does not specify the EXACT comparison semantics (whitespace handling, which `pixi` subcommand, which `-e` flag). Re-deriving those details from prose risks a subtly different comparison that disagrees with CI on an edge case (e.g. trailing-newline sensitivity) — exactly the "reimplementing the comparison" AD-1 forbids. `.github/workflows/scripts/linter.py` IS the CI gate's own implementation; reading it directly and reusing its exact three-step recipe (read, export, `.rstrip()`-compare) is the only way to guarantee `steward provision --verify` and the real PR gate never disagree.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- expected: all tests pass
- `pixi run --frozen -e pyforge-steward steward provision --verify` -- expected: reports the real repo's actual sync state

**Results (2026-08-07):**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` -- 161 passed (full Epic 3 suite; this story's own share is `test_provision_verify.py`'s 9 tests).
- **Live verification (real, not faked):** `steward provision --verify` was run against this repo's REAL, checked-out `environment.yaml` and `pixi.toml` (this worktree's state, no `pixi.toml` edits made during this Epic 3 session) -- output: `provision --verify: environment.yaml is in sync with pixi.toml`, exit 0, matching this session's own `git status` (no `pixi.toml` changes in this session's diff, so the real gate correctly reports clean).
