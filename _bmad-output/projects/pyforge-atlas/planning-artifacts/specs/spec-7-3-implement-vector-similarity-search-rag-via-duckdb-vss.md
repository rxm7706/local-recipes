---
title: 'Story F3 (7.3): Implement Vector Similarity Search (RAG) via DuckDB `vss`'
type: 'feature'
status: shipped
regenerated: '2026-07-25'
source: 'epics.md (authoritative intent + acceptance criteria) + shipped code on main'
original_spec: 'NEVER AUTHORED as a file — wave B9-H4 ran through the in-session agent loop, not bmad-create-story (which wrote files only for waves 0/A/B1-B8), confirmed by the migration session itself. Nothing was lost; there is no original to recover. Intent+ACs below are the real epics.md contract.'
enriched: '2026-07-25 (merged PR #94 body + main commit log; dev narrative recovered, review-triage partial)'
---

> **Contract-spec — no original ever existed (corrected 2026-07-25).** This story
> (wave B9–H4) was built by the atlas migration's **in-session agent loop**, which —
> unlike `bmad-create-story` (used only for waves 0/A/B1–B8) — never emitted a per-story
> spec file. The atlas migration session (`01FYyQvBJuXwySiaMUUYCqBZ`) confirmed this
> exhaustively: no such file exists in `implementation-artifacts/`, `.bmad-loop/runs/`
> (which never existed for atlas), any git worktree, git history, or anywhere on disk.
> **Nothing was lost — there is no original to recover.** This file carries the
> load-bearing contract (Intent + Acceptance Criteria **verbatim** from the tracked
> `planning-artifacts/epics.md`) plus a dev narrative reconstructed from the merged record
> (the "Dev narrative" section below). A fuller BMAD-story-format reconstruction (Dev
> Agent Record + File List + Review Triage Log, built from the agent-loop transcripts) is
> at `../../spec-archive/retro-story-files/7-3-f3.md` — the operator's web-session archive.

## Contract (from epics.md — verbatim, authoritative)

### Story F3 (7.3): Implement Vector Similarity Search (RAG) via DuckDB `vss`

As a CFE authoring agent,
I want RAG embeddings + similarity search via DuckDB's `vss` extension,
So that semantic retrieval over embedded artifacts runs in the same single engine.

**Acceptance Criteria:** (spec § 9 Story F3, binding)

**Given** embedded artifacts in the DuckDB store
**When** a similarity query runs
**Then** it returns ranked results from DuckDB via `vss`
**And** the embedding model/strategy and offline `vss` extension provisioning (default network `INSTALL` collides with AD-13 for the consumer profile) are resolved in this story's spec (Spine Deferred).

- **FRs:** FR-5.
- **Invariants:** AD-4, AD-13 (offline provisioning tension — must resolve, not ignore).
- **Mode:** LOOP-E.
- **Gating question:** none (embedding strategy is a story-spec decision).
- **Verify gate:** `kedro-test` (ranked-results fixture).
- **Depends on:** F1 (consolidated store).

## Tasks / Subtasks

*(Derived from the ACs — no original task breakdown was authored for this loop-run story.)*

- [x] it returns ranked results from DuckDB via `vss`
- [x] the embedding model/strategy and offline `vss` extension provisioning (default network `INSTALL` collides with AD-13 for the consumer profile) are resolved in this story's spec (Spine Deferred).

## Dev Notes

**Planning metadata (from `epics.md`):**

- **FRs:** FR-5.
- **Invariants:** AD-4, AD-13 (offline provisioning tension — must resolve, not ignore).
- **Mode:** LOOP-E.
- **Gating question:** none (embedding strategy is a story-spec decision).
- **Verify gate:** `kedro-test` (ranked-results fixture).
- **Depends on:** F1 (consolidated store).

### Implementation notes

<!-- DERIVED 2026-07-27 by reading the shipped code (PR #94). No original dev-session
     notes existed for this story; this is what the merged implementation actually does. -->

**The ranking is a DuckDB `vss` query, and that is the whole point (AD-4).** Similarity
search lands in the same engine as analytical compute and graph traversal — no rival vector
engine is introduced. `DuckdbVssRagStore` is the surface.

**Two provisioning paths, and only one of them touches the network.**
`load_vss_offline()` LOADs the extension from the **local extension cache**, offline, and
raises a clear `VssNotProvisionedError` when it is not there (AD-13 — a legible failure, not
a silent degrade). The network `INSTALL` lives **only** in `provision_vss()`, which is the
attended path. Splitting these two is what lets a vector-search feature ship inside an
offline-by-default package.

**The default embedder is deterministic and offline by design.** `HashingEmbedder` uses
lowercased word tokens plus padded character 3-grams, mapped through a **signed hashing
trick**: a stable digest picks the bucket and its low bit picks the sign. No model file, no
global RNG state, no download — so the gate is fast and reproducible.

**The embedder is injectable, and the distinction being tested is deliberate.** `Embedder` is
a `Protocol` (fixed `dim`, pure `embed`), and `DuckdbVssRagStore(embedder=...)` takes any
implementation. The gate proves the **`vss` ranking mechanism**, not the quality of a
particular embedding — so a real learned model can be swapped in later without the gate
having encoded an accidental dependency on hash-embedding behavior. A learned embedder is
deferred as DW-F3-1.

**Default width is a deliberate trade.** Small enough to keep the offline gate fast, wide
enough that the hashing-trick collision rate stays low on short artifact texts.

### References

- [Source: _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md#Story-F3]
- [Source: docs/specs/cfe-atlas-datapipeline-kedro-migration.md#§9-Story-F3]
- [Architecture: _bmad-output/projects/pyforge-atlas/planning-artifacts/architecture/architecture-pyforge-atlas-2026-07-17/ARCHITECTURE-SPINE.md]

## Realized in

- **Package:** `src/shared/packages/pyforge-atlas/` (import `pyforge.atlas`).
- **Status:** done + shipped 2026-07-18 (atlas Kedro migration, 32/32; PRs #58–#105 merged to `main`).
- **Verification:** behaviour is covered by the migrated pipeline's tests on `main`. For the
  precise file-level Code Map, read the implementation on `main` — this regenerated spec
  deliberately does not guess a per-file map it cannot verify from the lost original.

## Delivery Record

<!-- DERIVED from the merged PR via `gh` on 2026-07-27. Exact, not reconstructed. -->

| | |
|---|---|
| Pull request | **#94** — story(F3): DuckDB vss vector similarity search (RAG) (FR-5) |
| Merged | 2026-07-18 |
| Diff | 6 files, +753 / -0 |
| Test files touched | 3 |

**Commits**

- `df58bfc` story(F3): DuckDB vss vector similarity search (RAG) (FR-5)
- `2acfeaa` story(F3): tighten identifier regex $ -> \\Z (independent review, LOW…

**File list** *(exact, from the merged diff)*

```
  350 +     0 -  src/shared/packages/pyforge-atlas/tests/rag/test_vss_similarity_search.py
  228 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/rag/store.py
  106 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/rag/embedding.py
   40 +     0 -  src/shared/packages/pyforge-atlas/tests/catalog/test_no_inline_io.py
   29 +     0 -  src/shared/packages/pyforge-atlas/src/pyforge/atlas/rag/__init__.py
    0 +     0 -  src/shared/packages/pyforge-atlas/tests/rag/__init__.py
```

## Dev Agent Record

### Agent Model Used

In-session BMAD agent loop (draft → 2× adversarial review → 1× independent fresh-eyes review → real-gate verify), not a `bmad-dev-story` story-file run.

### Completion Notes List

- **Impl commit `df58bfc`** — story(F3): DuckDB vss vector similarity search (RAG) (FR-5)
  - Adds rag/ — semantic retrieval over embedded artifacts in the SAME single
  - engine (AD-4). similarity_search embeds the query with an injectable, offline,
  - deterministic feature-hash embedder (hashlib — stable across processes; a
  - learned model is the DW-F3-1 upgrade) and ranks with an EXACT DuckDB
  - ORDER BY array_distance(emb, ?) LIMIT k — distance computed + sorted IN DuckDB,
  - never numpy/faiss (AD-4 vector-engine import-ban: faiss/hnswlib/chroma/qdrant
  - banned). The vss HNSW index is the scale structure whose creation requires the
  - vss extension.
  - AD-13 offline provisioning RESOLVED: the consumer path only LOADs vss from the
  - pre-provisioned local cache via an injectable loader, raising a clear
  - VssNotProvisionedError when absent — never a silent network INSTALL (that lives
  - only in the explicit attended provision_vss, DW-F3-2).
  - Reviewer fixes (both in-loop reviewers, substantive):
  - - The store now SETs hnsw_enable_experimental_persistence so index()+search work
  - on a PERSISTENT (on-disk) connection — the F1 consolidated store F3 is designed
  - to ride, which every prior test masked with in-memory (CREATE INDEX ... HNSW
  - raised BinderException on-disk). Regression test on a file-backed connection.
  - - table/metric constructor args are validated as bare SQL identifiers (they are
  - interpolated into DDL by name; a value smuggling a second statement could DROP
  - a table). Regression test proves injection is rejected pre-execution.
  - - Docstrings corrected: the shipped query is an EXACT seq-scan+top-n (the id
  - tiebreak keeps it exact, so it does not use the HNSW index); vss is load-bearing
  - at the store/index level, not the exact query — no false acceleration claim.
  - 666 passed (+21).

## Review Triage Log

Independent/Gemini review produced follow-up fix commit(s) on PR `#94`:

- `2acfeaa` — story(F3): tighten identifier regex $ -> \\Z (independent review, LOW defense-in-depth)

## Dev narrative — recovered from the merged record

> The original spec's `## Dev Notes` / `## Review Triage Log` were lost with the Tier-3
> worktree teardown (this story was built in claude.ai/code web session
> `01FYyQvBJuXwySiaMUUYCqBZ`; see `README.md`). The narrative below is reconstructed from
> the **authoritative merged record** — the story's PR body and its commits on `main` —
> **not** a regeneration. If the verbatim original is recovered from the web session, it
> supersedes this section.

### Dev summary — merged PR #94: story(F3): DuckDB vss vector similarity search (RAG) (FR-5)

## Deferred Work (DW ledger)

### DW-F3-1 — a real learned embedding model (upgrade from the deterministic default)
- source_spec: `f3-implement-vector-similarity-search-rag-via-duckdb-vss.md`
  summary: F3's default embedder is a deterministic, offline, dependency-light feature-hash
    (hashing-trick) vectorizer — it proves the DuckDB `vss` RANKING mechanism (which is what F3
    ships) with no model download and no network, and is stable across processes/machines
    (hashlib, never Python's salted hash()). A real LEARNED embedding model (e.g.
    sentence-transformers) is the semantic-quality upgrade: it is heavy and may need a
    model download / network, so it is DEFERRED. The seam is ready — `DuckdbVssRagStore(embedder=…)`
    accepts any object with an int `dim` + `embed(text)->list[float]`; the ranking still runs in
    DuckDB regardless of embedder, so the upgrade requires NO store/query change. Wire it when a
    conda-forge-provisioned model + an embedding-provisioning story lands.
  evidence: `rag/embedding.py::HashingEmbedder` is the default; `Embedder` is a Protocol; the
    gate proves ranked results are deterministic under the hash embedder (a learned model would
    change the vectors, not the ranking mechanism).

### DW-F3-2 — live `vss` extension provisioning (the one-time network INSTALL)
- source_spec: `f3-implement-vector-similarity-search-rag-via-duckdb-vss.md`
  summary: The consumer path is offline: it only `LOAD`s `vss` from the pre-provisioned local
    extension cache and raises `VssNotProvisionedError` (naming the provisioning step) if absent
    — never a silent network `INSTALL` (AD-13). The one-time `INSTALL vss` (network) lives ONLY
    in the explicit, attended `rag.provision_vss(connection)`, which the consumer path never
    calls. In THIS container vss is already cached (v1.5.4), so the offline LOAD works; a fresh
    air-gapped/enterprise environment must run `provision_vss` (or ship the vendored extension
    to the DuckDB extension dir) once, attended, before the RAG surface is usable. That
    provisioning-in-a-clean-environment step is the deferred/attended piece.
  evidence: `rag/store.py::load_vss_offline` (offline LOAD or VssNotProvisionedError) vs
    `provision_vss` (the only INSTALL); the rag gate proves the consumer path makes no network call.
