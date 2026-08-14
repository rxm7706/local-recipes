---
spec: bmad-drift-new-artifact-shape
status: shipped
owner-dream: docs/dreams/bmad-drift-new-artifact-shape.md
surface:
  - src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py
sources:
  - ../../../../../../docs/dreams/bmad-drift-new-artifact-shape.md
open_questions: []
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> to build, test, and validate. `docs/dreams/bmad-drift-new-artifact-shape.md` is listed in
> `sources:` for narrative rationale this contract intentionally omits.

# `bmad_drift`'s classifier has no rule yet for a spike-report artifact

## Why

A pain to solve. `pyforge.doctor.sources.factory` (Doctor's port of `scripts/bmad_drift_check.py`,
Story 6.8/FR-15) is the single verdict on whether `pyforge-marshal`'s tracked project docs are in
sync with the live factory. Its `check_coverage` walks the whole
`_bmad-output/projects/pyforge-marshal/` tree and HARD-fails any file `classify()` cannot name a
shape for -- `"not covered by drift-check — add a classification rule"`. That rule is
deliberately unforgiving by design: `classify()`'s own docstring calls an unclassified file "a
hole, not a pass," and its body is a dated sequence of hand-authored rules, each a git-reviewed
response to a *previous* file shape landing as `uncovered` -- fourteen files on 2026-07-28 when
the detector was retargeted onto the sharded station layout, eleven more shapes on 2026-08-08.

On 2026-08-11 (PR #427, Marshal Story 7.6) the same mechanism fired a third time.
`_bmad-output/projects/pyforge-marshal/planning-artifacts/spike-0-copier-api-fit-report.md` -- a
throwaway design-spike's PASS/FAIL verdict, written to the project's `planning-artifacts/` root
per that story's own `epics.md` `**Surface:**` line ("spike report in marshal planning-artifacts")
-- is a shape `classify()` has never seen: not `spec-*`, not under `specs/`, not one of the eleven
prior one-off carve-outs. It falls through to `UNKNOWN` and trips a HARD `uncovered` finding in
`pixi run -e local-recipes detectors-ci`. Marshal's own landing agent for that story confirmed the
fix belongs in Doctor's classifier, out of scope for a marshal-package landing, and left it red
rather than patch code out of turn.

## Capabilities

- **CAP-1**
  - **intent:** `classify()` recognizes the spike-report shape -- a file matching the
    "design-spike PASS/FAIL report written to a project's `planning-artifacts/` root" convention
    (e.g. `spike-0-copier-api-fit-report.md`) is classified rather than falling through to
    `UNKNOWN`, so `check_coverage` stops HARD-failing it as `uncovered`.
  - **success:** Re-running `check_coverage` against the live `pyforge-marshal` tree no longer
    reports `spike-0-copier-api-fit-report.md` (or a future report following the same naming
    convention) as `uncovered`; `pixi run -e local-recipes detectors-ci` is clean for `bmad-drift`.
- **CAP-2**
  - **intent:** The fix ships as one classification rule, added in the same place and the same
    dated-comment convention the file already uses for its prior 14-shape (2026-07-28) and
    11-shape (2026-08-08) additions -- no change to `check_coverage`'s fail-closed default for
    files the new rule genuinely does not match.
  - **success:** A file that still matches no rule at all -- including a spike-report look-alike
    that doesn't fit the agreed pattern -- still HARD-fails as `uncovered`, exactly as before.

## Constraints

- **Always:** `check_coverage`'s HARD-by-default posture is unchanged -- an unrecognized file is
  still a hole, not a pass. This widens the recognized set by exactly one shape; it is never a
  general auto-accept path for arbitrary new files.
- **Always:** the classifier's independence rule (never importing `pyforge.marshal` or any station
  package it judges) and its per-check isolation model are untouched by this work.

## Non-goals

- **Not** a redesign of `check_coverage`'s fail-closed philosophy or a general new-shape-tolerance
  mechanism -- one confirmed shape gets one confirmed rule, the same remedy every prior
  `uncovered` incident already used.
- **Not** an attempt to pre-empt every artifact shape a future BMAD effort might invent -- only to
  close the one shape confirmed live today.

## Success signal

Running `check_coverage` directly against the live `pyforge-marshal` project tree today returns
exactly one `uncovered` finding, for `planning-artifacts/spike-0-copier-api-fit-report.md`; every
other file the same story produced (including its sibling
`implementation-artifacts/spec-7-6-spike-0-copier-api-fit.md`) already matches an existing rule.
After the fix, re-running `check_coverage` against the same tree returns zero `uncovered`
findings, and `pixi run -e local-recipes detectors-ci` reports clean for `bmad-drift`.
