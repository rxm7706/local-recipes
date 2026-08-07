---
title: 'scribe recall — grounded, cited answers (Story 2.4)'
type: 'feature'
created: '2026-08-07'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 'c16df8fe'
---

<intent-contract>

## Intent

**Problem:** `scribe recall "<query>"` is still an Epic-1 stub. A developer
or agent asking "why did we do X" has nowhere to get a grounded, cited
answer from the graph Stories 2.1-2.3 now compile.

**Approach:** Add `recall.py`: `answer(query, store, repo_root)` does
deterministic lexical (token-overlap) matching over the compiled graph's
ACTIVE (`is_current`) nodes — no LLM, no network call (AD-6, PRD Open
Question 3's "no-LLM-required" v1 default). Every returned answer's citation
is verified resolvable (file exists on disk, or a well-formed commit sha)
before being returned (AD-8) — an unresolvable citation is treated as no
match, never surfaced. No match above zero token overlap → an explicit
"no grounded answer found" result. Wire `scribe recall <query>` in `cli.py`
to call it, replacing the Epic-1 stub.

## Boundaries & Constraints

**Always:**
- Pure retrieval: query and node text are tokenized (lowercase
  alphanumeric runs, length > 1, stopword-filtered), scored by set
  intersection size. No generative synthesis, no LLM call, no network call
  anywhere in `recall.py`'s default path (AD-6).
- Only nodes with `is_current is True` are candidates for a default answer —
  a superseded fact (Story 2.3) is traceable but never surfaces as if it
  were still current.
- Deterministic ranking: highest overlap score first, ties broken by node id
  (lexical) — the SAME compiled graph file always produces the SAME answer
  for the SAME query, regardless of which operator/worktree runs it (FR-13;
  no randomness, no per-session state).
- Every grounded answer carries a citation verified resolvable at query time
  (file exists under `repo_root`, or `commit:<sha>` is a well-formed hex
  string) — an answer is never returned without one (AD-8). If the top-
  scoring candidate's citation fails resolution, fall through to the next
  candidate; if none resolve, return "no grounded answer found".
- `scribe recall`'s CLI command exits `0` for BOTH a grounded answer and an
  explicit "no grounded answer found" result (architecture's Consistency
  Conventions: only a hard failure is non-zero).
- Reads the compiled graph via `FlatFileGraphStore` only — `recall.py` never
  reads `.claude/memory/`, `.memlog.md`, or git directly; it queries the
  projection (Story 2.1's `GraphStore` port), never the raw capture log
  (architecture's Design Paradigm: "recall.py ... queries the compiled
  projection only, never the raw capture log directly").

**Block If:** none.

**Never:**
- Do not add an LLM-backed synthesis path in this story — the architecture's
  Deferred note leaves that choice open; this story implements ONLY the
  "must not require network reachability" default (AD-6), matching PRD Open
  Question 3's resolution to "no-LLM-required" for v1.
- Do not read `.claude/memory/` (or any Story-2.2 source surface) directly
  from `recall.py` — only through the compiled `GraphStore`.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Grounded match | graph has a node whose text/title shares tokens with the query | `RecallAnswer(grounded=True, text=..., citation=<resolvable path>)` | No error |
| No coverage | no node shares any token with the query | `RecallAnswer(grounded=False, text="no grounded answer found", citation=None)` | No error, never fabricated |
| Superseded-only match | the only token-overlapping node is `is_current=False` | not selected by default; falls through to the next candidate or "no grounded answer found" | No error |
| Unresolvable citation | top candidate's citation file was deleted after compile | skipped; next candidate (if any) considered; else "no grounded answer found" | Never returns an unverifiable citation |
| Determinism across operators | same query, same compiled graph file, two separate `FlatFileGraphStore` instances (simulating two worktrees) | byte-identical `RecallAnswer` | No error |
| Empty/no-op query | blank or stopword-only query string | "no grounded answer found" (zero query tokens) | No error |
| CLI, no compiled graph yet | `.claude/data/pyforge-scribe/graph.json` does not exist | `FlatFileGraphStore` loads as empty; CLI prints "no grounded answer found", exit 0 | No error, no crash |
| Offline conformance | any read during recall | zero network calls (AD-6) | Verified by test, reusing Story 2.1's blocked-socket pattern |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py` (NEW) — `RecallAnswer`, `answer()`, tokenizer, citation-resolution check
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` — wire `recall_cmd` to `answer()`, replacing the Epic-1 stub
- `src/shared/packages/pyforge-scribe/tests/unit/test_recall.py` (NEW)
- `src/shared/packages/pyforge-scribe/tests/unit/test_cli.py` — replace `test_recall_stub_touches_nothing_and_exits_0` with real-behavior coverage
- `_bmad-output/projects/pyforge-scribe/planning-artifacts/epics-with-stories.md` (L64-79) — Story 2.4's source ACs

## Tasks & Acceptance

**Execution:**
- [x] `recall.py` -- tokenizer, scoring, citation-resolution check, `answer()`
- [x] `cli.py` -- wire `recall <query>` to `answer()`
- [x] `test_recall.py` -- grounded/no-coverage/superseded-excluded/unresolvable-citation/determinism/offline-conformance
- [x] `test_cli.py` -- replace the stub test with real CLI coverage

**Acceptance Criteria:**
- Given the graph contains a record answering a query, when `scribe recall "<query>"` is run, then the response includes at least one citation resolvable to a real file/record in the repo — no response is returned without a resolvable citation (AD-8).
- Given a query has no relevant graph coverage, when `scribe recall` is run, then it returns an explicit "no grounded answer found" result.
- Given two different operators/worktrees run the identical query against the same compiled graph, when both complete, then both receive the identical grounded answer.
- And `scribe recall`'s default configuration performs zero required network calls (AD-6, no-LLM-required v1 default).

## Design Notes

- **Lexical token-overlap, not TF-IDF/embeddings:** the simplest scoring
  that satisfies "deterministic/lexical method, not an LLM call" (AD-6) and
  the determinism AC — no external model weights, no vector index, no
  additional dependency. A future ranking refinement is a drop-in
  replacement behind the same `answer()` signature.
- **Citation-resolution as a second filter, not a scoring input:** keeps the
  ranking logic simple (score by content overlap only) while still
  guaranteeing AD-8 — an unresolvable top match is skipped rather than
  silently downweighted, so the behavior is exactly "would have answered,
  but the citation didn't check out -> try the next one, or admit no
  grounded answer."
- **Superseded nodes are excluded from the DEFAULT answer set**, not from
  the graph — Story 2.3 already proved they remain queryable via
  `query_by_citation()`/`iter_nodes()`; `recall.py`'s exclusion is a
  presentation-layer choice (never present a stale fact as current), not a
  storage-layer one.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` -- expected: full suite green
- `git diff --stat` -- expected: only the files in Code Map changed

## Review Triage Log

- **AD-8 (no fabrication):** verified the "no grounded answer found" path is
  reached both when zero nodes share a token with the query AND when the
  only matching node's citation is unresolvable — the citation check is on
  the RETURN path, not just the initial candidate-gathering, so a match
  that later fails resolution can't slip through as `grounded=True`.
- **Determinism (FR-13):** verified via test that two INDEPENDENT
  `FlatFileGraphStore` instances loading the SAME on-disk graph file (no
  shared Python object, no cache) return byte-identical `RecallAnswer`s —
  proves the "single shared source, not per-session state" claim rather
  than just asserting the code has no obvious mutable global (it doesn't).
- **AD-6:** grepped `recall.py` for `socket`/`http`/`urllib`/`requests`/any
  LLM-client import — none; a dedicated blocked-socket test (mirroring
  Story 2.1's) runs a full query cycle with zero network calls.
- **Exit-code convention:** confirmed the CLI's "no grounded answer found"
  path exits `0` (architecture's Consistency Conventions table), not a
  non-zero code that would make an ungrounded-but-otherwise-successful
  query look like a hard failure to a caller.
- **No findings requiring further changes.**
