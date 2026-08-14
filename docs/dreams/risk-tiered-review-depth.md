---
title: A one-line doc fix and a cross-module rewrite get the identical review
type: dream
owner: marshal
status: realized
---

# A one-line doc fix and a cross-module rewrite get the identical review

## The Dream

Every station's `marshal-policy.toml` sets `gate_mode = "none"` for unattended
operation, and its own comment is explicit about what that does and does not
skip: "`gate_mode`: unattended (operator direction, 2026-07-26). This is the
HUMAN approval gate ONLY — **the independent reviewer still runs on every
story**" (e.g. `_bmad-output/projects/pyforge-marshal/planning-artifacts/
marshal-policy.toml:26-28`, the same comment cloned into all nine loop
homes). `core/policy.py`'s `DEFAULT_POLICY` backs that with two flat, global
ceilings — `max_dev_attempts: 2`, `max_review_cycles: 3`
(`core/policy.py:275-276`) — identical for a doc-only story and a
cross-cutting rewrite. There is no dial between "review runs" and "review
skips": every story pays the same review cost, regardless of how mechanical
or how consequential the change actually is. That flatness is a real
contributor to why an unattended `bmad-loop` run is slower and costlier per
story than a supervised `bmad-quick-dev` session — the loop cannot spend less
on a change that is obviously low-risk, because nothing in the policy or the
gate knows the difference.

There is already a real precedent for classifying a story's risk shape in
this exact codebase — `core/gate.py::classify_doc_only_declaration` (Story
2.4, FR-23, `core/gate.py:237-281`). Reading it in full: it is a **pure**
function of two already-gathered facts — `declared_doc_only` (the story's own
declaration) and `has_uncommitted_changes` (from `VcsPort`) — with **no** I/O
of its own. It fails exactly one combination: no worktree changes AND not
declared doc-only, "the one combination indistinguishable from a story that
silently failed to do its work" (`core/gate.py:250-253`). Every other
combination — declared-with-no-changes, declared-with-changes, or
undeclared-with-changes — passes unconditionally. Its blast radius today is
narrow and singular: it feeds exactly one finding code (`MRS-GATE-006`) into
gate PASS/FAIL, and it says nothing at all about review — it decides whether
a story with no diff is allowed to close, never how much scrutiny a story
*with* a diff receives. It is real, working evidence that "classify a
story's risk shape as a pure function of a declaration plus an observed
fact" is an idiom this codebase already trusts — but it has never been
pointed at review depth, only at gate pass/fail for the no-change case.

Anything that reaches toward review depth has to reckon with `DW-AD23-3`
first. `_bmad-output/policy-defaults.toml:19-36` documents the incident in
full: the upstream `bmad-loop` default for `max_followup_reviews` was `1`,
and that single cap "damped five still-recommended follow-up reviews across
three projects (atlas 10.5/10.6, marshal 1.1, warden 6.3/5.1) into a
gitignored ledger" — real, reviewer-recommended follow-up work that
vanished because the cap silently discarded it once a story converged. The
incident is the reason `deferred-work-check` exists at all, and the reason
the repo-wide value is now `2`, "explicitly... with reasoning inline," never
left at a default nobody examined (`core/policy.py:277-286` carries the
matching in-code comment). The lesson is precise: **a cap that is too low
doesn't fail loudly — it produces a clean-looking envelope while dropping
real, reviewer-identified work.** Any mechanism that lets a story's review
run cheaper or fewer cycles has to avoid reproducing exactly that failure
mode for a class of stories, not just for the repo as a whole.

## What it looks like when real

- A story can be classified — mechanically, from something already true
  about it (its own declaration, its diff shape, or both) — into a review
  weight *before* review runs, the same "pure function of already-gathered
  facts" idiom `classify_doc_only_declaration` already establishes.
- **The independent reviewer still runs on every story, with no exception.**
  This Dream changes review *cost*, never review *occurrence* — the
  `gate_mode = "none"` boundary (human approval only, reviewer unconditional)
  is untouched.
- A low-weight story may run fewer review cycles or a cheaper review pass;
  a high-weight story is unaffected, or could even earn *more* scrutiny —
  the classification is a real signal, not a one-directional discount.
- **Any follow-up a review recommends is captured with the same durability
  `deferred-work-check` already enforces, at every tier.** A tightened cap
  for a low-weight story can never again cause a real recommendation to
  vanish into an unindexed ledger entry the way `DW-AD23-3` did — whatever
  this mechanism proposes has to be checked against that incident by name
  before it ships, not merely asserted safe.
- The tier a story's review ran at, and why, is visible in the same
  machine-readable envelope every other gate output already uses — never a
  silent choice.

## Constraints

- **Never skips the independent reviewer.** `gate_mode = "none"` already
  means "human approval gate only" — that boundary is load-bearing and
  stays exactly where it is. Nothing here reopens "does review run at all."
- **Never lowers `max_followup_reviews` (or an equivalent cap) below what
  `deferred-work-check` can still fully capture, for any tier.** `DW-AD23-3`
  is the concrete failure this constraint exists to prevent from recurring —
  cite it by name in the downstream Spec/story, not just in spirit.
- **Not a prescription of mechanism.** Which signal drives the
  classification (doc-only-style declaration, diff shape, surface size, a
  combination), which review lever it adjusts (cycle count, model choice, a
  cheaper lens set), and how the tier is surfaced are all design decisions
  left to the Spec and its downstream story.
- **Not model-tiering/adaptive-escalation.** A cheaper review *model* is one
  plausible lever this Dream names as a possibility, but choosing DEV-side
  models by difficulty, or adaptive escalation generally, is a separate,
  already-scoped investigation thread (a sibling effort, not this one) —
  this Dream does not decide or duplicate that mechanism.

## Realization log

- **2026-08-11** — Captured after the operator asked why `bmad-loop`-driven
  unattended development is slower/costlier than a supervised `bmad-quick-dev`
  session, and what could make unattended runs faster without weakening the
  review guarantee. Confirmed via `epics.md`: no existing FR/epic/story ties
  story risk to review depth or cycle count — `classify_doc_only_declaration`
  (Story 2.4) is the only risk-classification precedent, and it feeds gate
  pass/fail, never review scheduling. Read `DW-AD23-3`'s incident comment in
  full before drafting the Constraints section, specifically so this Dream
  cannot be read as license to shrink `max_followup_reviews` again. Queued as
  a Dream rather than touched directly — `core/gate.py`, `core/policy.py`,
  and `_bmad-output/policy-defaults.toml` were deliberately left untouched
  pending the Spec/story chain. Companion pain, same investigation, separate
  Dream (different subsystem, different epic):
  [`quick-dev-reconciliation.md`](quick-dev-reconciliation.md).
- **2026-08-14** — Realized — Story 2.8 (FR-185) shipped `classify_review_tier`/`resolve_review_cycles` in `core/gate.py`. Status flipped and FR-185 backfilled into the PRD by the 2026-08-14 audit.
