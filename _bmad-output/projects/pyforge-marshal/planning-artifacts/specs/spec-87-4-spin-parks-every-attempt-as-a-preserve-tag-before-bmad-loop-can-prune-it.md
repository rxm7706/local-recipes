---
title: "87.4: Spin parks every attempt as a preserve tag before bmad-loop can prune it"
type: 'feature'
created: '2026-10-04'
status: 'done'
baseline_revision: d04dd6475647896d9dccd99dbf2424a23dce0873
review_loop_iteration: 0
followup_review_recommended: false
flag:
  key: pyforge.marshal.preserve_refs
  provider: openfeature-file
  default: {production: off, staging: off, dev: off}
  scope: global
  fallback: "spin keeps today's behaviour: the intent gap parks an attempt-preserve/* branch or a changes.patch, and no engine preserve is promoted"
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04-review.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/__main__.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/intent_gap_preserve.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/supervisor/durability.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/status.py
  - src/shared/packages/pyforge-core/src/pyforge/core/preserve_refs.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** bmad-loop parks an attempt under `attempt-preserve/<run>-<sha8>` and `refs/attempt-preserve-dirty/*` before a rollback reset or a re-mount. At every run start it prunes both families down to `preserve_keep` (`BL/verify.py:5805-5826`). Marshal's own intent-gap preserve copied that name on purpose (`supervisor/intent_gap_preserve.py:129, 139`, a `git branch -f` at `:291-295`), so durable work sits under the pruner's prefix. Marshal never pushes that ref: the stage push covers only `loop/<slug>` and `task.branch` (`supervisor/__main__.py:1798-1813`). Every such attempt is local, and one run start away from deletion. Story 87.13 renders `preserve_keep = 0`; this story makes the record a `preserve/` tag.

**Approach:**
- **On the event.** The supervisor promotes every engine preserve into a `preserve/<slug>/<N.M>/bmad-loop-<sha8>` tag when the engine journals `attempt-commits-preserved`, `attempt-worktree-preserved`, `worktree-kept` or `story-deferred` naming work.
- **By scan.** A reconcile scan at each stage boundary catches what the events miss, for example a missed event, an upstream event rename (AD-78) or a home the supervisor did not run. It promotes any unpromoted `refs/heads/attempt-preserve/*` or `refs/attempt-preserve-dirty/*` ref (AD-21).
- **Target.** Each target is resolved with `git rev-parse` of the engine ref, never from the sha a journal line prints (AD-9), and `Preserve-Source` names the engine ref.
- **Intent gap.** The intent gap writes `preserve/…/intent-gap-<sha8>` through `pyforge.core.preserve_refs`, with no `attempt-preserve/*` ref and no `git branch -f`. The patch file stays as a convenience.
- **Push.** The tag is written locally first, which satisfies AD-81 predicate (a). It is pushed at the next stage boundary through Story 87.15's content gate, journaled as a `stage-push` entry. A refused or offline push leaves the local tag, which status reports as debt.

Ledger key: `87-4-spin-parks-every-attempt-as-a-preserve-tag-before-bmad-loop-can-prune-it`.
Type / Effort / Deps: feature / M / S-87.3, S-87.13, S-87.15.

### Living CAP citations

- `spec-pyforge-marshal` CAP-287 (FR-234, AD-81), extending FR-189 / AD-74 (detect → preserve → defer-loud). Flag `pyforge.marshal.preserve_refs`.

## Acceptance Criteria

- Given a bmad-loop journal line `attempt-commits-preserved` (`ref=attempt-preserve/<run>-<sha8>`), `attempt-worktree-preserved` (`ref=refs/attempt-preserve-dirty/…`), `worktree-kept` or `story-deferred` with a `preserve_ref` When the supervisor reaches the next stage boundary Then a `preserve/<slug>/<N.M>/bmad-loop-<sha8>` tag exists whose target is `git rev-parse` of the engine ref; `Preserve-Source` names it; a `stage-push` journal entry records the push.
- Given an engine ref the journal never named (a bare run, or a renamed event) When the reconcile scan runs Then it is promoted the same way, once.
- Given a journal line whose printed sha differs from the ref's current target When the supervisor promotes it Then the tag points at the ref's target.
- Given an intent-gap escalation with an empty `preserve_ref` When the supervisor parks the attempt Then it writes `preserve/…/intent-gap-<sha8>`, creates no `attempt-preserve/*` ref, and the spec notice and the `escalation-detected` payload name the tag.
- Given a push the gate refuses, or no network When the boundary passes Then the escalation still names the local tag, and `marshal status` shows the row's preserve debt; nothing refuses.
- Given the same event, or the same scan finding, again When the supervisor runs Then no second tag is written.
- Given the flag off When the same inputs run Then today's behaviour is unchanged; one test file runs both states; removing the promotion, the scan or the rev-parse rule fails a test (mutation).

## Boundaries & Constraints

**Always:** Promote, never rename (AD-2). Resolve from git, not the journal (AD-9). Push through the gate, one refspec per tag.

**Never:** Never push an engine scratch ref. Never delete an engine ref here; retiring local scratch is Story 87.8. Never edit `bmad_loop`.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` CAP-287 (FR-234, AD-81); FR-189 / AD-74 (amended 2026-10-04).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (preserved-work refs) entry.
Research: drafts' Story 87.4; review minor 7 (the reconcile scan), B2 (local tag suffices), M7 (no second tag).
Ledger key: `87-4-spin-parks-every-attempt-as-a-preserve-tag-before-bmad-loop-can-prune-it`.
Ledger status at mint: `backlog`.
Deps: S-87.3, S-87.13, S-87.15.
Minted 2026-10-04 under the operator's ruling of the same day.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- The two-state flag test: `src/shared/packages/pyforge-marshal/tests/unit/test_intent_gap_preserve.py` — runs `pyforge.marshal.preserve_refs` on and off.
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.

## Spec Change Log

- 2026-10-09: Implemented engine preserve promotion (`supervisor/engine_preserve.py`), stage-boundary flush and intent-gap preserve tags behind `pyforge.marshal.preserve_refs`.

## Auto Run Result

Status: done

Verification: `pyforge-marshal-test`, `pyforge-deps-test`, `lint-types`, and `python scripts/spec_surface_reconcile.py` green (2026-10-09).

## Review Triage Log

- 2026-10-09: Implementation review against AC — engine journal tail + reconcile scan + stage-boundary tag/push wired in supervisor; intent-gap uses preserve tag when flag on; two-state tests in `test_engine_preserve.py` and `test_intent_gap_preserve.py`. No blocking findings.
