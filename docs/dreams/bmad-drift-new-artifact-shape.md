---
title: A spike report is not a corrupt file, and the classifier can't yet tell the difference
type: dream
owner: doctor
status: realized
---

# A spike report is not a corrupt file, and the classifier can't yet tell the difference

## The Dream

`pyforge.doctor.sources.factory` (Doctor's port of `scripts/bmad_drift_check.py`, Story
6.8/FR-15) is the single verdict on whether `pyforge-marshal`'s own tracked project docs are
in sync with the live factory. Its `check_coverage` walks the whole
`_bmad-output/projects/pyforge-marshal/` tree and HARD-fails any file `classify()` cannot
name a shape for — "not covered by drift-check — add a classification rule." That rule is
deliberately unforgiving: `classify()`'s own docstring calls an unclassified file "a hole,
not a pass," and the function's body is a long, dated sequence of hand-authored `re.fullmatch`
blocks, each one a git-reviewed response to a *previous* file shape landing as `uncovered` —
fourteen files on 2026-07-28 when the detector was retargeted onto the sharded station
layout, eleven more shapes on 2026-08-08. The mechanism works exactly as designed: a new
shape goes red, a human reviews it, a rule is added, the shape is now covered forever.

On 2026-08-11 (PR #427, Marshal Story 7.6) that mechanism fired a third time.
`_bmad-output/projects/pyforge-marshal/planning-artifacts/spike-0-copier-api-fit-report.md`
— a throwaway design-spike's PASS/FAIL verdict, written straight to the project's
`planning-artifacts/` root because the story's own epics.md `**Surface:**` line said so
("spike report in marshal planning-artifacts") — is a shape `classify()` has never seen:
not `spec-*` (the tracked-spec pattern), not under `specs/`, not one of the eleven prior
one-off carve-outs. It falls through every rule to `UNKNOWN` and trips a HARD `uncovered`
finding in `pixi run -e local-recipes detectors-ci`. The landing agent for that story
confirmed the fix belongs in Doctor's classifier, not in a marshal-package landing, and left
it as CI-red rather than patch code out of scope for that PR.

Running `check_coverage` directly against the live tree confirms the shape is real but
narrow: exactly one file trips it today. Nothing else under `pyforge-marshal`'s tree —
including the sibling spec file `implementation-artifacts/spec-7-6-spike-0-copier-api-fit.md`
that the same story also wrote, which matches the existing `tracked:spec` rule cleanly — is
affected. The naming choice "Spike-0" (epics.md, Story 7.6) leaves open that a Spike-1 could
follow a future Marshal story and repeat the identical shape.

## What it looks like when real

- `classify()` has a rule for the bare "spike report written to `planning-artifacts/` root"
  shape (however precisely scoped — literally `spike-*-report.md`, or a slightly wider
  pattern if the Spec's own research finds one — that is a decomposition-time decision, not
  settled here), so the 2026-08-11 file — and any future Spike-*N* report following the same
  convention — is covered rather than HARD-failing `detectors-ci`.
- The fix is exactly what the last two "shapes that landed as uncovered" incidents already
  were: one small, explicit, git-reviewed classification rule, added the same way, in the
  same function, with the same dated-comment convention the file already uses. Nothing about
  `check_coverage`'s fail-closed default changes — an honestly unrecognized file still HARD
  fails; this closes one specific, now-identified hole in what "recognized" already covers.
- `pixi run -e local-recipes detectors-ci` reports clean for `bmad-drift` again without
  anyone having silently widened the classifier's tolerance for genuinely unexpected files.

## Constraints

- This is a narrow gap-fill for one identified, confirmed shape — not a redesign of
  `check_coverage`'s HARD-by-default posture, and not a general "auto-accept new shapes"
  mechanism. The existing rule that an unrecognized file is a hole, not a pass, stays intact;
  only the recognized set grows.
- No implementation detail is prescribed here — not the exact regex, not whether the rule
  folds into the existing spike-adjacent carve-outs or stands alone, not whether it should
  also anticipate a `Spike-1` before one exists. That is for the Spec and its downstream story.
- This Dream does not extend to the classifier's independence rule (never importing
  `pyforge.marshal`, per the module's own docstring) or its per-check isolation model —
  both stay exactly as they are.

## Realization log

- **2026-08-11** — Captured after `pixi run -e local-recipes detectors-ci` reported one
  `bmad-drift` `uncovered` HARD finding for
  `_bmad-output/projects/pyforge-marshal/planning-artifacts/spike-0-copier-api-fit-report.md`,
  landed by PR #427 (Marshal Story 7.6, the Copier API-fit spike). Marshal's own landing
  agent confirmed the fix belongs in `pyforge.doctor.sources.factory::classify`, out of
  scope for a marshal-package PR, and left it red rather than patch it out of turn. Verified
  by running `check_coverage` directly against the live tree: exactly one file trips it;
  every other file the same story wrote (including its sibling
  `implementation-artifacts/spec-7-6-spike-0-copier-api-fit.md`) already matches an existing
  rule. Queued as a Dream rather than patched by hand, per the operator's standing decision
  (the same treatment as Story 5.8) to route this class of gap through the Dream/Spec/story
  chain instead of a same-session classifier edit — `factory.py`'s `classify()` was
  deliberately left untouched pending the Spec/story.
- **2026-08-14** — Realized — Story 6.11's implementation (commit `c9e59028ff`, stranded on its loop branch by a destructive rearm reset) landed via PR #491; the classifier recognizes the spike-report shape and the SPEC flipped to shipped in the same merge. Status flipped by the 2026-08-14 dream-backlog chain audit.
