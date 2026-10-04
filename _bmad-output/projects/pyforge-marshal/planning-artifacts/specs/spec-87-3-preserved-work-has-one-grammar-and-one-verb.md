---
title: "87.3: Preserved work has one grammar and one verb"
type: 'feature'
created: '2026-10-04'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
flag:
  key: pyforge.marshal.preserve_refs
  provider: openfeature-file
  default: {production: off, staging: off, dev: off}
  scope: global
  fallback: "the `marshal preserve` verb is listed disabled and refuses with the usage exit code; nothing calls pyforge.core.preserve_refs, so no preserve tag is written"
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-core/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04-review.md
  - src/shared/packages/pyforge-core/src/pyforge/core/landing_evidence.py
  - src/shared/packages/pyforge-core/src/pyforge/core/flags.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/main.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/mcp/parity.py
  - scripts/deferred_work_intake.py
  - src/platform/config/flags.json
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Preserved work has nine names and no parser. Five scripts and three marshal modules each hand-roll knowledge of `attempt-preserve/` or `rescue/dangling-`. Nothing writes a preserve with provenance, and nothing lists what is preserved by station, story or producer. AD-81 needs one grammar every producer and reader imports, on the AD-73 `landing_evidence` precedent, and one verb an operator or a skill can call.

**Approach:**
- Add `pyforge.core.preserve_refs`. It is stdlib-only and importable by path from a stdlib-only script (the `sys.path` precedent of `scripts/deferred_work_intake.py:32-35`), and it imports no `pyforge.<station>`.
- **Names.** It renders and parses `refs/tags/preserve/<project-slug>/<N.M>/<producer>-<sha8>` and `refs/tags/preserve/unbound/<producer>-<sha8>`, with no date in either. The producer vocabulary is closed: `bmad-loop`, `intent-gap`, `dispatch`, `build`, `sweep`, `workspace`, `dangling`, `hand`. It also renders and parses the archive twins `refs/tags/archive/heads/<branch>` and `refs/tags/archive/tags/<tag>`, which retirement uses.
- **Snapshot.** For a dirty worktree it commits the working tree, untracked non-ignored files included, the way `BL/verify.py` `snapshot_worktree` does, with no branch, HEAD or index moved.
- **Tag.** It writes an annotated tag with the seven trailers `Preserve-Producer`, `Preserve-Provenance` (`machine|human`), `Preserve-Reason`, `Preserve-Source`, `Preserve-Run`, `Preserve-Journal` and `Preserve-Commit`.
- **Dedup.** The same name on the same object is a no-op, and the same name on a different object is refused. A story whose tree equals an existing preserve's tree is a no-op.
- **List.** It lists preserves with their trailers parsed and a derived state: `open`, or `landed` when the commit is an ancestor of `refs/remotes/origin/main`. Story 87.15 adds `retired`, read from the retirement ledger.
- **Verb.** `marshal preserve tag|list` sits over the module, behind the flag. The marshal MCP face carries it, so `test_cli_tool_parity` stays green.
- This story writes **local** tags only. Pushing, the content gate, the caps and `retire` are Story 87.15. A local tag already satisfies AD-81's predicate (a), so an unpushed one is debt, never a refusal.

Ledger key: `87-3-preserved-work-has-one-grammar-and-one-verb`.
Type / Effort / Deps: feature / M / —.

### Living CAP citations

- `spec-pyforge-marshal` CAP-287 (FR-234, AD-81), co-governed by `spec-pyforge-core`: the operator ruled on 2026-10-04 that the grammar lives in `pyforge.core.preserve_refs`, with no new core CAP. Flag `pyforge.marshal.preserve_refs`, owner marshal (`spec-feature-flag-governance` Q1/Q3).

## Acceptance Criteria

- Given every producer and both shapes When a name is rendered, then parsed Then it round-trips; no rendered name contains a date; any other name under `refs/tags/preserve/` is rejected with a named error; archive names round-trip the same way.
- Given the tree When a pyforge-core meta-test scans `src/` and `scripts/` Then it fails on any module outside `preserve_refs` that matches a `refs/tags/preserve/` name by regex (scoped to that leading segment; today's `attempt-preserve/` matches are not caught).
- Given a stdlib-only interpreter with only `src/shared/packages/pyforge-core/src` on `sys.path` When `pyforge.core.preserve_refs` is imported Then it imports, and a meta-test pins that it imports no third-party or `pyforge.<station>` module.
- Given a dirty worktree with a modified tracked file and an untracked non-ignored file When `marshal preserve tag --story <slug> <N.M> --producer hand --from <worktree>` runs Then one local annotated tag exists whose commit's tree equals the working tree, untracked file included; no branch, HEAD or index moved; all seven trailers are present.
- Given the same object again, or another commit with an identical tree for the same story When it runs Then it is a no-op; the same name on a different object is refused.
- Given preserves for two stories, one of whose commits is an ancestor of `origin/main` When `marshal preserve list --json` runs with `--station`, `--story`, `--producer` or `--state open|landed` Then the filter holds and every trailer is parsed.
- Given the flag off When `marshal --help` and `marshal preserve tag …` run Then the verb is listed as disabled and refuses with the usage exit code and a flag-off message; no tag is written.
- Given the flag on and off When the tests run Then one test file runs both states (the testing kit's `flag_states`); removing the round-trip, the no-branch-move or the dedup rule fails a test (mutation).

## Boundaries & Constraints

**Always:** Stdlib only in the core module. Full refnames. Real git and a bare remote in tests. Journal-before-success where the verb journals (AD-6).

**Never:** Never push, move or delete a tag (pushing is Story 87.15). Never put a date in a name. Never import `pyforge.marshal` from core. Never edit bmad-loop.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` CAP-287 (FR-234, AD-81); co-governor `spec-pyforge-core` (memlog decision 2026-10-04).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (preserved-work refs) entry.
Research: drafts' Story 87.3, split by the review (minor 5); M8 (grammar in core).
Ledger key: `87-3-preserved-work-has-one-grammar-and-one-verb`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-04 under the operator's ruling of the same day.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-core pyforge-core-test` — expected: pass (the grammar, snapshot and meta-tests live in pyforge-core).
- The two-state flag test: `src/shared/packages/pyforge-marshal/tests/unit/test_preserve_cli.py` — runs `pyforge.marshal.preserve_refs` on and off.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.

## Spec Change Log

- No change yet.

## Review Triage Log

- No review has run yet.
