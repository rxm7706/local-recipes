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

## Capabilities

- **HER-1 — a Dream becomes a deck.** *Success:* `herald seed` renders a Dream into a deck and `herald pull` brings the designed result back; the round trip is the realized [[design-code-bridge]].
- **HER-2 — releases are proclaimed from the ledger.** *Success:* release notables compile from pipeline data, never hand-written.
- **HER-3 — the visual identity is one system.** *Success:* decks, infographics and the Guildhall share [[modernist-identity]]'s vocabulary.

## Constraints

- **The Dream is Tier 0 and this Spec is Tier 2.** Where they differ, the Dream is the
  intent and this contract is what was agreed to build from it.
- **Ownership does not move with the work.** Chains stay filed with the owning station
  (Charter §5), whatever surface the work touches.

## Non-goals

- **Owning the console.** The Guildhall is Marshal's ([[factory-console]]); Herald supplies its conviction and its look, not its machinery.
- **Infrastructure.** Moved to Marshal in the 2026-07-23 re-scope.

## Success signal

A release goes out with a deck, an infographic and notables that no one hand-assembled.
Open drift: the bridge is realized but runs on `claude-design`, an MCP outside the governed
tool surface — recorded in [[agent-tool-surface]]'s coverage table.
