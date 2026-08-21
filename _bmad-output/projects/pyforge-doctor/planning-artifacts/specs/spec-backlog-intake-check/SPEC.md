---
id: SPEC-backlog-intake-check
owner-dream: docs/dreams/deferred-work-resolution-sweep.md
companions: []
sources:
  - docs/dreams/deferred-work-resolution-sweep.md
---

> **Canonical contract.** This SPEC is the complete, preservation-validated contract for what to build, test, and validate. The source document listed in frontmatter is for traceability only.

# Backlog-intake check

## Why

A pain to solve. A tracked deferred-work entry says `owner: Story 4.5` (or names an epic) in prose, and nothing enforces that Story 4.5's actual scope addresses it — closing the entry today depends entirely on whoever drafts that story remembering to grep the ledger first. `docs/dreams/deferred-work-resolution-sweep.md` names this gap directly (its "Close the loop into future planning" bullet) and originally scoped it as CAP-8 of `spec-deferred-work-resolution-sweep` alongside that Spec's read-only verification sweep (CAP-1..7). Split into its own Spec 2026-08-21 (operator decision, tracked as `DW-11-8-1`) because it is write-adjacent to story-drafting — a different subsystem than read-only sweep verification — and bundling it into that Spec's Epic 11 would have muddied a pipeline that had already shipped cleanly as a self-contained whole.

## Capabilities

- **CAP-1 — backlog-intake surfacing.**
  - **intent:** When a new story/spec is drafted for an epic, tracked deferred-work entries whose `owner:`/prose names that epic or a story within it are surfaced as candidate acceptance criteria, instead of staying inert prose only a human happens to notice by re-reading the ledger.
  - **success:** Given a story/spec draft naming epic E, tracked deferred-work entries across the fleet's ledgers whose `owner:`/prose names epic E or a story within it are surfaced to the drafting session as candidates.

## Constraints

- **Matching must be precise, not substring/membership.** This fleet has already shipped one real bug from exactly this failure mode: `chain-completeness`'s INV-A decides a Spec is decomposed by testing whether its slug appears *anywhere* in concatenated `epics.md` prose — a substring test over a blob — which reported false-clean while 7 of 10 capabilities had zero stories (found 2026-08-15, still an open entry in this same ledger). CAP-1 must not repeat that class of bug: matching an `owner:`/prose reference to an epic/story id needs to name the id precisely (e.g. a parsed epic/story-id token), never a bare string-contains check that would also match a substring collision (epic 1's id matching epic 11's prose).

## Non-goals

- Not auto-writing acceptance criteria into the story/spec. CAP-1 surfaces candidates for the drafting session (human or agent) to accept, reject, or reword — it does not silently insert text into `epics.md` or a story spec.
- Not deciding which Tier-3 findings get promoted into tracked storage in the first place — that is `deferred-work-audit-completeness`'s / `spec-deferred-work-visibility`'s territory, the same non-goal `spec-deferred-work-resolution-sweep` states for its own sibling capabilities.

## Success signal

Drafting a story or spec for an epic that has open, precisely-matched deferred-work entries surfaces those entries as candidate acceptance criteria before the story is finalized — without a human having to remember to grep the ledger by hand.

## Assumptions

- **Trigger mechanism: a doctor CLI verb/detector, invoked manually, not a hook into the drafting skills' own instruction files.** `bmad-create-story` and `bmad-create-epics-and-stories` are prompt-driven markdown skills, not code — "hooking into" them means editing their skill instructions, a different integration shape than everything else Doctor owns. Every existing Doctor capability is a `pyforge.doctor.sources` detector or a `doctor <verb>` CLI command; CAP-1 follows that same pattern (a detector/verb a drafting session runs by hand, naming the epic/story it's about to draft against) rather than becoming the one capability that reaches into another skill's prompt. Resolved this way 2026-08-21 so implementation isn't blocked on a second open question after CAP-8's own split already cost one round of being blocked.
