---
id: SPEC-agentic-sdlc-autonomy
spec: agentic-sdlc-autonomy
status: ready
updated: "2026-09-09"
owner-dream: docs/dreams/agentic-sdlc-autonomy.md
surface:
  []          # no code surface yet
sources:
  - ../../../../../../docs/dreams/agentic-sdlc-autonomy.md
open_questions: []
---

> **Canonical contract.** This SPEC is the complete contract for what to build, test and
> validate. Source documents in frontmatter are traceability only.

# agentic-sdlc-autonomy

## Why

Move the conversation — the industry's and our own — beyond "AI-assisted coding" to the
**Agentic SDLC**: agents that plan, execute and govern software creation while the human
governs *intent*. "Autonomy" is overloaded; this practice makes it precise through four
views, and runs a factory that synthesises all four.

It is a **standing position**, not a deliverable: a thing perpetually argued and refined,
never shipped. Its evidence is the factory itself.

## Capabilities

- **AUT-1 — autonomy is stated in views, not adjectives.** *Success:* a claim about autonomy names which view it belongs to, rather than asserting a level.
- **AUT-2 — the position is evidenced by the factory.** *Success:* each claim traces to something the factory demonstrably does — unattended loop runs, gated verdicts, published state — not to aspiration.
- **AUT-3 — the human governs intent, not implementation.** *Success:* intent is exercisable through the Guildhall without reading logs (Charter §7).

## Constraints

- **The Dream is Tier 0 and this Spec is Tier 2.** Where they differ, the Dream is the
  intent and this contract is what was agreed to build from it.
- **Ownership does not move with the work.** Chains stay filed with the owning station
  (Charter §5), whatever surface the work touches.

## Non-goals

- **A maturity-model score.** Levels invite gaming; views invite precision.
- **Raising the autonomy share by weakening gates** — a standing anti-metric, inherited from the atlas contract.

## Success signal

The position survives contact with practitioners because every part of it is instantiated
here. Standing risk: this is the practice most able to drift into marketing, because nothing
fails when it does.

## Assumptions

- `status: pitched` → `ready` (2026-09-09, operator-approved). **Fleet ruling: `pitched` is not a
  Spec status.** It is Dream vocabulary and was the fleet's only instance in a Spec `status:`
  field; `AGENTS.md:118` sanctions `draft → ready → in-progress → shipped`. `ready` is the honest
  value here: a settled standing position with nothing to decompose.
- **Doctor's `DEFERRED_SPECS` entry for this Spec stays.** It had never done anything: `pitched`
  is not in `OPEN_SPEC_STATUSES` (`board.py:77`), so `board.py:716` skipped the Spec before the
  `DEFERRED_SPECS` check ever ran, leaving the carefully-worded exemption at `board.py:88-90`
  inert. The flip to `ready` makes the exemption **live and honest** — a settled contract with
  nothing to decompose, exempted on the record. **Rejected:** `archived`/`absorbed` — cleaner
  bookkeeping, but it deletes a standing position the Charter still argues from.
