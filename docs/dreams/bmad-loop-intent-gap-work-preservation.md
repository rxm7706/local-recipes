---
title: An intent-gap revert can never discard real work without a recoverable trace
type: dream
owner: marshal
status: specified
---

# An intent-gap revert can never discard real work without a recoverable trace

## The Dream

When a `bmad-loop` dev session finds an **intent_gap** (a contradiction inside the story's own
`<intent-contract>` that the workflow may not silently patch around), it correctly reverts the
attempt rather than committing broken or contract-violating work — but today that revert leaves
**no recoverable git artifact**: no `attempt-preserve/*` branch, no `failed/*/changes.patch`, a
clean reflog. This is a deliberate asymmetry with the deferred-story path, which already preserves
every attempt via `scm.keep_failed`. The dream is for an intent-gap revert to get the same
preservation guarantee — so a correct, protocol-following halt never also means the honest,
reviewed work it produced becomes unrecoverable through git.

## What it looks like when real

- Before an intent-gap revert discards tracked changes, the attempt's commits (or working-tree
  diff, for an attempt that never committed) are parked exactly the way `_preserve_attempt_commits`
  / `_preserve_attempt_worktree` already do for the deferred-story path (`engine.py`'s
  `_rollback_or_pause`, called via `rollback-auto`) — an `attempt-preserve/*` branch when there are
  real commits, a `failed/<story>/changes.patch` when there aren't.
- The spec's own "Auto Run Result" / escalation text, which already names the exact recommended
  contract fix in detail, ALSO names the preserve ref/patch path directly — so a human or a
  `bmad-loop resolve --restore-patch` re-drive doesn't have to go looking for it.
- Recovering an intent-gap revert never requires session-transcript archaeology (reconstructing a
  diff from an adversarial-review Agent prompt's embedded content, as this Dream's own motivating
  incident required) — that path should exist as a last resort for pre-existing runs, never as the
  first-choice recovery method for a NEW one.

## What is real

- **`scm.keep_failed`'s auto-preserve safety net already exists** for the sibling failure mode
  (a story that times out, or is deferred by the orchestrator) — `attempt-preserve/<run>-<hash>`
  branches and `failed/<story>/changes.patch` files, both used repeatedly this session to recover
  real work (`docs/dreams/bmad-loop-baseline-drift.md`'s three occurrences). The intent-gap path is
  the ONE story-halting flow in this session that did NOT get this treatment.
- **One live, concrete occurrence (2026-08-14)**: marshal Story 10.1 (`Copier engine wrapper — the
  single seam`) implemented `seed/engine/copier.py` in full, passed the whole `pyforge-marshal`
  suite (3646 tests) plus two adversarial reviews, then correctly found and halted on a real
  contradiction in its own `<intent-contract>` (the `never_write` Boundaries rule vs. two
  already-shipped manifest entries FR-74 needs). The revert left the worktree "confirmed clean,
  matching `baseline_revision`" — by design, per the escalation's own text — with nothing to `git
  merge-base --is-ancestor` against and no preserve branch to fetch.
- **Recovery was still possible, but only by accident of a different feature**: the adversarial-
  review Agent-tool prompts (`bmad-review-adversarial-general` / `bmad-review-edge-case-hunter`)
  embed the FULL diff-against-baseline plus the complete content of every new file, so the
  reviewed implementation could be reconstructed byte-identical from the dev session's own Claude
  Code transcript (`~/.claude/projects/**/*.jsonl`) rather than re-implemented from scratch. This
  worked, but it is fragile — it depends on the review step having run at all (an intent-gap found
  during REVIEW, as here, has this; one found earlier, during dev, might not), on locating the
  right session transcript, and on the transcript still existing on disk.
- **The escalation's own text already recommends against re-implementing from scratch** ("The
  reverted implementation in this run's transcript... is a working reference — re-implementing
  from scratch should not be necessary") — i.e. the workflow already KNOWS the work shouldn't be
  thrown away, it just doesn't currently act on that knowledge with a durable artifact.

## Constraints

- **Cannot be fixed by editing the installed package in place**, for the same reason as
  [[bmad-loop-baseline-drift]]: `bmad_loop` ships via a pixi/conda-forge dependency (git-pinned
  upstream), not code this repo owns, and two loops may be actively running against it.
- **Must not weaken the intent-gap halt itself.** The dream is preserving the discarded work, not
  changing when or whether an intent-gap should halt and revert — that protocol (never silently
  patch around a contract contradiction) is correct and should stay exactly as strict.

## Non-goals

- **Not a general "never lose any AI-generated output" system.** Scoped specifically to the
  intent-gap revert path inside `bmad-loop`'s own dev-session lifecycle.
- **Not retroactive recovery tooling.** Story 10.1's own recovery (this session) already happened,
  by transcript reconstruction; this Dream is about the NEXT occurrence not needing that.

## Kinships

[[bmad-loop-baseline-drift]] (the sibling Dream for a different `bmad-loop` work-loss failure mode
— found the same session, both traced to gaps in how the orchestrator's dev-retry lifecycle
handles an attempt that doesn't cleanly land; shared upstream report filed 2026-08-23 as
https://github.com/bmad-code-org/bmad-loop/issues/701, register id `baseline-commit-midflight-drift`) ·
[[pyforge-marshal]] (the estate; owns `bmad-loop` adoption)

## Realization log

- **2026-08-14** — Dream captured immediately after recovering marshal Story 10.1 by Claude Code
  transcript reconstruction (`_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/
  spec-pyforge-marshal/.memlog.md` has the full recovery narrative), per the operator's explicit
  request to fix marshal/bmad-loop to prevent this class of loss going forward.
- **2026-08-14** — Spec authored (spec-bmad-loop-intent-gap-work-preservation, pyforge-marshal) by the 2026-08-14 dream-backlog audit: Marshal-side preservation symmetry at the adapter seam; upstream evidence rides spec-bmad-loop-baseline-drift's gated report track.
- **2026-08-23** — Story 20.3 shared upstream report path cleared both gates and filed
  https://github.com/bmad-code-org/bmad-loop/issues/701 — body includes this Dream's Story 10.1
  intent-gap evidence (revert with no `attempt-preserve/*` / `failed/*/changes.patch`) alongside
  the baseline-drift mid-flight failure mode. Register entry
  `baseline-commit-midflight-drift` in marshal `upstream-register.json`. Marshal-side preservation
  for this mode remains Stories 20.4+; no `bmad_loop` package edits.
