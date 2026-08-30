---
title: 'The graphify ingest extra and its move-list verbs (Story 6.1, Epic 6)'
type: 'feature'
created: '2026-08-30'
status: 'done'
baseline_revision: '6cf3a6ed7776161a09c510c42ea640cbc425be73'
review_loop_iteration: 0
followup_review_recommended: true
difficulty: heavy
deferred:
  - summary: >-
      The graphify "on" path's tests structurally skip in the only wired
      `pyforge-scribe-test` command, so a future `graphify` API drift would
      ship undetected by normal verification.
    evidence: |-
      No pixi environment pairs the built `pyforge-scribe` package with
      `graphifyy` — `graphifyy` lives only under `[feature.local-recipes...]`
      in pixi.toml, which does not build/install `pyforge-scribe`. The six
      `pytest.importorskip("graphify", ...)`-gated tests always skip under
      `pixi run -e pyforge-scribe pyforge-scribe-test`. Manually verified the
      real integration is correct today via an ad hoc PYTHONPATH bridge
      pairing graphify's site-packages with the pyforge-scribe env (252
      passed, 0 skipped) — but there is no standing CI-wired proof of this,
      and adding `graphifyy` (network/tree-sitter-parser-heavy) as a hard dep
      of the lean `pyforge-scribe` env is a real env-bloat tradeoff the
      implementer deliberately declined, so the fix needs a scoped decision
      (e.g. a dedicated test-only env/task), not a blind patch.
    location: >-
      src/shared/packages/pyforge-scribe/tests/unit/test_extras_graphify.py;
      pixi.toml [feature.pyforge-scribe.dependencies]
    severity: medium
  - summary: >-
      The graphify ingest emits generic kind="code" nodes with no linkage to
      Dream/PRD/spec_id, narrower than the Design Notes' quoted stack.md
      vision ("link functions to Dream/PRD/spec_id").
    evidence: |-
      This story's own Acceptance Criteria do not require spec_id/Dream/PRD
      linkage (only the Design Notes quote stack.md's longer-term framing),
      so it is out of THIS story's contract — but marshal Story 28.9
      (planning-corpus retrieval) is a named future consumer that will likely
      need this linkage and doesn't have it yet.
    location: src/shared/packages/pyforge-scribe/src/pyforge/scribe/extras/graphify.py
    severity: low
  - summary: >-
      `build_graphify_report()`'s god-node list truncates at `top_n` with no
      indication when the real count exceeds it.
    evidence: |-
      `god_nodes_fn(graph, top_n=top_n)` returns an already-truncated list;
      indicating truncation would need calling with a higher/unbounded top_n
      and slicing locally, which needs verifying against graphify's actual
      API rather than a blind one-line fix.
    location: src/shared/packages/pyforge-scribe/src/pyforge/scribe/extras/graphify.py
    severity: low
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-unifying-strategy/stack.md
  - docs/dreams/pyforge-unifying-strategy.md
warnings:
  - Two consumers are waiting on this extra's grammar — the foundry-cutover move-list
    (docs/dreams/pyforge-target-monorepo.md) and marshal Story 28.9 (planning-corpus
    retrieval). Declare the grammar in the scribe SKILL.md so consumers bind to it, not to
    internals.
---

<intent-contract>

## Intent

**Problem:** The estate locks `graphifyy` (≥0.9.44, MIT) and the unifying-strategy stack
schedules it "bind now" behind Scribe, but no story builds the binding. Meanwhile the
foundry cutover needs a move list (host `import pyforge.*` sites, `sys.path` inserts,
`five_tier` roots, CFE callers) and marshal's token economy needs a queryable planning
graph — both would otherwise hand-roll their own graphify use.

**Approach:** Bind graphifyy as an **optional `compile_surface` ingest extra** (the
Grounding 2026-08-30 port contract): when enabled, folder ingest writes `GraphNode`s
*through* the `graph_store` persist port (`open_graph_store`, Story 4.1's CAP-18 plugins).
Add report verbs on the scribe grammar (`scribe index …`) that emit a GRAPH_REPORT-style
summary (incl. God-node findings) and the move list — derived, gitignored artifacts, like
`graph.json`. Extras are off by default (air-gap).

## Acceptance Criteria

- Given the extra absent or off (default), when a compile runs, then behavior is identical
  to today's six builtins — proven by an off-mode test.
- Given the extra on, when a folder is ingested, then `GraphNode`s are written through the
  persist port — no parallel store, no second persistence format.
- Given the report verbs, when run against the repo, then a GRAPH_REPORT-style summary
  (incl. God-node findings) and a move list (host `import pyforge.*` sites, `sys.path`
  inserts, `five_tier` roots, CFE callers) land as derived, gitignored artifacts.
- Given the implementation, when inspected, then graphifyy is imported only inside the
  extra adapter, and no foundry-root `graphify-out/` product dir is created.

## Boundaries & Constraints

**Always:** Write artifacts under `_bmad-output/projects/pyforge-scribe/planning-artifacts/`
literally. `BMAD_ACTIVE_PROJECT=pyforge-scribe` only — never `scripts/bmad-switch`. Ledger
key `6-1-the-graphify-ingest-extra-and-its-move-list-verbs`. AD-1 (append-only capture is
the only mutation path), AD-2 (write boundary), AD-6 (air-gap: extras off by default) all
bind.

**Block If:** A change would create a second graph store-of-record, alter the `GraphStore`
protocol, or put graphify output anywhere a detector treats as tracked product surface.

**Never:** A `mem0` binding (out of this epic). A Kedro project. Publishing any graph
metric as a PR-gate verdict (Warden doctrine).

</intent-contract>

## Code Map

- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py` (compile_surface fan-in — extra hook point)
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store_plugins.py` + `graph_store.py` (persist port, Story 4.1 — read-only protocol)
- graphify extra adapter (new, e.g. `pyforge/scribe/extras/graphify.py`; optional dependency)
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` (`scribe index` verbs)
- `.claude/skills/pyforge-scribe/active/pyforge-scribe/SKILL.md` (declare the consumer grammar)

## Tasks & Acceptance

**Execution:** Implement the Approach. Add station-owned tests that fail if ACs are violated
(off-mode identical, port-only writes, report/move-list artifacts derived + gitignored,
adapter-only import). Land this spec in `planning-artifacts/specs/`.

**Acceptance Criteria:** Same as Intent Contract.

## Design Notes

Bind to epics.md Story 6.1. The stack.md row: "`cocoindex` + `graphifyy` | scribe |
`scribe index`: AST graph + incremental index; link functions to Dream/PRD/spec_id |
**bind**". The Grounding rules: "behind GraphStore" means ingest writes through the persist
port; extras off by default. Consumers bind to the declared grammar only — marshal Story
28.9 explicitly forbids importing graph internals, so whatever this story declares in the
SKILL.md is the contract they get.

## Spec Change Log

- 2026-08-30: drafted as Epic 6 preflight (unifying-strategy stack.md "bind now" rows; pairs with marshal Epic 28's token-economy consumers)

## Review Triage Log

### 2026-08-30 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7 (high 0, medium 0, low 7)
- defer: 3 (high 0, medium 1, low 2)
- reject: 6 (high 0, medium 0, low 6)
- addressed_findings:
  - `[medium]` `[patch]` (found during diff construction, before the 4 formal review layers ran) A pre-existing, passing assertion (`assert "[source: session-a.jsonl:L1]" in output`) was deleted from `test_graph_compile_registers_transcript_surface_and_recall_finds_it` in `test_cli.py` with no functional reason — restored it and confirmed it still passes (both standalone and in the full suite).
  - `[low]` `[patch]` `compile.py::_read_graphify_surface`'s docstring overclaimed off-mode import-graph identity (the local `pyforge.scribe.extras.graphify` wrapper module import is unconditional; only the third-party `graphify` package's import is truly deferred) — reworded for accuracy.
  - `[low]` `[patch]` `docs/cli-runbooks.md` was not updated for the new `--extra`/`--no-extra` flag, `SCRIBE_GRAPHIFY_EXTRA`, or the `scribe index report`/`scribe index move-list` commands — added.
  - `[low]` `[patch]` `SKILL.md`'s `## Overview`/`## Key Exports` still said "4 CLI exports" and omitted `index_report`/`index_move_list` — updated the count and export table.
  - `[low]` `[patch]` `SKILL.md`'s `## Usage` claimed present-tense that marshal Story 28.9 "consumes" the `scribe index` grammar; that story is still `ready-for-dev` (unimplemented) — reworded to future/intended tense.
  - `[low]` `[patch]` `pyproject.toml`'s new `graphify` extra (`graphifyy>=0.9.51`) had no upper bound despite binding to `graphify.extract`/`graphify.build`/`graphify.analyze` internals rather than a documented stable API — added a conservative upper bound.
  - `[low]` `[patch]` `move_list_to_document()` baked the caller's absolute, machine-local `repo_root` path into the derived JSON artifact, hurting portability/diffability of an artifact meant for comparison — removed the absolute path from the document (all entries are already repo-relative).
  - `[low]` `[patch]` `SKILL.md`'s `## Key Types` omitted the three new public dataclasses (`GraphifyReport`, `GraphifyIngestResult`, `MoveListFinding`) — added.

Deferred findings (see frontmatter `deferred:`): the graphify "on" path's tests structurally skip in the only wired `pyforge-scribe-test` command (no pixi env pairs the built `pyforge-scribe` package with `graphifyy`) — verified manually correct via an ad hoc PYTHONPATH bridge (252 passed, 0 skipped) but with no standing CI-wired proof; the shipped ingest emits generic `kind="code"` nodes with no linkage to Dream/PRD/spec_id, narrowing the Design Notes' quoted longer-term stack.md vision (not required by this story's own ACs); `build_graphify_report()`'s god-node list truncates at `top_n` with no indication when the real count exceeds it.

Rejected (noise or already-correct-by-design, dropped silently): narrow exception handling in `_read_graphify_surface`/`index_report` (matches the existing `_read_git_surface` convention of catching specific known failure modes, not broad `Exception`); a code node's citation resolving to `"."` when `source_file` is empty (already degrades gracefully per `recall.py`'s AD-8 unresolvable-citation doctrine, never a crash); an untested `os.environ.setdefault("GRAPHIFY_OUT", ".")` side effect (explicitly documented as redundant defense-in-depth — the real guarantee is the explicit `cache_root` pin, confirmed by testing); duplicated directory-exclusion name lists across three call sites (stylistic, no concrete failure scenario); a claimed loosened `node_count >= …` assertion in `test_graphify_extra_on_writes_code_nodes_through_the_store` (not present in the actual diff — the test asserts `code_nodes` truthiness and per-node citation resolvability, not `node_count`).

## Auto Run Result

**Summary:** Bound `graphifyy` (import name `graphify`) as an optional `compile_surface`
ingest extra for `pyforge-scribe`, off by default (`SCRIBE_GRAPHIFY_EXTRA`, AD-6 air-gap).
When enabled, `scribe graph compile [--extra]` ingests AST code-structure nodes
(`kind="code"`) through the existing `GraphStore` persist port — no parallel store. Added
`scribe index report [--path]` (GRAPH_REPORT-style summary + god-node findings) and
`scribe index move-list` (foundry-cutover move list: host `import pyforge.*` sites,
`sys.path` inserts, `five_tier` roots, CFE callers), both writing derived, gitignored
artifacts under `.claude/data/pyforge-scribe/graphify/`. `graphify` is imported only inside
`pyforge/scribe/extras/graphify.py`, lazily, inside a function.

**Files changed** (12 files, +1296/-26):
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/extras/__init__.py` (new) — extras package marker.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/extras/graphify.py` (new, 387 lines) — the graphify adapter: `graphify_extra_enabled()`, `ingest_graphify_surface()`, `build_graphify_report()`, `scan_move_list()`/`move_list_to_document()`.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py` — new `graphify_extra`/`graphify_root` kwargs on `compile_graph()`; `_read_graphify_surface()` fan-in, off by default.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py` — `scribe graph compile --extra/--no-extra`; new `scribe index report`/`scribe index move-list` commands.
- `src/shared/packages/pyforge-scribe/src/pyforge/scribe/models.py` — `GraphNodeKind` gains `"code"`.
- `src/shared/packages/pyforge-scribe/pyproject.toml` — `[project.optional-dependencies] graphify = ["graphifyy>=0.9.51,<0.10"]`; deliberately not a hard dep of the lean `pyforge-scribe` pixi feature (air-gap).
- `src/shared/packages/pyforge-scribe/docs/cli-runbooks.md` — documented the new flag, env var, and `index` verbs.
- `.claude/skills/pyforge-scribe/0.1.0/pyforge-scribe/SKILL.md` — declared the new grammar (Design Notes' consumer-binding requirement), updated export counts/Key Types, corrected the marshal 28.9 tense.
- Tests: new `tests/unit/test_extras_graphify.py` (25 cases); additions to `test_compile.py` and `test_cli.py` covering off-mode, on-mode, degrade-on-unavailable, idempotency, and the two CLI verbs. Also restored a pre-existing assertion in `test_cli.py` that had been dropped without cause (see Review Triage Log).

**Review findings breakdown:** 16 findings across 4 parallel review layers (Blind Hunter, Edge Case Hunter, Verification Gap, Intent Alignment Auditor) — 0 intent_gap, 0 bad_spec, 7 patched (all low severity), 3 deferred (1 medium, 2 low — see frontmatter `deferred:`), 6 rejected. Full detail in Review Triage Log above. One additional issue (a deleted passing test assertion) was found and fixed during diff construction, before the formal review layers ran.

**Follow-up review recommendation:** This pass's `patch`-triaged findings: 7, all low severity. Score = 3×0 (medium) + 1×7 (low) = 7 ≥ 5, and none were high severity → `followup_review_recommended: true`.

**Verification performed:**
- `pixi run -e pyforge-scribe pyforge-scribe-test` (lean, air-gapped env, no `graphifyy` installed): 247 passed, 6 skipped (exactly the graphify-dependent tests, correctly `importorskip`-skipped) — proves the off-mode path needs nothing from this extra.
- Independently re-verified the "extra on" path for real (not just trusting the subagent's report): built a minimal, uncontaminated PYTHONPATH bridge exposing only `graphify` + its actual runtime deps (networkx, numpy, rapidfuzz, 25 tree-sitter grammars) from the `local-recipes` env's site-packages into the `pyforge-scribe` env — avoiding a first, contaminated attempt that pulled in unrelated stations' entry points and caused unrelated `PluginError`s. Result: 253 passed, 0 skipped, both before and after the patch round.
- Manual CLI smoke test against this real repo: `scribe index move-list` (1134 findings across 4 categories) and `scribe index report --path src/shared/packages/pyforge-scribe/src` (315 nodes, 568 edges, 10 god nodes) both produced sensible real output; confirmed no `graphify-out/` directory ever appears anywhere; confirmed derived artifacts land under the already-gitignored `.claude/data/` (`git check-ignore` confirmed) and leave `git status` clean.
- Confirmed `graphify`/`graphifyy` is imported only inside `extras/graphify.py`, and only inside functions (lazy import) — `compile.py`/`cli.py` import only this package's own wrapper functions.
- Confirmed `move_list_to_document()`'s new no-`repo_root` shape via a fresh CLI run post-patch.
- `ruff check` on all touched/new files: no new findings.

**Residual risks:** the graphify "on" path has no CI-wired verification (deferred, medium severity — see frontmatter); the shipped ingest doesn't yet link nodes to Dream/PRD/spec_id (deferred, low, out of this story's AC scope); `build_graphify_report()`'s god-node list doesn't indicate truncation (deferred, low). None of these affect the four literal Acceptance Criteria, which are all independently verified met.
