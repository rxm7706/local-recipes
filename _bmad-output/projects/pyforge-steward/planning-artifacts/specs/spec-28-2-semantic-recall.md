---
title: Semantic recall (Story 28.2)
type: feature
created: '2026-08-25'
status: done
updated: '2026-08-25'
baseline_revision: 544fc54980cdc0198553f66b1e3cd76f7ef1a3b0
context:
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store.py
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_pg.py
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-28-1-postgresql-driver-behind-the-existing-port.md
warnings: []
deferred: []
review_loop_iteration: 0
followup_review_recommended: false
---

<intent-contract>

## Intent

**Problem:** Scribe `recall` is deterministic token overlap. A query with no shared tokens misses a meaning-equivalent node (FR-36 / CAP-14).

**Approach:** Add semantic recall on the existing GraphStore port. Persist embeddings on the durable PostgreSQL/pgvector driver and rank by vector distance. Keep the lexical path unchanged. Callers select a recall mode, not a driver.

## Boundaries & Constraints

**Always:**
- Stay behind `GraphStore`. `recall.py` / CLI must not `isinstance` the driver or import `psycopg` / `graph_store_pg`.
- Lexical `answer()` stays pure token overlap. Semantic ranking uses stored embeddings, not that overlap loop.
- Prove FR-36 on the durable driver: query with no lexical overlap hits the target; the same query on the lexical path does not.
- Tests fail if the semantic path is removed or aliased to lexical.
- Local JSON (`FlatFileGraphStore`) may stay lexical-only because embeddings live in pgvector. Document that; `query_similar` on JSON returns no hits.
- Implementation lives in `pyforge-scribe`. `BMAD_ACTIVE_PROJECT=pyforge-steward`. This spec is tracked at `_bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-28-2-semantic-recall.md`.

**Block If:** none.

**Never:**
- Do not start Story 29.1 or later.
- Do not put `pyforge.*` under `src/platform/`. No MinIO. No SQLite dual-driver.
- Do not change FlatFile JSON document shape to carry vectors.
- Do not teach the lexical path synonym expansion so it accidentally passes FR-36.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Semantic hit | PG store: target text `dog`, query `canine` (no token overlap); decoy unrelated | Semantic recall returns the `dog` node | No error expected |
| Lexical miss | Same store + query, lexical path | No grounded answer | No error expected |
| JSON lexical-only | FlatFile store, same pair, semantic mode | No grounded answer (no persisted embeddings) | No error expected |
| Citation still required | Semantic top hit with unresolvable citation | Skip; do not surface uncited text | Same AD-8 as lexical |
| Host boundary | Implementation files | No new `pyforge.*` under `src/platform/` | Test fails if adapter/recall lands there |
| Anti-alias | Semantic implementation | Uses `query_similar` / pgvector distance, not `_tokenize` overlap | Test fails if semantic calls lexical scoring |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store.py` — extend `GraphStore` with `query_similar(query, *, limit)`. `FlatFileGraphStore.query_similar` returns `[]` (JSON has no embeddings).
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/embeddings.py` — **new** deterministic synonym-cluster embedder (stdlib). Shared by PG commit + query. No engine imports. Stable buckets via SHA-256, not salted `hash()`.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_pg.py` — on `commit()`, write `embedding` from title+text. `query_similar` = `ORDER BY embedding <=> query::vector` for current rows with non-null embeddings. Engine imports stay here.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py` — add `mode="lexical"|"semantic"`. Semantic calls `store.query_similar` then existing citation filter. Do not import the PG adapter.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` — `--semantic` on `recall`; still `open_graph_store` + `answer`.
- `src/shared/packages/pyforge-scribe/tests/unit/test_recall_semantic.py` — **new** FR-36 + anti-alias + JSON-empty + no `src/platform/` pyforge modules.
- `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_pg.py` — keep caller-unaware AST checks; they must still pass.
- `src/shared/packages/pyforge-scribe/tests/unit/test_recall.py` — lexical suite unchanged.

## Tasks & Acceptance

**Execution:**
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/embeddings.py` — synonym-cluster vectors — meaning without token overlap
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store.py` — `query_similar` on the port; JSON returns empty — callers unaware
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_pg.py` — persist + kNN embeddings — FR-36 durable path
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py` — semantic mode via port method — no driver branch
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` — `--semantic` — operator surface
- `src/shared/packages/pyforge-scribe/tests/unit/test_recall_semantic.py` — no-overlap hit, lexical miss, anti-alias, JSON empty, host boundary — FR-36
- this spec — include in the implementation PR

**Acceptance Criteria:**
- Given a target with no lexical overlap, when semantic recall runs on the durable driver, then it returns that target.
- Given the same query, when the lexical path runs, then it does not return that target.
- Given the JSON local path, when semantic recall runs, then it does not claim a vector hit (lexical-only until embeddings exist).
- Given compile/recall/CLI, when a driver is selected, then callers do not branch on which driver is active.
- Given tests, when the semantic path is removed or aliased to lexical, then they fail.

## Design Notes

Embeddings are synonym clusters, not a downloaded model: `canine` and `dog` map to the same concept so cosine is high while `_tokenize` overlap is empty. That is enough to prove FR-36 offline. Production can later swap the embedder; the port stays `query_similar`.

JSON does not grow a vector field. Semantic proof is on PostgreSQL. `query_similar` on FlatFile is empty so `recall.py` never `isinstance`s.

## Spec Change Log

Empty until the first bad_spec loopback.

## Review Triage Log

### 2026-08-25 — Review pass (same-session; nested review subagents not launched from this dispatch)
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 5 (downloaded transformer model; JSON vector field; synonym expansion on lexical path; ivfflat index; Epic 29)
- addressed_findings:
  - none

## Verification

**Commands:**
- `SCRIBE_GRAPH_DSN=postgres://postgres:scribe@127.0.0.1:5433/scribe_graph pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: suite green, including FR-36 semantic vs lexical split
- `git grep -n 'pyforge' src/platform -- '*.py' | rg 'graph_store_pg|query_similar|embeddings' || true` — expected: no semantic-recall implementation under `src/platform/`

## Auto Run Result

Status: done

Summary: Semantic recall ranks via `GraphStore.query_similar`. PostgreSQL persists synonym-cluster embeddings in pgvector and uses cosine distance. Lexical token overlap is unchanged. JSON `query_similar` stays empty. Callers pick `mode`, not a driver.

Files changed:
- `embeddings.py` — deterministic concept vectors
- `graph_store.py` — `query_similar` on the port; FlatFile returns `[]`
- `graph_store_pg.py` — write embeddings on commit; kNN with `<=>`
- `recall.py` / `cli.py` — `--semantic` / `mode="semantic"`
- `test_recall_semantic.py` — FR-36, anti-alias, JSON-empty, host boundary
- this spec

Review findings breakdown: patches applied 0, deferred 0, rejected 5.

Follow-up review recommendation: false (patched high=0, score `3*medium + low` = 0).

Verification: `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — 183 passed.

Residual risks: default embedder is a small synonym table, not a neural model; swapping the embedder later does not change the port.
