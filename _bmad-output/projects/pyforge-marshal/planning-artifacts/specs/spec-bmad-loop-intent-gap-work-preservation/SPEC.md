---
spec: bmad-loop-intent-gap-work-preservation
status: ready
owner-dream: docs/dreams/bmad-loop-intent-gap-work-preservation.md
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/harness_bmadloop.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/
sources:
  - ../../../../../../docs/dreams/bmad-loop-intent-gap-work-preservation.md
open_questions:
  - "Interception point (a story-level design decision, not resolved by the Dream): whether the adapter seam can observe the attempt before bmad_loop's internal revert executes, or whether Marshal must snapshot proactively (supervisor-side) so the preserve artifact exists by the time the revert fires -- the revert itself runs inside the unowned package."
  - "Selectivity: whether an intent gap surfaced during DEV (no adversarial-review prompts in the transcript, so no accidental recovery path at all) is distinguishable at the seam from an ordinary retry revert -- determines if preservation can target intent-gap halts specifically or must cover every revert to be safe."
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> to build, test, and validate. `docs/dreams/bmad-loop-intent-gap-work-preservation.md` is
> listed in `sources:` for narrative rationale this contract intentionally omits.

# `bmad-loop`'s intent-gap revert leaves no recoverable git artifact

## Why

A pain to solve. When a `bmad-loop` dev session halts on an **intent_gap** -- a contradiction
inside the story's own `<intent-contract>` that the workflow may never silently patch around --
it correctly reverts the attempt. But that revert leaves **no recoverable git artifact**: no
`attempt-preserve/*` branch, no `failed/<story>/changes.patch`, a clean reflog. This is a
deliberate asymmetry with the deferred-story path, where `engine.py`'s
`_preserve_attempt_commits` / `_preserve_attempt_worktree` (via `_rollback_or_pause`,
`scm.keep_failed`) already park every timed-out or deferred attempt -- the safety net this repo
leaned on repeatedly in the 2026-08-14 baseline-drift recoveries. The intent-gap path is the ONE
story-halting flow that never got this treatment.

The live occurrence (2026-08-14): marshal Story 10.1 (*Copier engine wrapper -- the single
seam*) implemented `seed/engine/copier.py` in full, passed the entire `pyforge-marshal` suite
(3646 tests) plus two adversarial reviews, then correctly halted on a real contradiction in its
own contract (the `never_write` Boundaries rule vs. two already-shipped manifest entries FR-74
needs). The revert left the worktree "confirmed clean, matching `baseline_revision`" -- nothing
to fetch, nothing to `merge-base` against. The work was recovered byte-identical (PR #486) only
because the adversarial-review Agent prompts happened to embed the full diff and every new
file's content in the dev session's Claude Code transcript -- a fragile accident that depends on
the review step having run at all, on locating the right `~/.claude/projects/**/*.jsonl`, and on
it still existing on disk. The escalation's own text already concedes the point ("re-implementing
from scratch should not be necessary"): the workflow knows the work shouldn't be thrown away; it
just doesn't act on that knowledge with a durable artifact.

## Capabilities

- **CAP-1**
  - **intent:** Preservation symmetry -- before/around an intent-gap revert discards tracked
    changes, Marshal-side compensation at the adapter seam parks the attempt exactly the way the
    deferred-story path already does: an `attempt-preserve/*` branch when there are real
    commits, a `failed/<story>/changes.patch` when there aren't. No edit to `bmad_loop` itself.
  - **success:** After an intent-gap halt on a story with tracked changes, a preserve artifact
    exists in the loop home's git (branch or patch) whose content matches the reverted attempt;
    the worktree is still reverted clean per protocol.
- **CAP-2**
  - **intent:** The escalation surface names the artifact -- the "Auto Run Result" / escalation
    text, which already spells out the recommended contract fix in detail, ALSO names the exact
    preserve ref or patch path, so a human or a `bmad-loop resolve --restore-patch` re-drive
    finds it directly, without archaeology.
  - **success:** Given only the escalation text of a post-fix intent-gap halt, `bmad-loop
    resolve --restore-patch` (or a human following the named ref) restores the reverted attempt
    with zero session-transcript access.
- **CAP-3**
  - **intent:** A post-hoc detector makes any residual gap loud -- an intent-gap halt whose
    preserve artifact is missing (seam bypassed, upstream behavior shifted) is flagged as a
    finding rather than passing silently, following the `story-status-check` / `loop-stall-check`
    precedent of local detectors containing an upstream bmad-loop blind spot.
  - **success:** Simulating an intent-gap halt with no preserve artifact trips the detector;
    a halt with its artifact present passes clean.

## Constraints

- **Always:** no edits to the installed `bmad_loop` package -- it ships via a pixi git-pinned
  dependency this repo does not own, and live loops may be importing it mid-run. Everything here
  is Marshal-side compensation (adapter seam, supervisor, detector).
- **Always:** the intent-gap halt itself stays exactly as strict. The never-patch-around
  protocol is correct; this work preserves the discarded attempt, and never changes when or
  whether the halt fires, nor lets a preserved attempt auto-reland without the contract fix.

## Non-goals

- **Not** a general "never lose any AI-generated output" system -- scoped to the intent-gap
  revert path inside `bmad-loop`'s dev-session lifecycle, the one halting flow without coverage.
- **Not** retroactive recovery tooling. Story 10.1's recovery already happened (PR #486, by
  transcript reconstruction); this contract is about the NEXT occurrence not needing that.
- **Not** its own upstream-report track. This dream rides the sibling
  `spec-bmad-loop-baseline-drift`'s upstream backlog (repo-access check, duplicate search,
  evidence packaging) -- both trace to gaps in how the orchestrator's dev-retry lifecycle
  handles an attempt that doesn't cleanly land, and likely share one report. This spec
  *contributes* the Story 10.1 evidence to that track; it does NOT maintain a parallel backlog.

## Success signal

Today, an intent-gap halt reproduces Story 10.1's exact end state: worktree clean at
`baseline_revision`, no `attempt-preserve/*` branch, no `failed/<story>/changes.patch`, clean
reflog -- recovery possible only via transcript archaeology, and only if a review step ran.
After the fix, an intent-gap halt on a story with tracked changes leaves a preserve artifact
matching the attempt (branch for real commits, patch otherwise), the escalation text names it,
`bmad-loop resolve --restore-patch` restores it without touching any transcript, and the CAP-3
detector reports clean; deleting the artifact and re-running the detector trips a finding.

## Open Questions

- "Interception point (a story-level design decision, not resolved by the Dream): whether the
  adapter seam can observe the attempt before bmad_loop's internal revert executes, or whether
  Marshal must snapshot proactively (supervisor-side) so the preserve artifact exists by the
  time the revert fires -- the revert itself runs inside the unowned package."
- "Selectivity: whether an intent gap surfaced during DEV (no adversarial-review prompts in the
  transcript, so no accidental recovery path at all) is distinguishable at the seam from an
  ordinary retry revert -- determines if preservation can target intent-gap halts specifically
  or must cover every revert to be safe."
