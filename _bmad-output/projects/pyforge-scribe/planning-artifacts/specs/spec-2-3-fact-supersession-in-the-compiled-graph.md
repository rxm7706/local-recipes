---
title: 'Fact supersession in the compiled graph (Story 2.3)'
type: 'feature'
created: '2026-08-07'
status: 'in-review'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 'a65962b2'
---

<intent-contract>

## Intent

**Problem:** A decision that supersedes a prior one must invalidate — never
delete — the prior record, so historical accuracy survives.

**Approach:** The mechanism itself already exists as of Story 2.1/2.2:
`GraphNode.valid_until`/`superseded_by` (bi-temporal-lite, Story 2.1),
`GraphStore.invalidate_edge()` (Story 2.1), the additive `supersedes`
frontmatter field on `.claude/memory/*.md` (Story 2.1's `models.py`/
`capture.py` change), and `compile.py`'s `_apply_supersession()` pass
(written alongside Story 2.2 because a coherent `compile_graph()` needed it
to process `supersedes` references it reads off every memory record
regardless). **This story's job is to prove the full contract end-to-end**
with dedicated tests spanning capture → compile → query, since neither prior
story's test suite exercised the `supersedes` field being non-`None`.

## Boundaries & Constraints

**Always:**
- A memory record's `supersedes: "<type>/<slug>"` frontmatter field, when
  present and resolvable, causes `compile_graph()` to call
  `store.invalidate_edge(target_id, ended_at=<superseding record's
  valid_from>, superseded_by=<superseding record's id>)` on the target node.
- The target node remains present after invalidation: `iter_nodes()` and
  `query_by_citation()` both still return it, with `valid_until` set (not
  `None`) and `is_current is False` — traceable, distinguishable from the
  current/active record, never removed.
- The superseding (new) record's own node is unaffected — always `is_current
  is True` unless something else later supersedes IT.
- A dangling `supersedes` reference (names a record that doesn't exist / was
  never compiled into a node) is logged as a warning and skipped — an
  unattended nightly compile must not crash on it (already implemented in
  Story 2.2; this story adds a dedicated test proving it).

**Block If:** none.

**Never:**
- Do not add a `--supersedes` flag to `scribe capture`'s CLI surface — no AC
  requires it (the mechanism is exercised via `capture()`'s existing Python
  parameter, or by hand-editing a memory file's frontmatter, either of which
  already satisfies "a capture explicitly names a prior record as
  superseded"); adding a CLI flag now would be speculative surface area
  ahead of a concrete need (Simplicity First).
- Do not change `invalidate_edge()`'s signature or `_apply_supersession()`'s
  logic unless a test in this story's own I/O matrix proves it's wrong.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| End-to-end supersession | capture A (`project`, slug `plan-x`), then capture B with `supersedes="project/plan-x"`; run `compile_graph()` | graph has 2 nodes: `memory:project/plan-x` (`is_current=False`, `valid_until` set, `superseded_by` = B's node id) and B's node (`is_current=True`) | No error |
| Query the superseded record | `store.query_by_citation()` for A's file, or `iter_nodes()` | A's node IS present and distinguishable (`is_current=False`) from B's (`is_current=True`) | No error |
| Dangling reference | capture with `supersedes="project/does-not-exist"` | compile succeeds; a warning names the unresolved reference; no node is invalidated | Never raises |
| Re-compile after supersession, no further source change | run `compile_graph()` twice after the supersession capture | both runs produce byte-identical store output (idempotency holds even with an active supersession edge) | No error |
| Chained supersession | A superseded by B, B superseded by C | A and B both `is_current=False` with their own distinct `superseded_by`; C is the only current node | No error |

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py` — no change expected; `_apply_supersession()` (already written) is the target under test
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store.py` — no change expected; `invalidate_edge()` (already written) is the target under test
- `src/shared/packages/pyforge-scribe/tests/unit/test_supersession.py` (NEW) — end-to-end capture→compile→query coverage
- `_bmad-output/projects/pyforge-scribe/planning-artifacts/epics-with-stories.md` (L48-62) — Story 2.3's source ACs

## Tasks & Acceptance

**Execution:**
- [x] `test_supersession.py` -- end-to-end happy path, dangling reference, re-compile idempotency with an active edge, chained supersession

**Acceptance Criteria:**
- Given a capture explicitly names a prior record as superseded, when `scribe graph compile` processes it, then the prior record's node remains present in the graph, marked with ended validity, rather than removed (FR-10).
- And a query against the graph for the superseded record still resolves it (traceable), distinguishing it from the current/active record.

## Design Notes

- **Why no new production code was needed:** `_apply_supersession()`
  (compile.py) and `invalidate_edge()` (graph_store.py) were written during
  Story 2.2 because `compile_graph()`'s design required reading the
  `supersedes` field off every memory record it already parses regardless
  of whether the field is set — deferring that read to a later story would
  have meant re-parsing every file a second time. This story validates that
  decision was correct rather than re-implementing it; if the new tests had
  found a defect, this spec's Tasks would have grown a fix, but they did
  not.
- **Chained supersession** (A→B→C) is exercised because it is the one
  topology where a naive `invalidate_edge()` implementation might
  accidentally cascade-invalidate transitively or lose the distinct
  `superseded_by` pointer per hop — proven correct by test, not assumed.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` -- expected: full suite green
- `git diff --stat` -- expected: only `test_supersession.py` (new) changed

## Review Triage Log

- **Docstring-vs-behavior drift:** re-read `compile.py`'s `_apply_supersession()`
  docstring against its actual behavior — accurate; confirmed the dangling-
  reference path logs and continues rather than raising, matching the
  docstring's claim.
- **Idempotency with an active edge:** the new re-compile test proves
  `invalidate_edge()`'s effect (setting `valid_until`/`superseded_by`) is
  itself recomputed identically on each run (the superseding record's
  `supersedes` field is read fresh from disk every time, and its
  `valid_from` is derived from the SAME file mtime both times) -- no drift
  between runs.
- **No findings requiring a production code change** -- both target modules'
  existing implementation (from Stories 2.1/2.2) passed every new test in
  this story's I/O matrix on the first run.


## Adversarial review pass (2026-08-07, Blind Hunter + Edge Case Hunter)

Dispatched with the diff file path only, no shared context.

- `medium` `patch` **TOCTOU crash risk in `_apply_supersession`.** `.claude/memory/<type>/*.md` is globbed and parsed TWICE -- once in `_read_memory_surface`, again independently in `_apply_supersession` (rather than reusing the already-parsed records from the first pass). The second pass's `parse_capture_file` call only caught `ValueError`; a file that existed during the first scan but was removed before the second (a real race an unattended nightly compile can hit -- a concurrent `scribe capture` cleanup, or simply normal repo activity while the cron fires) raised an uncaught `FileNotFoundError`, crashing the whole compile instead of degrading like every other surface. Fixed: the loop now also catches `OSError`, logging a warning and skipping, matching the module's own documented "a single degraded surface does not abort the rest of the compile" guarantee. New test: `test_memory_file_removed_between_the_two_read_passes_is_skipped_not_a_crash`.

**Re-verification (2026-08-07, after the patch):** `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` -- **88 passed** (full suite).

**Follow-up review recommendation (updated): false** -- narrow fix, covered by a dedicated regression test.
