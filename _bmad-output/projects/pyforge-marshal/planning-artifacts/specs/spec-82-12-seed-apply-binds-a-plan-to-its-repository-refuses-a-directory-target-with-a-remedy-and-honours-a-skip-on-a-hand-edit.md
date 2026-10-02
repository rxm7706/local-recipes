---
title: '82.12: Seed apply binds a plan to its repository, refuses a directory target with a remedy, and honours a skip on a hand-edit'
type: 'fix'
created: '2026-10-02'
status: 'backlog'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/deferred-work-ledger.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Three seed apply checks protect less than they claim. Re-verified at HEAD a7cdb91fe4:

- `seed/plan/types.py::RepoFingerprint` (`:220`) carries `git_head`, `dirty` and `artifact_hashes`, nothing naming the
  repository. For a non-git target `seed/plan/build.py::_git_head` and `_repo_is_dirty` (`:482-505`) degrade to the same
  `None` / `True` everywhere, so a plan built against directory A applies to directory B with zero drift from
  `fingerprint_drift` (`:681`) whenever B's actioned artifacts hash the same, most easily two empty greenfield directories
  (DW-10-3-7).
- Rung 5 of `seed/verbs/preconditions.py::check_preconditions` (`:651-671`) `lstat`s each target and refuses only a symlink;
  an existing directory falls through every rung, and apply then fails in `os.replace(tmp, target)` with an untyped
  `IsADirectoryError` outside the `SeedError` taxonomy, where every other refusal is a `PreconditionFailure` with exit 3 and
  a remedy (DW-10-4-5).
- `seed/verbs/skips.py::managed_after_skips` (`:359-385`) filters managed records by `plan.skipped`, which only an artifact
  with an action can enter (`apply_skips`, `:250-325`). A hand-edited `copied-managed` file classifies
  `PRESENT_CONFORMANT` and never gets an action, so `--skip <its path>` is a silent no-op and rung 6's only remaining
  override is `--force`, which discards every hand-edit. It is live now: `seed/verbs/adopt.py:1011` uses the helper, and
  `seed/verbs/update.py:1060` passes managed records to `check_preconditions` with no skip filter at all (DW-10-4-4).

**Approach:**

- `RepoFingerprint` gains the repository's identity (its resolved root, and its git common directory when it has one),
  recorded at plan build and serialized in `plan.json`; `fingerprint_drift` reports a mismatch against the apply target,
  and a `plan.json` without the field is refused with a re-plan remedy.
- Rung 5's `lstat` also refuses an existing directory at an action's target: a `PreconditionFailure` naming the target with
  a remedy (remove or rename the directory, or `--skip` the artifact), inside the existing six-rung order.
- `managed_after_skips` also drops managed records whose path matches a skip pattern the operator passed, so the skip
  reaches a file that never had an action; `adopt` and `update` both apply it before rung 6.

Ledger key: `82-12-seed-apply-binds-a-plan-to-its-repository-refuses-a-directory-target-with-a-remedy-and-honours-a-skip-on-a-hand-edit`.
Type / Effort / Deps: fix / M / 82.11.

### Living CAP citations

- `spec-pyforge-marshal` CAP-12 (adopt reviews exactly what will change) and CAP-15 (update without touching team work),
  with Story 9.6 (the repo fingerprint and `plan.json`), Story 10.3 (FR-83; P-04, P-07; AD-57) and Story 10.4 (FR-85,
  FR-86, FR-87). Defects of shipped behaviour, so no new CAP; no flag.

## Acceptance Criteria

- Given a plan built against an empty non-git directory A When it is applied to an empty non-git directory B Then `fingerprint_drift` names the repository mismatch and apply refuses
- Given a `plan.json` written before the repository field existed When apply reads it Then it refuses with a remedy to re-plan
- Given an action whose target path is an existing directory When `check_preconditions` runs Then it raises a `PreconditionFailure` with a non-blank remedy and exit code 3, and no write is attempted
- Given a hand-edited `copied-managed` file and `--skip` naming its path When `adopt` or `update` runs Then rung 6 does not refuse it and the edit is kept, without `--force`
- Given each fix reverted in turn When its new test runs Then it fails (mutation)

## Boundaries & Constraints

**Always:** Every refusal is a `PreconditionFailure` with a remedy. Rung 6 still checks every managed record a skip does
not name. Close DW-10-3-7, DW-10-4-5 and DW-10-4-4 in `deferred-work-ledger.md` when the story lands (status `closed`, a
`resolved:` line naming this story).

**Never:** Do not add a seventh rung or reorder the ladder. Do not weaken `--force`'s meaning. Do not touch the never-write
matching or manifest path validation (Story 82.11's surface) or opt-out handling (Story 82.13's).

</intent-contract>

## Binding

Parent: Stories 9.6, 10.3 and 10.4, `spec-pyforge-marshal` CAP-12 and CAP-15; a defect, no new CAP.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-02 entry.
Ledger key: `82-12-seed-apply-binds-a-plan-to-its-repository-refuses-a-directory-target-with-a-remedy-and-honours-a-skip-on-a-hand-edit`.
Ledger status at mint: `backlog`.
Deps: 82.11 (both edit `seed/verbs/preconditions.py`).
Closes: DW-10-3-7, DW-10-4-5, DW-10-4-4.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).

## Review Triage Log

- No review has run yet.
