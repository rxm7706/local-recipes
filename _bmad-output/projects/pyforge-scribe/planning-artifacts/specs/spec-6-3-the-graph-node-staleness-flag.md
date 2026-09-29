---
title: 'The graph-node staleness flag (Story 6.3, Epic 6)'
type: 'feature'
created: '2026-08-31'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
difficulty: medium
baseline_revision: 'b4b361354454173e7a1d439de517a817811036e1'
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-6-1-the-graphify-ingest-extra-and-its-move-list-verbs.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
warnings:
  - "Marshal Story 28.9 (planning-graph retrieval, pyforge-marshal project) consumes the `stale` field via the scribe grammar only, as its fifth acceptance criterion — no graphifyy/scribe internals import inside `pyforge.marshal`. Declared as an external consumer, not a co-dependency: this story ships and is verifiable standalone."
---

<intent-contract>

## Intent

**Problem:** Story 2.3's supersession is purely author-declared (`supersedes:` frontmatter)
— compile mechanically walks only those declared links. Nothing detects a node whose source
has moved with no such link, so a stale node looks exactly as authoritative as a current
one. This matters now that CAP-6 retrieval (marshal Story 28.9) serves graph nodes as
routing context: a silently stale node would feed wrong planning history into a story
iteration with no signal anything was wrong.

**Approach:** A comparison against Mem0's OSS memory layer (docs.mem0.ai) considered and
rejected porting its consolidation model — a per-write LLM tool-call deciding
ADD/UPDATE/DELETE/NOOP — because Scribe's memories are already structured; the only missing
signal is "did the world move since this was compiled," a timestamp comparison, not a
judgment call. `compile_graph` (which already walks git history for other surfaces,
`_read_git_surface`) gains one more field: a node is flagged `stale: true` when its source
file's latest git commit postdates the node's own `valid_from` and no `supersedes:` edge
points at it. Zero LLM calls, zero new dependency.

## Acceptance Criteria

- Given a node whose source file's latest git commit postdates the node's own `valid_from`
  and no `supersedes:` edge points at it, when compile runs, then the node is flagged
  `stale: true`.
- Given an unchanged source, or a node with a declared `supersedes:` edge pointing at it,
  when compile runs, then the node is never flagged stale.
- Given a retrieval that resolves to a stale-flagged node, when the answer is served, then
  the consumer falls back to its non-graph path rather than serving the stale node silently.
- Given the implementation, when inspected, then the check is a git-timestamp comparison
  only — no LLM call, no new external dependency, and Story 2.3's existing `supersedes:`
  mechanism is unchanged.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-scribe/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-scribe` only — never `scripts/bmad-switch`. Ledger
key `6-3-the-graph-node-staleness-flag`.

**Block If:** A change would call an LLM, add a new external dependency, or alter Story
2.3's `supersedes:` semantics rather than layering on top of them.

**Never:** An LLM-judged consolidation decision (Mem0's ADD/UPDATE/DELETE/NOOP pattern) —
already ruled out epic-wide (no `mem0.add` in place of `scribe capture`). Marking a node
stale by any signal other than its own source file's git history.

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py` (`_apply_supersession`
  and the `GraphNode` construction sites — the staleness check lands beside supersession,
  reusing the git-history read `_read_git_surface` already performs)
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/models.py` (`GraphNode`'s `stale`
  field, if not already carried)
- `.claude/skills/pyforge-scribe/active/pyforge-scribe/SKILL.md` (declare the `stale` field
  in the grammar consumers bind to)

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(stale-flagged on moved+undeclared source, never flagged on unchanged/superseded source, no
LLM call or new dependency introduced). Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 6.3 and `spec-marshal-token-economy` CAP-13. This is compile.py's
general surface, not the graphify extra specifically — every compiled surface (memlog,
changelog, retro, git, transcript) gets the same staleness signal, since Story 2.3's
supersession already applies epic-wide, not just to graphify nodes. Epic-homed under 6
because the graphify → marshal-retrieval consumer (Story 28.9) is what makes the gap matter
in practice, not because the mechanism is graphify-specific.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` — expected: pass, including this story's own new/updated test coverage.

## Spec Change Log

- 2026-08-31: drafted from `spec-marshal-token-economy` CAP-13 (minted the same day from a
  Mem0 OSS comparison against Story 2.3's author-declared-only supersession) — the
  compile-step half of a two-station capability; marshal Story 28.9 carries the consumer
  half as its fifth AC.

## Review Triage Log

### 2026-08-31 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4 (medium 3, low 1)
- defer: 0
- reject: 13
- addressed_findings:
  - `[low]` `[patch]` `src/shared/packages/pyforge-scribe/docs/cli-runbooks.md:43`'s
    example `scribe graph compile` output was stale against the new
    `compiled N node(s), M invalidated, K stale -> path` format `cli.py` now emits;
    updated the example line.
  - `[medium]` `[patch]` `graph_store_pg.py::query_similar()`'s SQL `WHERE` clause
    filtered `valid_until IS NULL` but not `stale` — since `recall.py::_answer_semantic()`
    excludes stale nodes only in Python, after the SQL `LIMIT` already truncated the
    candidate set, enough stale nodes ranked ahead of a valid one could starve it out
    of the window entirely. Added `AND stale = false` to the SQL predicate, mirroring
    the existing `valid_until IS NULL` idiom.
  - `[medium]` `[patch]` `graph_store_plane.py::query_similar()` had the identical gap
    (`WHERE n.valid_until IS NULL` with no `stale` predicate). Added `AND NOT n.stale`.
  - `[medium]` `[patch]` No test exercised `stale` surviving a commit/reopen round-trip
    against either durable backend (`test_graph_store_operations.py`'s shared
    parametrized suite's `_node()` helper never set `stale`; `test_graph_store_plane.py`
    never constructs a live `PlaneGraphStore` at all) — a future edit to either
    backend's hand-written SQL column list (the exact kind of edit this story itself
    made) could silently break `stale` persistence with no test catching it. Added a
    stale round-trip case to the shared suite and a live-duckdb round-trip test for
    `PlaneGraphStore`.

## Auto Run Result

**Summary:** Implemented Story 6.3 (CAP-13) — a git-timestamp-only `stale` flag on
`GraphNode`, set by a new `_apply_staleness()` pass in `compile_graph()` for every
still-current node whose citation's source file has a git commit postdating the node's
own `valid_from`, with no `supersedes:` edge naming it. `recall.py` excludes stale
nodes from candidacy on both the lexical and semantic paths, falling through to the
next resolvable candidate or the explicit "no grounded answer found" miss. Zero LLM
calls, zero new dependency; Story 2.3's `_apply_supersession()` is untouched.

**Files changed:**
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/models.py` — `GraphNode.stale: bool = False`.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py` — `_apply_staleness()`, `_git_latest_commit_time()`, `_staleness_source_path()`; `CompileResult.stale_count`.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py` — stale exclusion in `answer()` and `_answer_semantic()`.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` — `graph_compile` echo reports `stale_count`.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_pg.py` — `stale` column (migration + SELECT/INSERT) and SQL-level stale filter in `query_similar()` (review patch).
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_plane.py` — `stale` column (migration + SELECT/INSERT) and SQL-level stale filter in `query_similar()` (review patch).
- `.claude/skills/pyforge-scribe/0.1.0/pyforge-scribe/SKILL.md` — documents `GraphNode.stale` and the compile summary line for external consumers.
- `src/shared/packages/pyforge-scribe/docs/cli-runbooks.md` — example compile output updated to the new format (review patch).
- `src/shared/packages/pyforge-scribe/tests/unit/test_compile.py` — 8 new tests covering AC1/AC2/exemptions/degradation.
- `src/shared/packages/pyforge-scribe/tests/unit/test_recall.py` — 3 new tests covering AC3 (lexical + semantic exclusion, fall-through).
- `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_operations.py` — stale round-trip case added to the shared parametrized suite (review patch).
- `src/shared/packages/pyforge-scribe/tests/unit/test_graph_store_plane.py` — live-duckdb stale round-trip test, skips gracefully when `duckdb` isn't installed (review patch).

**Review findings breakdown:** 17 findings raised across 4 review layers (Blind Hunter,
Edge Case Hunter, Verification Gap, Intent Alignment). 4 patched, 0 deferred, 13
rejected (matched existing codebase convention, out of scope per the intent's own
Boundaries & Constraints, or low-value/speculative nitpicks — see Review Triage Log
above for the full breakdown and rationale).

**Follow-up review recommendation:** `true`. This pass's patched findings: high 0,
medium 3, low 1 → score = 3×3 + 1×1 = 10 ≥ 5.

**Verification performed:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` (post-implementation): 273 passed.
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` (post-patch, final): 275 passed, 1 skipped (the new live-duckdb round-trip test skips because `duckdb` is not a declared `pyforge-scribe` pixi dependency — confirmed via `pixi.toml`'s `[feature.pyforge-scribe.dependencies]`; its logic was manually validated against a real duckdb file in the `local-recipes` env, which does carry duckdb).
- Manually confirmed `graph_store_pg.py`'s new `stale = false` SQL predicate against a live PostgreSQL instance, and `graph_store_plane.py`'s equivalent against a real duckdb file (per the implementation subagent's report).

**Residual risks:**
- The live-duckdb round-trip test (`test_graph_store_plane.py`) skips rather than runs
  under the default `pyforge-scribe` pixi env, since `duckdb` isn't a declared
  dependency there. It runs for real only where duckdb happens to be installed
  (e.g. `local-recipes`). Adding `duckdb` as a `pyforge-scribe` test dependency was
  judged out of scope for this patch round.
- Staleness compares git *author* date (`%aI`) against `valid_from`; a rebase,
  cherry-pick, or `commit --amend` can preserve an original author date on a commit
  whose content changed materially later, which could understate staleness in that
  specific scenario. Reviewed and rejected as a patch: the AC's literal wording
  ("source file's latest git commit postdates … `valid_from`") doesn't specify
  author vs. committer date, and this matches the existing `_read_git_surface`
  convention in the same module.
- AC3's "the consumer falls back to its non-graph path" is implemented and tested
  only at scribe's own `recall.py` surface. The actual external-consumer fallback
  behavior (marshal's `bmad-build-auto` step-01 routing on a stale node) belongs to
  marshal Story 28.9 (`ready-for-dev`), per this spec's own frontmatter `warnings`
  and Design Notes — confirmed intentional two-station decomposition, not a gap in
  this story.
