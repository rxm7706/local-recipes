---
id: SPEC-agent-portability
spec: agent-portability
status: archived
archived-reason: absorbed
owner-dream: docs/dreams/agent-portability.md
surface: []          # archived — no live surface; see § What carries forward
sources:
  - ../../../../../../docs/dreams/agent-portability.md
open_questions: []
---

> **Retirement record.** This Dream is `status: archived` (`absorbed`). Charter §5 requires
> every Dream to carry a Spec, archived included. It states what was contracted, why it
> ended, and what survives — not a plan for work that will not happen.

# agent-portability — retirement record

## Why it was contracted

A standing practice, not a one-time build: the BMAD operating model should run on whichever
agent a team uses — Devin, GitHub Copilot, Claude, Cursor, Gemini — with planning able to run
on flat-rate subscriptions instead of metered IDE tokens. The method is the asset; the agent
is a socket. Three capabilities: PORT-1 (the entry-file family — `AGENTS.md`, `CLAUDE.md`,
`.cursor/rules/`, `GEMINI.md`, `.github/copilot-instructions.md` — stays in step, drift
detectable), PORT-2 (no vendor lock in the model itself), PORT-3 (planning runs on a
substitutable, flat-rate surface).

## Why it ended

**Retired 2026-08-02, as part of a dream-consolidation pass.** Not a duplicate or a
fabrication — checked each capability individually against what's real today:

- **PORT-1** maps directly onto `spec-pyforge-marshal`'s **FR-46** (entry-file family drift
  check) in the real PRD — the same concern, already contracted under Marshal's main FR range.
- **PORT-2** is a design constraint threaded through Epic 6's whole shape (adapter profiles,
  conformance matrix, no agent named as required anywhere in the tier layout) rather than a
  separately testable capability — it was never going to get its own FR, it's the reason
  FR-41..48 exist at all.
- **PORT-3** (planning on flat-rate web bundles / Gemini Gems / Custom GPTs) is not covered
  by Marshal's runtime-portability FRs (those are about *execution* agents, not *planning*
  tools) — but it already has a real home: `docs/specs/copilot-bridge-vscode-extension.md`
  (legacy Tier-1, tracked, unimplemented backlog), which this Dream's own body pointed to
  before being archived. Not orphaned.

## What carries forward

The practice continues under `pyforge-marshal.md` / `spec-pyforge-marshal` Epic 6 (PORT-1/2)
and `docs/specs/copilot-bridge-vscode-extension.md` (PORT-3) — this retirement does not touch
either. The five bridge patterns (`copilot-api`, `litellm`, `copilot-openai-api`,
`copilot-api-proxy`, `c2p`) remain real, cited detail in that legacy spec.

## Non-goals

- **Reviving this Dream as written.** Its intent already lives in the two homes named above.
- **Treating this record as a backlog item.** Archived Dreams are excluded from the Backlog
  board by design.

## Success signal

A reader arriving at this Dream learns in one page which of its three capabilities went
where — FR-46, an implicit design constraint, or a pre-existing legacy spec — without
mistaking any of them for an orphaned gap.
