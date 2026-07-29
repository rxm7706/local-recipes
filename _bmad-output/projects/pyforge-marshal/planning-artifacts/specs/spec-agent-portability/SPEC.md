---
id: SPEC-agent-portability
spec: agent-portability
status: dreamt
owner-dream: docs/dreams/agent-portability.md
surface:
  []          # no code surface yet
sources:
  - ../../../../../../docs/dreams/agent-portability.md
open_questions: []
---

> **Canonical contract.** This SPEC is the complete contract for what to build, test and
> validate. Source documents in frontmatter are traceability only.

# agent-portability

## Why

**The method is the asset; the agent is a socket.** The operating model must run on
whichever agent the team uses — Devin, GitHub Copilot and its agents, Claude, Cursor,
Gemini — and planning must run on flat-rate subscriptions rather than metered IDE tokens.
Re-scoped to Marshal in the 2026-07-23 ownership review; Herald keeps the communication face.

This is a **practice**, not a deliverable: every new agent is a new socket, so it is tended
and never finished. Its sibling from the other side is [[agent-tool-surface]] — portability
is "runs on whichever agent", the surface is "reaches whichever craft".

## Capabilities

- **PORT-1 — the entry-file family stays in step.** *Success:* `AGENTS.md` and its per-tool pointers (`CLAUDE.md`, `.cursor/rules/`, `GEMINI.md`, `.github/copilot-instructions.md`) carry the same contract; a drift between them is detectable, not discovered.
- **PORT-2 — no vendor lock in the model.** *Success:* nothing in the tier layout, the BMAD wiring or the Spec contract names a specific agent as required.
- **PORT-3 — planning is substitutable.** *Success:* the planning chain runs on a flat-rate surface (web bundles, Gems, Custom GPTs) and its artifacts return to the repo unchanged.

## Constraints

- **The Dream is Tier 0 and this Spec is Tier 2.** Where they differ, the Dream is the
  intent and this contract is what was agreed to build from it.
- **Ownership does not move with the work.** Chains stay filed with the owning station
  (Charter §5), whatever surface the work touches.

## Non-goals

- **A per-agent fork of the model.** One method, many sockets — the moment a tool needs its own conventions, portability has already failed.
- **Guaranteeing feature parity across agents.** Capabilities differ; the *contract* must not.

## Success signal

Adding a new agent is a new pointer file and no change to the model. Today the family is
maintained by review rather than by a gate — PORT-1 is the first thing to make mechanical.
