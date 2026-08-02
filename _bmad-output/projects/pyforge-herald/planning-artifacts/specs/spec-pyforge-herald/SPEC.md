---
id: SPEC-pyforge-herald
spec: pyforge-herald
status: specified
owner-dream: docs/dreams/pyforge-herald.md
surface:
  - src/shared/packages/pyforge-herald/**
sources:
  - ../../../../../../docs/dreams/pyforge-herald.md
open_questions: []
---

> **Canonical contract.** This SPEC is the complete contract for what to build, test and
> validate. Source documents in frontmatter are traceability only.

# pyforge-herald

## Why

Herald is the factory's **voice and visual surface**. *Invisible engineering is failed
engineering* — Herald exists so nothing the factory does stays invisible. Re-scoped by the
2026-07-23 ownership review (infrastructure moved to Marshal; Herald keeps communication).

**Herald's work is continuous, not a bookend** — corrected 2026-07-25, when this Dream said
"first to touch a Dream and last to touch a release". Communication runs throughout, not at
the ends.

**Current state (2026-08-02):** the deck family (Moment 1 content) is production-ready. HER-1's
CLI mechanization of it is in progress — 4 of 17 foundation stories done (package scaffold,
MCP-transport spike, bridge-core skeleton, registry module); `seed`/`pull`/`status`/`watch`
are not wired into the CLI yet, and the loop is paused mid-story on the fallback transport
adapter. Moments 2–4 (progress/success/operations proclamation) are Herald's active next
frontier, planned end-to-end but not yet implemented — see [[pyforge-herald]] (the Dream) and
`spec-herald-moments-2-4` (the separate, untouched Spec governing that work).

## Capabilities

- **HER-1 — a Dream becomes a deck.** *Success:* `herald seed` renders a Dream into a deck and `herald pull` brings the designed result back; the round trip is the realized [[design-code-bridge]]. *In progress:* the CLI foundation (package scaffold, transport port, bridge-core, registry) is built and tested; the `seed`/`pull`/`status`/`watch` subcommands themselves are not yet wired up.
- **HER-2 — releases are proclaimed from the ledger.** *Success:* release notables compile from pipeline data, never hand-written. *Status:* specced (Moments 2–4 chain, `spec-herald-moments-2-4`), not yet implemented.
- **HER-3 — the visual identity is one system.** *Success:* decks, infographics and the Guildhall share [[modernist-identity]]'s vocabulary.

## Constraints

- **The Dream is Tier 0 and this Spec is Tier 2.** Where they differ, the Dream is the
  intent and this contract is what was agreed to build from it.
- **Ownership does not move with the work.** Chains stay filed with the owning station
  (Charter §5), whatever surface the work touches.

## Non-goals

- **Owning the console.** The Guildhall is Marshal's ([[factory-console]]); Herald supplies its conviction and its look, not its machinery.
- **Infrastructure.** Moved to Marshal in the 2026-07-23 re-scope.
- **Re-specifying Moments 2–4.** Progress/success/operations proclamation is governed by
  `spec-herald-moments-2-4` (its own Spec, PRD, Architecture, Epics) — this Spec references
  that work in HER-2 but does not duplicate its capability breakdown.

## Success signal

A release goes out with a deck, an infographic and notables that no one hand-assembled. **Not
yet true end to end** (2026-08-02): the deck (HER-3) is production-ready and hand-operated;
the CLI that mechanizes seed/pull (HER-1) is mid-build; the notables (HER-2) have a full
planning chain but no code. Open drift: the bridge's design intent runs on `claude-design`, an
MCP outside the governed tool surface — recorded in [[agent-tool-surface]]'s coverage table.
