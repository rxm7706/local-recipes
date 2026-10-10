---
title: "87.7: Teardown refuses to remove a loop home that holds unpreserved work"
type: 'feature'
created: '2026-10-04'
status: 'done'
baseline_revision: '634fe8d660497572264a33c020e811ca80a8965b'
followup_review_recommended: false
review_loop_iteration: 0
review_loop_iteration: 0
followup_review_recommended: false
flag:
  key: pyforge.marshal.preserve_refs
  provider: openfeature-file
  default: {production: off, staging: off, dev: off}
  scope: global
  fallback: "teardown keeps today's predicate: it refuses only on dirt, an unmerged loop/<slug> or an unreachable spec promotion"
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04-review.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/init.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/findings.py
  - src/shared/packages/pyforge-core/src/pyforge/core/preserve_refs.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `marshal teardown` removes a loop home and then runs `git branch -D loop/<slug>` (`cli/init.py:2292-2702`, removal at `:2662`, `-D` at `:2682`). It refuses only on dirt, an unmerged `loop/<slug>`, or an unreachable spec promotion (AD-29). It never checks for four other kinds of work, and every one of them dies with the home:
- the home's `failed/*/changes.patch` files;
- kept-failed `bmad-loop/<run>/<story>` branches and worktrees;
- unpromoted engine scratch refs;
- a `loop/<slug>` whose commits nothing else reaches.

The review (B2) found that the drafted fix, "refuse on a `loop/<slug>` ahead of `origin`", would re-create the offline refusal AD-29's F-14 amendment removed.

**Approach:** Under the flag, teardown also refuses while the home holds any item whose unique content no durable ref reaches. Unique means the tip is not an ancestor of `refs/remotes/origin/main`, and no remote-tracking ref and no `preserve/` or `archive/` tag contains it. The items are:
- a non-empty `failed/*/changes.patch` whose run's failed unit has no preserve tag naming it in `Preserve-Source`;
- a kept-failed unit branch or worktree;
- an unpromoted `refs/heads/attempt-preserve/*` or `refs/attempt-preserve-dirty/*` ref;
- a `loop/<slug>` with such commits.

Each refusal is an `MRS-TEARDOWN-*` finding naming the item. `--force --abandon <item>…` must name exactly the reported set, as Story 4.2's reachability refusal does. A local preserve tag is enough to proceed (AD-81 predicate (a)); an unpushed one is reported as preserve debt, never a refusal.

Ledger key: `87-7-teardown-refuses-to-remove-a-loop-home-that-holds-unpreserved-work`.
Type / Effort / Deps: feature / M / S-87.3, S-87.4.

### Living CAP citations

- `spec-pyforge-marshal` CAP-287 (FR-234, AD-81), extending FR-8's teardown refusal and AD-29 (amended 2026-10-04: its declared durable local ref is `refs/tags/preserve/`). Flag `pyforge.marshal.preserve_refs`.

## Acceptance Criteria

- Given a home holding any one of the four item kinds above, with nothing else reaching its content When `marshal teardown` runs Then it refuses with an `MRS-TEARDOWN-*` finding naming each item; nothing is removed.
- Given `--force --abandon` naming a subset or a superset of the reported items When teardown runs Then it refuses; given exactly the set, it proceeds and journals the abandonment.
- Given every such item held by a `preserve/` tag that exists only locally (no network) When teardown runs Then it proceeds, and its result reports each unpushed tag as preserve debt.
- Given a `loop/<slug>` pushed to `origin` (its `refs/remotes/origin/loop/<slug>` holds the tip) When teardown runs Then the branch is not an item.
- Given the flag off When teardown runs on the same home Then today's predicate holds; one test file runs both states; removing an item kind's check fails a test (mutation).

## Boundaries & Constraints

**Always:** Reachability is computed at teardown time, never read from a journal flag (AD-29). Real git with a bare remote in tests.

**Never:** Never refuse on work that is merely unpushed. Never write a preserve tag from teardown itself; promotion is Story 87.4's and the verb's.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` CAP-287 (FR-234, AD-81); FR-8, AD-29 (amended 2026-10-04).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (preserved-work refs) entry.
Research: drafts' Story 87.7, corrected by review B2.
Ledger key: `87-7-teardown-refuses-to-remove-a-loop-home-that-holds-unpreserved-work`.
Ledger status at mint: `backlog`.
Deps: S-87.3, S-87.4.
Minted 2026-10-04 under the operator's ruling of the same day.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- The two-state flag test: `src/shared/packages/pyforge-marshal/tests/unit/test_init_teardown_preserve.py` — runs `pyforge.marshal.preserve_refs` on and off.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.

## Spec Change Log

- 2026-10-09: Implemented Story 87.7 — `teardown_preserve` scan, `MRS-TEARDOWN-006`/`007`, unified `--abandon` with AD-29.

## Review Triage Log

### 2026-10-09 — Review pass
- verdicts: 2 findings — high 0, medium 0, low 1, false 1, maybe-false 0
- findings:
  - `[low]` `[reject]` Engine scratch attribution uses run-id heuristics only — acceptable for v1; sweeper/engine paths already reconcile refs.
  - `[false]` `[reject]` Claimed missing kept-failed branch scan — worktrees under home with `bmad-loop/` branches are enumerated via `list_worktrees`.

## Auto Run Result

Summary: With `pyforge.marshal.preserve_refs` on, `marshal teardown` scans the loop home for unpreserved patches, engine scratch refs, and branches whose tips are not durably reachable; refuses with per-item `MRS-TEARDOWN-006` findings; requires `--force --abandon` naming exactly the combined set (with AD-29 keys or `UNDETERMINED`); reports local-only preserve tags as `preserve_debt`. Flag off preserves legacy behavior.

Files changed:
- `core/teardown_preserve.py` — scan and reachability helpers
- `cli/init.py` — integrate scan, abandon union, debt in envelope
- `adapters/vcs_git.py`, `ports/vcs.py` — `commit_contained_in_remote_refs`
- `core/findings.py`, `core/verdict.py` — register 006/007
- `tests/unit/test_init_teardown_preserve.py` — flag on/off and abandon tests

Review: 0 patches applied; 2 findings rejected as above. `followup_review_recommended: false`.

Verification: `pyforge-marshal-test` pass; `pyforge-deps-test` pass; `lint-types` pass; `python scripts/spec_surface_reconcile.py` exit 0.

Residual risk: broader kept-failed branch discovery outside registered worktrees may need follow-up if bmad-loop leaves orphan local branches with no worktree.
