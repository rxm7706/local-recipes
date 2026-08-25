---
title: 'Consume the sprint ledger; never derive story status'
type: 'feature'
created: '2026-08-09'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: ['oversized']
baseline_revision: 'c09088a6e6e3ae6ab8d9923dcb7df61a18052fa0'
final_revision: 'c0c66f86daccf383ab628230d7130852c73eba76'
---

<intent-contract>

## Intent

**Problem:** `steward deploy dashboard` (`deploy.py::build_dashboard`) triggers a full
`docs/dashboard/` rebuild with no precondition on Steward's own tracked
`sprint-status-ledger.yaml`. Per AD-71, Marshal produces that ledger and owns its
currency; Steward must only ever publish what it says, never invent a fallback when it
can't be read — today nothing checks the ledger exists before building, so a missing or
unreadable ledger is silently invisible rather than a named refusal.

**Approach:** Add a precondition guard to `deploy.py`'s `dashboard` verb: before
`build_dashboard()` runs, resolve Steward's own tracked ledger
(`_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`,
by physical path, never through the `_bmad-output/planning-artifacts` symlink) and
refuse with a named `DutyResult(ok=False, ...)` if it is missing, unreadable, or not
shaped like a ledger. The guard only ever checks the file's *presence and shape* — it
never reads or compares individual story-status values, so `deploy.py` still performs
zero status derivation of its own (AD-1: wrap, never reimplement — the actual status
computation stays inside the wrapped `dashboard-gen` subprocess). Pin that invariant
with a structural (AST-based) test, matching this package's existing
`tests/meta/test_invariants.py` precedent.

## Boundaries & Constraints

**Always:**
- The refusal check runs for the `dashboard` verb only (`--build`, `--dry-run`, and the
  bare reconcile path all go through `_run_dashboard`), before `build_dashboard()` is
  invoked. The `status` verb (`_run_status`) is unaffected — it never builds/publishes.
- The check reads only enough of the ledger file to confirm it exists, is readable, and
  contains a `development_status:` block — never an individual story key or status
  value. No new dependency on `yaml`/`re`/any parsing library.
- Use the ledger's physical path
  (`_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`
  relative to `repo_root()`), never the `_bmad-output/planning-artifacts` symlink target
  (that symlink is per-worktree global state and may point at a different project).
- `build_dashboard()` itself and the underlying `dashboard-gen` pixi task are unchanged
  — AD-1 forbids `deploy.py` from reimplementing `pyforge.doctor.sources.fleet_scan`'s own
  ledger-consumption logic; this story only adds a presence/shape precondition in front
  of the existing wrap.
- Existing conformance tests that drive `deploy dashboard` through a scratch git repo
  (`test_deploy_build.py`, `test_deploy_reconcile.py`, `test_deploy_dry_run.py`) must
  keep passing — update their fixtures to write a minimal valid ledger file so the new
  guard doesn't false-refuse the happy path they're testing.

**Block If:** Nothing identified — the change is additive and scoped to `deploy.py`
plus its existing test fixtures; no ambiguity requires a human decision.

**Never:**
- Never modify `pyforge.doctor.sources.fleet_scan` (repo-wide, shared by all 8 stations; out
  of this story's declared Surface and far beyond XS effort).
- Never add branching logic in `deploy.py` on any story-status vocabulary value
  (`done`, `in-progress`, `backlog`, `blocked`, `pending`, `active`, `gated`) — that
  would itself be the re-derivation this story exists to prevent.
- Never gate the `status` verb on the ledger — FR-11 already governs it separately and
  the AC scopes this to the `dashboard` verb.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Ledger present and valid | tracked ledger file exists, contains `development_status:` | `_run_dashboard` proceeds to `build_dashboard()` as today | No error expected |
| Ledger missing | no file at the tracked ledger path | `DeployDuty.run` returns `DutyResult(ok=False, ...)` naming the missing path; `build_dashboard()` never called | Named refusal, not a silent fallback |
| Ledger present but empty/malformed | file exists, no `development_status:` block | Same named refusal as missing; `build_dashboard()` never called | Named refusal, not a silent fallback |
| `--build`-only with a bad ledger | `steward deploy dashboard --build`, ledger missing | Refused before the build subprocess runs (no partial build) | Named refusal |
| `--dry-run` with a bad ledger | `steward deploy dashboard --dry-run`, ledger missing | Refused before the build subprocess runs; git state untouched | Named refusal |
| `deploy status` with a bad/missing ledger | `steward deploy status`, ledger missing | Unaffected — reports last commit as today (ledger check does not apply to `status`) | No error expected |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-steward/src/pyforge/steward/deploy.py` -- add the ledger
  presence/shape guard and wire it into `_run_dashboard` before `build_dashboard()`.
- `src/shared/packages/pyforge-steward/tests/conformance/test_deploy_build.py` -- update
  the two CLI round-trip tests to write a minimal ledger fixture under the mocked
  `repo_root()` before calling `main(...)`.
- `src/shared/packages/pyforge-steward/tests/conformance/test_deploy_reconcile.py` --
  update `_make_repo_with_origin` to also write the ledger fixture (shared by every
  test in the file; harmless no-op for the tests that call the git primitives directly
  rather than through the CLI).
- `src/shared/packages/pyforge-steward/tests/conformance/test_deploy_dry_run.py` --
  update its own `_make_repo_with_origin` copy the same way.
- `src/shared/packages/pyforge-steward/tests/conformance/test_deploy_ledger_refusal.py`
  (new) -- behavioral coverage of the I/O matrix's refusal rows.
- `src/shared/packages/pyforge-steward/tests/meta/test_invariants.py` -- add the
  AST-based "no story-status derivation in `deploy.py`" structural test (AC's third
  bullet), matching this file's existing `test_no_rotation_scheduler_exists`-style
  precedent.

## Tasks & Acceptance

**Execution:**
- [x] `deploy.py` -- add `_STEWARD_LEDGER_RELATIVE_PATH` constant
  (`_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml`)
  and a `_tracked_ledger_refusal(*, cwd) -> str | None` helper that returns a refusal
  message (missing file / unreadable / no `development_status:` block) or `None` --
  wraps the CI-safe pattern already used for the `pyforge.doctor.sources.fleet_scan` marker.
- [x] `deploy.py` -- call `_tracked_ledger_refusal(cwd=root)` at the top of
  `_run_dashboard`, before `build_dashboard()`; on a non-`None` result return
  `DutyResult(ok=False, summary=f"deploy dashboard: refused — {refusal}")` immediately.
- [x] `test_deploy_build.py` -- write a valid ledger fixture into the mocked
  `repo_root()` (`tmp_path`) in `test_deploy_dashboard_build_via_cli_round_trips` and
  `test_deploy_dashboard_build_surfaces_a_task_failure_as_exit_failed`.
- [x] `test_deploy_reconcile.py` -- extend `_make_repo_with_origin` to also write the
  ledger fixture under `work`.
- [x] `test_deploy_dry_run.py` -- extend its own `_make_repo_with_origin` copy the same
  way.
- [x] `test_deploy_ledger_refusal.py` (new) -- cover: missing ledger refuses;
  empty/malformed ledger refuses; valid ledger proceeds (asserting `build_dashboard` is
  reached, e.g. via a fixture command that writes a marker file); refusal applies to
  `--build` and `--dry-run` too; `deploy status` is unaffected by a missing ledger.
- [x] `test_invariants.py` -- add `test_deploy_has_no_story_status_derivation`: AST-parse
  `deploy.py`, assert no `import re`/`import yaml` and no `ast.Compare` against any
  story-status vocabulary string literal (`done`, `in-progress`, `backlog`, `blocked`,
  `pending`, `active`, `gated`).

**Acceptance Criteria:**
- Given a tracked, valid `sprint-status-ledger.yaml`, when `steward deploy dashboard`
  runs (bare, `--build`, or `--dry-run`), then it proceeds to `build_dashboard()`
  unchanged from today's behavior.
- Given the tracked ledger is missing or unreadable, when `steward deploy dashboard`
  runs (any flag combination), then `DeployDuty.run` returns `ok=False` with a summary
  naming the refusal and the checked path, and `build_dashboard()` is never invoked.
- Given the tracked ledger is missing, when `steward deploy status` runs, then behavior
  is unchanged (the ledger check does not apply to the `status` verb).
- Given `deploy.py`'s source, when parsed as an AST, then it contains no import of
  `re`/`yaml` and no comparison against any story-status vocabulary literal.

## Spec Change Log

## Review Triage Log

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 2, medium 3, low 0)
- defer: 1: (medium 1)
- reject: 8: (low 8)
- addressed_findings:
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independently, both reproduced): `_tracked_ledger_refusal`'s shape check was a bare substring test (`"development_status:" in text`), satisfied by a comment merely mentioning the key or any longer identifier ending in it — while the real consumer (`generate.py::parse_sprint_status`) only recognizes a line whose stripped text equals `development_status:` exactly. A malformed ledger could pass this guard and still parse to zero statuses downstream (empirically reproduced both ways). Fixed to the same line-exact match; pinned by a new test using the reviewer's exact repro content, plus a cross-check against the real `parse_sprint_status` confirming they now agree.
  - `[high]` `[patch]` Blind Hunter + Edge Case Hunter (independently): `except OSError` does not catch `UnicodeDecodeError` (its MRO is `UnicodeError → ValueError → Exception`), so a ledger with invalid-encoding content would crash uncaught instead of producing the promised named refusal. Fixed to `except (OSError, UnicodeDecodeError)`.
  - `[medium]` `[patch]` Blind Hunter + Edge Case Hunter (independently): the new `except OSError` refusal branch had zero test coverage. Added `test_unreadable_ledger_refuses_before_build` (permission-denied via `chmod 0o000`, skips gracefully if running as root).
  - `[medium]` `[patch]` Blind Hunter: every happy-path fixture wrote a bare `development_status:\n` with no entries or comment preamble, unlike the real tracked ledger's multi-line `#`-comment header. Added `test_ledger_with_a_realistic_comment_header_proceeds_to_build` using the real file's actual header shape.
  - `[low]` `[patch]` Blind Hunter: the ledger's relative-path string was duplicated across 5 files with no single source of truth. All four test files now import `_STEWARD_LEDGER_RELATIVE_PATH` from `pyforge.steward.deploy` instead of re-declaring the literal.
  - `[medium]` `[defer]` Blind Hunter: the guard only covers `steward deploy dashboard` (manual/local path) — the actually-published GitHub Pages dashboard is built by `.github/workflows/dashboard.yml` running `generate.py --source git` directly, which never invokes `steward` and still silently continues past a missing ledger. Out of this story's declared Surface (`deploy.py`, `tests/` only; closing it needs `pyforge.doctor.sources.fleet_scan`, repo-wide/shared by 7 other stations). Logged to `deferred-work.md`.
  - `[low]` `[reject]` Blind Hunter + Edge Case Hunter (both, different framings): the AST invariant test only forecloses `ast.Compare`-against-literal and a fixed import denylist — a dict/lookup-table, `match/case`, or an unlisted parsing library could still derive status undetected. Matches this file's existing precedent tests' rigor exactly (also finite import denylists / single-pattern AST checks); expanding indefinitely against every possible circumvention has no natural stopping point.
  - `[low]` `[reject]` Blind Hunter: three "missing ledger refuses" tests look similar but each exercises a genuinely distinct code path (bare, `--build`, `--dry-run`) downstream of the same guard call — not redundant.
  - `[low]` `[reject]` Blind Hunter: refusal-message path formatting untested for symlinks/long worktree paths — speculative, no identified failure mode beyond `Path.__str__` behaving as documented.
  - `[low]` `[reject]` Blind Hunter: module docstring "overstates" the guarantee — resolved as a side effect of the two high-severity patches above; no separate wording change needed.
  - `[low]` `[reject]` Blind Hunter: sparse/partial checkout (generate.py present, `_bmad-output/projects/pyforge-steward/planning-artifacts/` absent) — already correctly handled by `ledger.is_file()` returning `False`; same refusal as "genuinely missing," which is the intended behavior, not a gap.

## Design Notes

`_tracked_ledger_refusal` returns `str | None` rather than raising a new exception
type, mirroring `dashboard_id_to_status`-style optional-return helpers elsewhere in
this codebase and avoiding an extra exception class for a single call site. Example:

```python
_STEWARD_LEDGER_RELATIVE_PATH = Path(
    "_bmad-output/projects/pyforge-steward/planning-artifacts/sprint-status-ledger.yaml"
)


def _tracked_ledger_refusal(*, cwd: str | Path) -> str | None:
    ledger = Path(cwd) / _STEWARD_LEDGER_RELATIVE_PATH
    if not ledger.is_file():
        return f"tracked ledger not found at {ledger}"
    try:
        text = ledger.read_text(encoding="utf-8")
    except OSError as exc:
        return f"tracked ledger unreadable at {ledger}: {exc}"
    if "development_status:" not in text:
        return f"tracked ledger at {ledger} has no development_status: block"
    return None
```

`_run_dashboard` calls this first and returns a named `DutyResult(ok=False, ...)` on a
non-`None` result, before `build_dashboard()` runs -- the same "refuse before any
write" shape `commit_and_push_dashboard` already uses for a detached HEAD.

## Verification

**Commands:**
- `pixi run -e pyforge-steward pyforge-steward-test` -- expected: full suite green,
  including the new/updated `deploy` conformance tests and the new meta invariant.

## Auto Run Result

- **Summary:** `steward deploy dashboard` now refuses (named `DutyResult(ok=False,
  ...)`, never a silent fallback) before `build_dashboard()` runs, whenever
  Steward's own tracked `sprint-status-ledger.yaml` is missing, unreadable, or not
  shaped like a ledger -- covering the bare, `--build`, and `--dry-run` paths alike.
  `deploy status` is unaffected. `deploy.py` performs zero story-status derivation of
  its own (AD-1); the guard only checks presence/shape via a line-exact
  `development_status:` match, matching `generate.py::parse_sprint_status`'s own
  detection, and is pinned by a new AST-based structural test. Landed in commit
  `1039c6201b` (dev attempt 1).
- **Repair pass (dev attempt 2):** dev attempt 1's own deterministic verify passed
  (`pixi run -e pyforge-steward pyforge-steward-test`) but the repo-wide
  `python scripts/spec_surface_check.py` gate (wired into this station's verify
  commands by marshal 13.7 specifically to catch this) failed: the 6 files attempt 1
  touched are governed by the project-level `pyforge-steward/spec-pyforge-steward`
  Spec, and that Spec's `.memlog.md` never named them, so the detector reported
  `[drift]` on all 6. Reconciled by appending a `(change)` entry to
  `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`
  naming all 6 paths, then `python scripts/spec_surface_check.py --write-baseline
  --spec pyforge-steward/spec-pyforge-steward` (scoped, per the detector's own
  documented remedy -- never an unscoped stamp, which would launder every other
  spec's pending drift). No code change, no `<intent-contract>` change. Landed in
  commit `c0c66f86`.
- **Files changed (repair pass):**
  - `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/.memlog.md`
    -- new `(change)` entry naming the 6 governed paths from Story 5.2.
  - `scripts/.spec-surface-baseline.json` -- re-stamped, scoped to
    `pyforge-steward/spec-pyforge-steward` only.
- **Review findings breakdown:** unchanged from dev attempt 1's pass (5 patch, 1
  defer, 8 reject -- see `## Review Triage Log` above); the repair pass touched only
  spec-governance bookkeeping, not application code, so no new adversarial review
  was run against it.
- **Follow-up review recommendation:** `false` -- bookkeeping-only reconciliation, no
  behavior change.
- **Verification performed:** `pixi run -e pyforge-steward pyforge-steward-test` --
  208 passed. `python scripts/spec_surface_check.py` -- exit 0, "OK: every tracked
  file governed or allowlisted; no drift."
- **Residual risks:** none identified for this repair. The dev-attempt-1 deferred
  item stands: the CI-published dashboard path (`.github/workflows/dashboard.yml`
  running `generate.py --source git` directly) has no equivalent ledger guard --
  out of this story's declared `deploy.py`-only Surface, logged to
  `deferred-work.md`.

