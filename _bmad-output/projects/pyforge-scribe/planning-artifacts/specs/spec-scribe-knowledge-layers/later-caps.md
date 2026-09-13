---
doc: later-caps
spec: scribe-knowledge-layers
status: parked
updated: 2026-09-13
---

# Parked capabilities — do not implement from this file

These are **not** in the five-field contract (`SPEC.md` CAP-1–CAP-5). They were
identified while locking the layered-knowledge approach (2026-09-13) so they
are not lost in a session. Mint a Story (and hoist into `SPEC.md` via
`bmad-spec` / memlog) before writing code.

**Still out of scope even as later CAPs:** wholesale `docs/`, `recipes/`,
presentations export trees, cocoindex inside `compile_graph`, full-text
`prd.md` / `epics.md` / architecture novels, semantic/pgvector as the default.

| ID | Intent | Why later | Unblocks |
|---|---|---|---|
| **CAP-6** | Compile **in-flight story specs.** Hoisted 2026-09-13 to `spec-scribe-in-flight-story-specs` CAP-1 / Story 10.1 (ledger filter, not frontmatter). | Was parked so the session would not lose it. | Session agents asking about the story they are on |
| **CAP-7** | **Pointer or extract** nodes for Brief / PRD / Architecture / `epics.md`: title + path + status, or FR/AD/spine list only. Never the wholesale body. | Documents stay SoT; Marshal already forbids `*prd*`/`*epic*` wholesale loads. A pointer does not recreate CAP-6’s token failure. | “Where is the PRD?” without serving 46k tokens |
| **CAP-8** | Explicit **graphify target list** (`src/platform/`, `scripts/` in addition to `src/shared/packages/`). Still not `recipes/` or repo root. | Cost + Story 8.2 currency must stay green first. Needs a target-list CAP, not a bigger hardcoded default. | Code map of host + factory scripts |
| **CAP-9** | Persist **`compiled_at`.** Hoisted 2026-09-13 to `spec-scribe-recall-stale-between-nightlies` CAP-1 / Story 11.1. | Was parked so the session would not lose it. | Marshal CAP-13 meaning between nightlies |
| **CAP-10** | **Fact ledgers visible to Marshal retrieve.** Hoisted 2026-09-13 to `spec-scribe-marshal-fact-visibility` CAP-1 / Story 9.1 (identity citation rule). | Was parked here so the session would not lose it. | Decks and dispatch citing the same numbers |
| **CAP-11** | First-class recall **modes** (`planning` / `memory` / `code`), not only `--kind`. | `--kind` is enough for CAP-4. Modes are the PyForge wiring shape. | Portal + agents without inventing argv |
| **CAP-12** | **Portal / harness wiring** (django-scribe, `.cursor/rules` if needed) calls kind-filtered recall. CAP-5 is `AGENTS.md` only. | Inherit CLI defaults first; do not redesign the portal. | “Wiring this into PyForge” |
| **CAP-13** | Named extra **`docs/` surfaces** (e.g. how-tos, `library-llms-full.md`) — never `docs/**`. | FR-9 named Dreams (CAP-3). Other docs are catalog, not contract. | Library/how-to questions |
| **CAP-14** | **One navigation owner:** graphify `code:` vs Marshal `codegraph.db`. Not both as recall peers. | Non-goal on this Spec is “do not replace codegraph.” A later decision can pick. | Agents asking “where is this symbol?” |

## Recorded, not scheduled

CAP-10 is Story 9.1. CAP-6 is Story 10.1. CAP-9 is Story 11.1
(`spec-scribe-recall-stale-between-nightlies`). No story is minted
here for CAP-7–CAP-8 or CAP-11–CAP-14.
