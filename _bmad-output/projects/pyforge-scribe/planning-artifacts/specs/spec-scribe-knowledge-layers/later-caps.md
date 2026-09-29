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
| **later-caps:CAP-6** | Compile **in-flight story specs.** Hoisted 2026-09-13 to `spec-scribe-in-flight-story-specs` CAP-1 / Story 10.1 (ledger filter, not frontmatter). | Was parked so the session would not lose it. | Session agents asking about the story they are on |
| **later-caps:CAP-7** | **Pointer or extract** nodes for Brief / PRD / Architecture / `epics.md`. Hoisted 2026-09-13 to `spec-scribe-planning-pointers` CAP-1 / Story 13.1. | Was parked so the session would not lose it. | “Where is the PRD?” without serving 46k tokens |
| **later-caps:CAP-8** | Explicit **graphify target list**. Hoisted 2026-09-13 to `spec-scribe-graphify-target-list` CAP-1 / Story 15.1. | Was parked so the session would not lose it. | Code map of host + factory scripts |
| **later-caps:CAP-9** | Persist **`compiled_at`.** Hoisted 2026-09-13 to `spec-scribe-recall-stale-between-nightlies` CAP-1 / Story 11.1. | Was parked so the session would not lose it. | Marshal later-caps:CAP-13 meaning between nightlies |
| **later-caps:CAP-10** | **Fact ledgers visible to Marshal retrieve.** Hoisted 2026-09-13 to `spec-scribe-marshal-fact-visibility` CAP-1 / Story 9.1 (identity citation rule). | Was parked here so the session would not lose it. | Decks and dispatch citing the same numbers |
| **later-caps:CAP-11** | First-class recall **modes**. Hoisted 2026-09-13 to `spec-scribe-recall-modes` CAP-1 / Story 16.1. | Was parked so the session would not lose it. | Portal + agents without inventing argv |
| **later-caps:CAP-12** | **Portal / harness wiring.** Hoisted 2026-09-13 to `spec-scribe-portal-recall-defaults` CAP-1 / Story 12.1. | Was parked so the session would not lose it. | “Wiring this into PyForge” |
| **later-caps:CAP-13** | Named extra **`docs/` surfaces** (how-tos, `library-llms-full.md`). Hoisted 2026-09-13 to `spec-scribe-named-docs` CAP-1 / Story 14.1. | Was parked so the session would not lose it. | Library/how-to questions |
| **later-caps:CAP-14** | **One navigation owner:** graphify `code:` vs Marshal `codegraph.db`. **Hoisted 2026-09-13 to `spec-scribe-code-navigation-owner` / Epic 17.** | Was parked so the session would not lose it; unifying pgvector/semantic stays steward 49.7. | Agents asking “where is this symbol?” |

## Recorded, not scheduled

later-caps:CAP-6/7/8/9/10/11/12/13 are Stories 10.1 / 13.1 / 15.1 / 11.1 / 9.1 /
16.1 / 12.1 / 14.1. later-caps:CAP-14 is Story 17.1
(`spec-scribe-code-navigation-owner`).
