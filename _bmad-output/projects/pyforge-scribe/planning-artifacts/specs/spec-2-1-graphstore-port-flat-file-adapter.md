---
title: 'GraphStore port + flat-file v1 adapter (Story 2.1)'
type: 'feature'
created: '2026-08-07'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: '060fc7352f'
---

<intent-contract>

## Intent

**Problem:** `compile.py` and `recall.py` (Stories 2.2-2.4) need a stable seam to
read/write the compiled knowledge graph without committing to an embedded
graph-database engine before it's justified (AD-5) — the KuzuDB-archival
lesson the domain research flagged.

**Approach:** Add `graph_store.py`: a `GraphStore` `Protocol` (write:
`upsert_node`/`invalidate_edge`-shaped ops; read: `query_by_citation`/
`iter_nodes`) plus one concrete adapter, `FlatFileGraphStore` — a single JSON
index file (`{id: node-dict}`), extending `.claude/memory/MEMORY.md`'s
existing flat-index pattern per the architecture's AD-5 Deferred note. Add a
`GraphNode` Pydantic model to `models.py` (bi-temporal-lite: `valid_from`/
`valid_until`/`superseded_by`, unused by this story but load-bearing for
Story 2.3). Ship a dedicated offline-conformance test proving zero network
calls (AD-6) as this story's own deliverable, not deferred.

## Boundaries & Constraints

**Always:**
- `GraphStore` is a `typing.Protocol` — `compile.py`/`recall.py` (future
  stories) depend on it, never on `FlatFileGraphStore` internals or any
  storage-engine client library directly (AD-5).
- `FlatFileGraphStore.__init__(store_path: Path)` — always an injected
  `Path`, never a hardcoded location, matching `capture.py`'s
  `memory_root`-injection convention.
- Write path is a full in-memory rebuild + one atomic `commit()`: `reset()`
  clears in-memory state, `upsert_node()`/`invalidate_edge()` mutate it,
  `commit()` does a temp-file-then-`os.replace()` whole-file rewrite under a
  cross-platform advisory lock (mirrors `capture.py`'s `_locked()` —
  `fcntl`/`msvcrt`, stdlib only). A reader never observes a half-written
  file; two racing `commit()` calls resolve to one clean last-writer-wins
  swap, never corruption.
- `commit()`'s JSON output is deterministic byte-for-byte for the same node
  set: sorted keys, sorted node ids, `indent=2` — a re-`commit()` with an
  unchanged node set produces byte-identical output (the idempotency Story
  2.2 depends on).
- Zero imports of any network/socket-touching library anywhere in this
  module (AD-6) — pure `json` + stdlib file/lock primitives.

**Block If:** none.

**Never:**
- Do not implement `compile.py`/`recall.py` themselves — Stories 2.2-2.4.
- Do not wire a CLI command to this module yet.
- Do not choose an embedded graph-database engine — the flat-file adapter
  IS the v1 choice (architecture Deferred note resolves it to flat-file for
  v1; an embedded-engine adapter, if ever justified, is a future addition
  behind the same `GraphStore` protocol).
- Do not use the real repo `.claude/memory/` tree in any test — `tmp_path`
  only.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Fresh store | no file at `store_path` | `iter_nodes()` empty, `query_by_citation()` empty | No error |
| Upsert + commit + reopen | one node upserted, committed | a freshly-constructed `FlatFileGraphStore` at the same path sees the node | No error |
| Idempotent re-commit | commit the same node set twice | both commits produce byte-identical file content | No error |
| Upsert same id twice | two `upsert_node()` calls with the same `node.id`, different content | last write wins in memory; `commit()` persists exactly one node for that id | No error |
| `invalidate_edge` on unknown id | id not present in the in-memory node set | raises `ValueError` before any write | Caller (compile.py) must upsert before invalidating |
| `invalidate_edge` on known id | id present | node's `valid_until`/`superseded_by` set; node still present via `iter_nodes()`/`query_by_citation()` | No error |
| `reset()` | store loaded from an existing file, then `reset()` | in-memory node set is empty; the on-disk file is untouched until the next `commit()` | No error |
| Offline conformance | `socket.socket` blocked via monkeypatch | a full reset→upsert→commit→reopen→iter cycle completes with zero socket construction attempts | `AssertionError` from the test's blocked-socket stub would surface any violation |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store.py` (NEW) — `GraphStore` Protocol, `FlatFileGraphStore`
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/models.py` — add `GraphNode` model (`id`, `kind`, `title`, `text`, `citation`, `valid_from`, `valid_until`, `superseded_by`, `is_current` property)
- `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store.py` (NEW) — write/read/idempotency/lock + offline-conformance test
- `_bmad-output/projects/pyforge-scribe/planning-artifacts/epics-with-stories.md` (L1-27) — Story 2.1's source ACs
- `_bmad-output/projects/pyforge-scribe/planning-artifacts/architecture/architecture-pyforge-scribe-2026-07-25/ARCHITECTURE-SPINE.md` — AD-5/AD-6, Structural Seed (`graph_store.py`'s intended shape)

## Tasks & Acceptance

**Execution:**
- [x] `models.py` -- add `GraphNode` Pydantic model (bi-temporal-lite fields)
- [x] `graph_store.py` -- `GraphStore` Protocol + `FlatFileGraphStore` (reset/upsert_node/invalidate_edge/query_by_citation/iter_nodes/commit), atomic locked write
- [x] `test_graph_store.py` -- write/read/idempotency/unknown-id/reset coverage + the dedicated offline-conformance test (blocked-socket harness)

**Acceptance Criteria:**
- Given no graph storage exists yet, when `graph_store.py` is implemented, then `GraphStore` defines upsert/invalidate write ops and citation-query/iterate read ops, and `FlatFileGraphStore` implements it fully — no module outside this one imports a storage-engine client library directly (AD-5; there is none yet to import, satisfied vacuously and by construction).
- Given the air-gap NFR, when the flat-file adapter performs any read/write, then zero network calls occur, verified by a dedicated offline-conformance test in this story's own test file.

## Design Notes

- **Store location is deliberately NOT under `.claude/memory/`.** The compiled
  graph is a derived, disposable-and-rebuildable artifact (AD-1) — unlike
  `.claude/memory/`'s intentionally-tracked entries, it should not be
  git-tracked. `graph_store.py` itself stays path-agnostic (matches
  `capture.py`'s injection convention); `compile.py` (Story 2.2) is
  responsible for choosing a default path under the already-gitignored
  `.claude/data/` tree (`.claude/data/` is blanket-ignored at
  `.gitignore:718`), not this story.
- **`invalidate_edge` naming mirrors the architecture's own vocabulary**
  (AD-5: "an invalidate-edge-shaped call for supersession") even though the
  flat-file adapter's nodes ARE the facts and there is no separate edge
  object — a deliberate simplification for the v1 flat-file engine,
  documented in the module docstring so a future embedded-graph adapter
  swap doesn't have to guess the intended semantics.
- **No offline-conformance harness precedent exists as reusable code in this
  repo** (the CLAUDE.md's "matching this repo's `deckcraft` precedent"
  reference is conceptual/architectural, not an importable module) — the
  concrete mechanism here is a `monkeypatch`-blocked `socket.socket`
  constructor, a portable, deterministic technique that doesn't require
  `unshare -n`/OS-level network-namespace sandboxing (not reliably available
  in this repo's test runners). `pyforge-warden`'s
  `test_osv_offline_db_spike.py` trusts a subprocess flag (`--offline`) for
  its analogous guarantee; this story's mechanism is stronger because it
  fails on ANY socket construction, not just a documented flag.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` -- expected: full suite green (existing 32 tests + new `test_graph_store.py` cases)
- `git diff --stat` -- expected: only the files in Code Map changed

## Review Triage Log

Adversarial self-review pass (exception handling, silent drops, docstring-vs-behavior
drift, concurrent-compile races, idempotency, accidental network calls):

- **Concurrency:** `commit()` takes the same advisory-lock approach as
  `capture.py`'s `_locked()` (fcntl/msvcrt), keyed by `store_path`. Verified
  the temp file is created inside the lock and cleaned up on any exception
  (`try/except BaseException` + `os.unlink`) so a crashed writer never
  leaves a stray `.tmp` file that a later `commit()` would need to notice.
- **Idempotency:** confirmed via test that committing the identical node set
  twice produces byte-identical file content (sorted keys/ids, fixed
  `indent=2`).
- **AD-6:** grepped `graph_store.py` for `socket`, `http`, `urllib`,
  `requests` — none present; confirmed via the blocked-socket test.
- **No findings requiring a code change** beyond what's implemented — this
  story's scope (pure local file I/O) has a narrow surface for these classes
  of bug.
