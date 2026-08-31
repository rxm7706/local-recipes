---
title: 'The graph-node staleness flag (Story 6.3, Epic 6)'
type: 'feature'
created: '2026-08-31'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
difficulty: medium
context:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-6-1-the-graphify-ingest-extra-and-its-move-list-verbs.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-marshal-token-economy/SPEC.md
warnings:
  - Marshal Story 28.9 (planning-graph retrieval, pyforge-marshal project) consumes the
    `stale` field via the scribe grammar only, as its fifth acceptance criterion — no
    graphifyy/scribe internals import inside `pyforge.marshal`. Declared as an external
    consumer, not a co-dependency: this story ships and is verifiable standalone.
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
