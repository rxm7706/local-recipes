---
title: "pyforge-scribe — Epics 3–5 + Canopy-cooperation retrospective"
created: "2026-08-26"
updated: "2026-08-26"
covers: "all pyforge-scribe code motion since retro-scribe-2026-08-08.md (2026-08-09 through 2026-08-26)"
evidence: "git log --oneline --since=2026-08-08 -- src/shared/packages/pyforge-scribe"
---

# pyforge-scribe — Retrospective, 2026-08-26

**Scope:** everything that landed on Scribe's code surface after the 2026-08-08 whole-build retro — Epic 3 (transcripts), Epic 4 (CAP-18 plugins), Epic 5 (skill/persona + portal slice), and the steward-driven Canopy cooperation work (PG driver, semantic recall, SKF compile, plane driver) that lives in Scribe's package under Scribe's port. Sprint ledger at close: all 14 stories `done`, epics 1–5 `done`.
**Format:** solo / AI-driven; substance only, no fabricated dialogue. Companion to `retro-scribe-2026-08-08.md` (which remains the Epic 1/2 record).

## Delivery snapshot (git evidence)

| Date | Commit | What |
|---|---|---|
| 2026-08-10/12 | `28551a6b65`, `1d60da0193` | Audit-phase reconcile; atomic-write consolidated into `pyforge-core` (CAP-2/CAP-7) — Scribe's locking pattern became shared infrastructure |
| 2026-08-22 | `48cfe52967` | Story 3.1 — transcript scanner (`--transcripts`): promotion candidates surfaced from raw `.jsonl` session transcripts into the existing reviewed `capture --promote` flow, never auto-promoted |
| 2026-08-22 | `80e95f3eed` + `84e8102155`, `00ca2467ed`, `7da904435c`, `5997b64e94` | Story 3.2 — transcripts join the compile sources, then **four** review-hardening passes on the same story |
| 2026-08-24 | `d16d3cd270` | Story 4.1 — `FlatFileGraphStore` registered as the default CAP-18 plugin; `open_graph_store` owner-selection factory (`graph_store_plugins.py`) |
| 2026-08-25 | `5a81f27f81` | steward 28.1 — `PostgresGraphStore` (pgvector, `scribe_schema`) behind the existing port, as a second plugin, not a fork |
| 2026-08-25 | `44ef5fc4f1` | steward 28.2 — semantic recall behind `GraphStore` (canopy FR-36), deterministic local embeddings (`embeddings.py`) — AD-6 air-gap preserved |
| 2026-08-25 | `1ff08a43b4` | steward 29.1 — SKF domain skill compiled from Scribe (the station with no skill, per CAP-15's success criterion) |
| 2026-08-26 | `ceed8f5fa9` | Story 5.1 — station-owned skill/persona tests (`tests/meta/test_skf_skill_ownership.py`, `test_station_persona.py`) |
| 2026-08-26 | `9f968be5e5` | Story 5.2 — first portal slice: `/stations/scribe/` submits one recall query via `PortalClient` only, with a meta-test that fails on raw HTTP or a host `pyforge.*` import |
| 2026-08-26 | `3d745c2c31` | Seven station SKF skills exported into `CLAUDE.md`/`AGENTS.md` — Scribe's skill now loads estate-wide |
| 2026-08-26 | `2d264c7f5c` | steward 34.5 / canopy FR-50 — `PlaneGraphStore`: semantic recall ranked on the CAP-19 query plane; embeddings persist in `atlas.duckdb`, so FR-36 survives without Chroma or an in-memory DuckDB |

## What shipped, in product terms

1. **Scribe reads the fleet's highest-fidelity source.** Epic 3 systematized what the pyforge-warden spec-recovery incident proved by hand: raw session transcripts hold decisions curated memory missed. The scanner surfaces discussed-never-curated candidates *into the reviewed promotion flow* (the FR-3 gate is untouched), and transcripts joined the compile sources with transcript+position provenance. This is a deliberate, recorded amendment of the PRD's "never mines session transcripts" non-goal — the review gate survived; the absolutism didn't.
2. **The storage engine became a plugin surface instead of a decision.** Story 4.1 put the `GraphStore` port on the shared CAP-18 hook contract. Three drivers now sit behind one Protocol: flat-file (default, owner `scribe`), PostgreSQL/pgvector (owner `steward`), plane/DuckDB (owner `atlas`). No caller imports an engine client; owner selection is one env var.
3. **Semantic recall arrived without breaking the air gap.** Embeddings are deterministic and local; lexical recall remains the default path. The 2026-07 PRD's "no LLM required" resolution still holds even after the semantic upgrade.
4. **Scribe completed the five-tier station shape** — CLI (+ unified `pyforge scribe`), portal slice, MCP face, SKF skill, persona — counted in the estate's 40/40 declaration (strategy Epic 37.1, 2026-08-26).

## The dual-write decision (2026-08-26)

Operator ruling, recorded in `spec-pyforge-unifying-strategy` § Open Questions (`query-plane-scribe-cutover`): **dual-write for now.** The CAP-19 plane — via the 34.5 store-port driver — is **primary** and satisfies FR-36; `scribe_schema` pgvector **stays written as the safety net** until the plane has operating history, at which point retirement becomes its own explicit decision. Lexical recall may stay local. Two implications this retro pins down for future Scribe work: (a) do not treat the PG path as dead code or "clean it up" — it is a deliberate safety net; (b) the cutover's end state is a *future decision with a precondition* (plane operating history), not a scheduled task — nobody should back into it via a refactor.

## What held

- **AD-5 keeps paying.** Third consecutive validation of the port-first pattern: PG, plane, and plugin-factory work all landed with zero changes to `compile.py`/`recall.py` callers and zero changes to the Protocol. The 2026-08-08 retro called the seam a template worth reusing; three more drivers later, that is measured fact, not opinion.
- **The adversarial-review lesson was applied, not just recorded.** Story 3.2 took four independent review-hardening passes before done — exactly the "unattended-pipeline code gets independent review" process action the 2026-08-08 retro minted from Epic 2's crash-bug findings. The process item can be marked adopted.
- **AD-2/AD-7 discipline extended to new surfaces cleanly**: the portal slice reaches Scribe only through `PortalClient`, the persona only through `pyforge scribe …` + `POST /stations/scribe/mcp`, and both are enforced by meta-tests rather than convention.
- **Convergence with the Unifying Strategy is real, not aspirational**: Scribe's roles in that SPEC — team memory/graph (CAP-14), portal + MCP face client on the Canopy host (CAP-3/4), skill/persona (CAP-15/16), plane client (CAP-19) — each now maps to landed code listed in the snapshot above. The strategy's earlier correction ("the dual-driver premise was false; only flat-file exists") is itself now historical: the drivers exist, on Scribe's own port, owned by the stations the strategy assigned.

## What to watch (open items, carried forward with evidence)

1. **RISK-1, still open, now 4 weeks old:** `promote.py` — the only write path outside `.claude/memory/` — has never received an adversarial review (no Review Triage Log in spec-1-3; no review commit since). Highest-value unclosed loop from the 2026-08-08 retro, unchanged.
2. **RISK-2, still open:** nothing schedules the nightly compile (no pixi task, no CI workflow as of 2026-08-26). Epic 3 *raised the stakes*: the transcript surface is the only compile surface with **no cost bound** (whole-file `.jsonl` reads, O(candidates × curated-sentences) diffing — `DW-FU-3-2-2`), so the first scheduled run will also be the first unattended stress test.
3. **`DW-FU-3-2` / `DW-FU-3-2-4`:** transcript node ids collide on shared basenames across subdirectories; recall's id-ascending tie-break favors the *older* of two equally-matching statements for date-ordered filenames — a supersession-adjacent wrinkle worth fixing before recall quality work.
4. **`DW-FU-3-2-3`:** the `spec-pyforge-scribe` spec-surface baseline is stale for 12 files and the spec memlog has no Epic 3 provenance entries — the governed-surface reconcile for Epic 3 has not been done.
5. **Promotion sweep still pending:** the 2026-08-08 market refresh's #4 recommendation (sweep the ~112-file user-local store) has not run; team memory holds 5 indexed entries as of 2026-08-26. The mine is still mostly unmined.

## Verdict

Accepted. The three post-ship epics landed complete with ledger, code, and tests agreeing; the steward-cooperation work respected Scribe's port and write boundaries; and the one genuinely new operating condition — dual-write on the query plane — is an operator decision this retro records so no future session re-derives or "optimizes" it away. The open items above are debt with names and owners, not drift.
