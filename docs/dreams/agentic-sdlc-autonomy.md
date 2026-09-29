---
title: The Agentic SDLC — four views of autonomy, one governed factory
type: practice
owner: marshal
status: archived
archived-reason: folded-into-station-dream
---

> **Consolidated into [[pyforge-marshal]]** on 2026-09-16 (one-chain-per-station CAP-8 pilot; folded from `agentic-sdlc-autonomy`).

# The Agentic SDLC — redefining autonomy in software engineering

## The Dream

Move the industry conversation (and our own practice) beyond "AI-assisted
coding" to the **Agentic SDLC**: agents that plan, execute, and govern software
creation while the human governs *intent*. "Autonomy" is overloaded; the dream
is to make it precise through **four views** — and to run a factory that
synthesizes all four:

1. **Taxonomy** (governance): L1–L5 levels; L3 "Context Gates" as the production
   ceiling — machine-readable boundaries, human escalation.
2. **Implementation** (process): agents mapped to pipeline stages; automated
   verification pipelines as the answer to Verification Debt; privilege drift
   contained.
3. **Architectural** (control flow): deterministic Workflows where determinism
   wins; dynamic Agents (BMad-Method + module ecosystem) where judgment is
   needed.
4. **Environmental** (workspace): from API-bounded surfaces to native terminals
   with conda-forge/pixi — capability bounded by sandbox and policy.

## What is real (the factory as living proof)

- L3 governance in production: bmad-loop's graduated gates + CRITICAL
  escalation ([[pyforge-marshal]]); Warden's never-false-green verdicts
  ([[pyforge-warden]]); per-story `mode:` fields; live Context-Gate evidence
  (the 2026-07-23 permission-boundary escalation).
- The Workflows-vs-Agents split applied deliberately (the bridge's
  deterministic no-LLM constraint vs. persona agents).
- Both ACI extremes governed: MCP-bounded Design surface + sandboxed native
  terminal.
- **The deck**: `presentations/agentic-sdlc/` (45 slides, PR #50) — the family's
  origin engine and this Dream's chapter on method.

## The frontier

- Fold the four-views white paper into the deck as a new act — all source
  material is staged in `docs/intake/agentic-sdlc/` (white paper, infographic +
  masterclass HTMLs, updated Marp draft) awaiting the refresh.
- **Formal L-level adoption**: label story modes L1–L5; publish the mapping.
- Fleet-level resource budgets; privilege-drift management ([[pyforge-doctor]]).

## Realization log

- **2026-07-11** — the agentic-sdlc deck shipped (PR #50).
- **2026-07-23** — the four-views white paper arrived; Dream retro-seeded with
  the factory's own L3 evidence.

- **2026-09-09 (fleet readiness pass — operator-approved batch)** — Dream status kept `specified`;
  **`spec-agentic-sdlc-autonomy` moves `pitched` → `ready`.** `pitched` is Dream vocabulary and was
  the fleet's only instance in a Spec's `status:` field, outside the sequence `AGENTS.md:118`
  sanctions (`draft → ready → in-progress → shipped`). Its effect was invisible: `pitched` is not in
  `OPEN_SPEC_STATUSES` (`board.py:77`), so `board.py:716` skipped the Spec before the
  `DEFERRED_SPECS` check ever ran — the carefully-worded exemption at `board.py:88-90` had never done
  anything. **The `DEFERRED_SPECS` entry stays**; `ready` makes it live and honest: a settled
  standing position with nothing to decompose, exempted on the record. Fleet ruling recorded in the
  same batch: `pitched` is not a Spec status. Batch:
  `_bmad-output/projects/pyforge-steward/planning-artifacts/research/fleet-readiness-decision-batch-2026-09-09.md`.
