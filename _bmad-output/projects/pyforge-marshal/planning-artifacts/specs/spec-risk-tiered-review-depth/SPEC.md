---
id: SPEC-risk-tiered-review-depth
spec: risk-tiered-review-depth
status: draft
owner-dream: docs/dreams/risk-tiered-review-depth.md
surface:
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/gate.py
sources:
  - ../../../../../../docs/dreams/risk-tiered-review-depth.md
open_questions: []
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what
> to build, test, and validate. `docs/dreams/risk-tiered-review-depth.md` is listed in
> `sources:` for narrative rationale this contract intentionally omits.

# A one-line doc fix and a cross-module rewrite get the identical review

## Why

A pain to solve. Every station's `marshal-policy.toml` sets `gate_mode = "none"` for
unattended operation, and its own comment is explicit: this is the HUMAN approval gate ONLY --
"the independent reviewer still runs on every story." `core/policy.py`'s `DEFAULT_POLICY`
backs that with two flat, global ceilings -- `max_dev_attempts: 2`, `max_review_cycles: 3` --
identical for a doc-only story and a cross-cutting rewrite. There is no dial between "review
runs" and "review skips": every story pays the same review cost regardless of how mechanical
or how consequential the change actually is, and that flatness is a real contributor to why an
unattended `bmad-loop` run costs more per story than a supervised `bmad-quick-dev` session.

There is already a real precedent for classifying a story's risk shape in this codebase --
`core/gate.py::classify_doc_only_declaration` (Story 2.4, FR-23). It is a pure function of two
already-gathered facts (a story's own doc-only declaration, and whether the worktree has
changes), with no I/O of its own. Its blast radius today is narrow: it feeds exactly one
finding code into gate pass/fail, and says nothing about review depth -- it decides whether a
no-diff story is allowed to close, never how much scrutiny a story *with* a diff receives. It
is real, working evidence that "classify a story's risk shape as a pure function of a
declaration plus an observed fact" is an idiom this codebase already trusts, but it has never
been pointed at review scheduling.

Any mechanism reaching toward review depth has to reckon with `DW-AD23-3` first. The upstream
`bmad-loop` default for `max_followup_reviews` was `1`, and that single cap damped five
still-recommended follow-up reviews across three projects into a gitignored ledger -- real,
reviewer-identified work that vanished because the cap silently discarded it once a story
converged. That incident is the reason `deferred-work-check` exists, and the reason the
repo-wide value is now `2`, explicit, with reasoning inline. The lesson is precise: a cap that
is too low doesn't fail loudly -- it produces a clean-looking envelope while dropping real
work. Any mechanism that lets a story's review run cheaper for a class of stories has to avoid
reproducing exactly that failure mode.

## Capabilities

- **CAP-1**
  - **intent:** A story is classified into a review weight before review runs, mechanically,
    from something already true about it (its own declaration, its diff shape, or both) --
    the same pure-function-of-already-gathered-facts idiom `classify_doc_only_declaration`
    already establishes.
  - **success:** Given a story's declaration and its observed diff, the classification
    produces a deterministic, testable weight with no I/O and no model call in the path.
- **CAP-2**
  - **intent:** Review depth/cost varies by weight without ever skipping the independent
    reviewer -- a low-weight story may run fewer review cycles or a cheaper review pass; the
    `gate_mode = "none"` human-approval-only boundary is untouched.
  - **success:** A test proves the reviewer runs on every story regardless of weight, and that
    only cycle count/cost, never occurrence, differs by tier.
- **CAP-3**
  - **intent:** `deferred-work-check`'s full-capture guarantee holds at every tier -- a
    tightened cap for a low-weight story can never cause a real reviewer-recommended
    follow-up to go uncaptured.
  - **success:** A regression test reproduces the `DW-AD23-3` shape (a follow-up recommended
    under a tightened cap) and proves it is captured by `deferred-work-check`, not silently
    dropped, for every defined tier.
- **CAP-4**
  - **intent:** The tier a story's review ran at, and why, is visible in the same
    machine-readable envelope other gate output already uses.
  - **success:** The envelope for any evaluated story carries its review-weight tier and the
    classification facts that produced it.

## Constraints

- **Always:** the independent reviewer runs on every story, with no exception -- `gate_mode =
  "none"` remains human-approval-gate-only; nothing here reopens whether review runs.
- **Always:** `max_followup_reviews` (or an equivalent cap) is never lowered below what
  `deferred-work-check` can still fully capture, for any tier -- `DW-AD23-3` is cited by name
  in the downstream story, and the proposed mechanism must be proven not to reproduce it.

## Non-goals

- **Not** a prescription of which signal drives the classification, which review lever it
  adjusts (cycle count, model choice, a cheaper lens set), or how the tier surfaces -- left to
  the downstream story's design.
- **Not** model-tiering or adaptive-escalation for DEV-side model selection. A cheaper review
  model is named as one plausible lever, but choosing models by difficulty generally is a
  separate, already-scoped sibling investigation thread this spec does not decide or
  duplicate.

## Success signal

A story mechanically classified as low-weight (e.g. a doc-only-style change) runs review at
reduced cost (fewer cycles, or a cheaper pass) while a high-weight story is unaffected --
**and** a reviewer-recommended follow-up on a low-weight story still reaches
`deferred-work-check` with zero `tier3-only-deferral`-style loss, the same guarantee every
other story already gets.
