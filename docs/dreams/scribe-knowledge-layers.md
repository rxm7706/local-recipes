---
title: The graph is layered knowledge, not one bag
type: dream
owner: scribe
status: specified
---

# The graph is layered knowledge, not one bag

## The Dream

The estate already compiles a knowledge graph every night. Agents still do not
know what to ask, and the one consumer that works (Marshal planning-graph)
never sees most of what the compile writes. Thirty-seven thousand AST nodes
sit in the same candidate list as seven team-memory decisions. Retros are a
filename glob. Stale flags fire on a compile that just read the file. Dreams
and five-field SPECs — the contract this repo claims to run on — are absent.

The Dream is **layered knowledge**: policy stays in `AGENTS.md` and skills;
decisions stay in team memory; contracts (active Dreams, ready SPECs, Herald
fact ledgers) compile as `doc`; planning memlogs stay the Marshal slice;
code stays in the store for navigation extras and `scribe recall --kind code`,
never as the default answer. Marshal `codegraph` owns structure-graph
navigation. Archive, test fixtures, and implementation-artifacts are not
fleet truth.

## What it looks like when real

- A full rebuild does not mark just-read sources stale.
- `scribe recall "why…"` cites memory, a Dream, a SPEC, a fact ledger, or a
  memlog — not a graphify label.
- Marshal `context retrieve --scope` still grounds on that project's
  planning tree.
- Nightly still keeps `code:` nodes; default recall does not serve them.
- An agent session knows to run `scribe recall` for decisions and not to
  treat the AST dump as policy.

## Constraints / Non-goals

- No second GraphStore. Code still writes through `open_graph_store`.
- No `docs/**` dump, no `recipes/`, no presentations export tree.
- Cocoindex stays on `scribe index refresh`, not `compile_graph`.
- Do not replace Marshal `codegraph.db` with graphify recall.

## Kinships

[[pyforge-scribe]] · [[scribe-graphify-nightly-currency]] ·
[[deck-family-currency]] · [[marshal-token-economy]] ·
[[pyforge-unifying-strategy]]

## Realization log

- **2026-09-13** — Operator accepted the layered-knowledge recommendation
  (hygiene, named surfaces, kind-filtered recall, session path). Spec
  `spec-scribe-knowledge-layers` under pyforge-scribe; Epic 8 Stories 8.4–8.6
  (8.3 fact ledgers already minted on the currency Dream).
- **2026-09-13** — Parked later CAPs recorded in
  `planning-artifacts/specs/spec-scribe-knowledge-layers/later-caps.md`
  (CAP-6–CAP-14). Not in the five-field contract; do not implement until
  hoisted + Story-minted.
- **2026-09-13** — CAP-4/CAP-5 realized in Stories 8.5–8.6: default recall
  omits `code:`; `AGENTS.md` session path (outside `bmad:context`).
