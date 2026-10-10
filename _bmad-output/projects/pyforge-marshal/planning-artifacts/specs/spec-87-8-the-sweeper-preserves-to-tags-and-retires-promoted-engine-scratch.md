---
title: "87.8: The sweeper preserves to tags and retires promoted engine scratch"
type: 'feature'
created: '2026-10-04'
status: 'done'
baseline_revision: '02167e79f48afd9fb8cacd8ce3369c435302f1ab'
review_loop_iteration: 0
followup_review_recommended: false
flag:
  key: pyforge.marshal.preserve_refs
  provider: openfeature-file
  default: {production: off, staging: off, dev: off}
  scope: global
  fallback: "the sweeper keeps today's PRESERVE-THEN-DELETE (git format-patch into ~/.local/state/pyforge-marshal/worktree-preserve) and never retires an engine scratch ref"
  cleanup: 90 days after ON in every environment (Q4)
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04-review.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-87-1-the-sweeper-reaches-remote-branches-and-never-deletes-a-protected-ref.md
  - scripts/worktree_sweep.py
  - tests/scripts/test_worktree_sweep.py
  - docs/how-to/manage-worktrees-with-bmad.md
  - src/shared/packages/pyforge-core/src/pyforge/core/preserve_refs.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The sweeper's PRESERVE-THEN-DELETE parks a worktree's unmerged commits as `git format-patch` files under `~/.local/state/pyforge-marshal/worktree-preserve/` (`scripts/worktree_sweep.py:63, 244-261`). That copy is host-local and not git. Engine scratch refs have nothing to retire them once marshal renders `preserve_keep = 0` (Story 87.13). That covers `refs/heads/attempt-preserve/*` and `refs/attempt-preserve-dirty/*`; 17 dirty refs sat on one disk on 2026-10-04. The protected list kept `attempt-preserve/` for every scope, so even a promoted local scratch branch could not go (review M4). A local branch retired by the sweeper can orphan commits.

**Approach:** The sweeper is a stdlib script. It imports `pyforge.core.preserve_refs` by path and, behind the flag, does four things:
- **PRESERVE-THEN-DELETE** writes a `preserve/<slug>/<N.M>/sweep-<sha8>` tag (or `preserve/unbound/sweep-<sha8>`) before `git worktree remove`. The tag is local first, which satisfies AD-81 predicate (a). The push goes through Story 87.15's content gate or is reported as debt. Nothing new is written under `~/.local/state`.
- **Engine scratch.** A local `refs/heads/attempt-preserve/*` or `refs/attempt-preserve-dirty/*` ref is retired only once a `preserve/` tag with `Preserve-Source` naming it exists, locally or on `origin`. Its target must be an ancestor of that tag's commit.
- **Local branches.** A local branch whose deletion would orphan commits first gets an annotated `refs/tags/archive/heads/<branch>` twin.
- **Tags.** `refs/tags/**` is never a candidate.

The how-to describes the new behaviour.

Ledger key: `87-8-the-sweeper-preserves-to-tags-and-retires-promoted-engine-scratch`.
Type / Effort / Deps: feature / M / S-87.1, S-87.3, S-87.15.

### Living CAP citations

- `spec-pyforge-marshal` CAP-287 (FR-234, AD-81) and AD-47 (amended 2026-10-04). Flag `pyforge.marshal.preserve_refs`. Story 87.1 owns the sweeper's remote mode and `--retire`; Story 87.14 owns stale locks and orphan directories.

## Acceptance Criteria

- Given a PRESERVE-THEN-DELETE verdict for a worktree with unmerged commits and an untracked file When `--execute` runs Then a `sweep` preserve tag whose tree includes the untracked file exists before `git worktree remove`; nothing is written under `~/.local/state/pyforge-marshal/worktree-preserve`.
- Given no network, or a push the gate refuses When `--execute` runs Then the worktree is still removed on the local tag, and the run reports the tag as preserve debt.
- Given a local `refs/attempt-preserve-dirty/x` with no preserve tag naming it When the sweep runs Then it is KEEP with the reason "unpromoted scratch"; once a tag names it and contains its target, `--execute` deletes the ref.
- Given a local branch whose tip is not an ancestor of `origin/main` and that no other ref contains When the sweep retires it Then an archive twin exists before the delete; an ancestor branch gets none.
- Given any `refs/tags/**` ref When the sweep runs in any mode Then it is never listed as a candidate.
- Given the flag off When the same sweep runs Then today's format-patch behaviour holds; one test file runs both states; removing each rule fails a test (mutation).

## Boundaries & Constraints

**Always:** Dry run by default. Write before remove. Real git and a bare remote in tests; no GitHub.

**Never:** Never remove a working copy whose unique content no tag holds. Never touch `~/.bmad-loops/`. Never delete a tag.

</intent-contract>

## Binding

Parent: `spec-pyforge-marshal` CAP-287 (FR-234, AD-81); AD-47 (amended 2026-10-04).
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (preserved-work refs) entry.
Research: drafts' Story 87.8, split by the review (minor 5); review M4 (retire promoted scratch), M5 (orphan criterion).
Ledger key: `87-8-the-sweeper-preserves-to-tags-and-retires-promoted-engine-scratch`.
Ledger status at mint: `backlog`.
Deps: S-87.1, S-87.3, S-87.15.
Minted 2026-10-04 under the operator's ruling of the same day.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_worktree_sweep.py -q` — expected: pass; it holds the two-state flag test for `pyforge.marshal.preserve_refs`.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass (the CI `scripts-suite` twin).
- `pixi run --frozen -e pyforge-guild flag-gate-check` — expected: exit 0.

## Spec Change Log

- 2026-10-09: Implemented CAP-287 sweeper preserve tags (`pyforge.marshal.preserve_refs`), engine scratch retirement, local archive twins, and how-to update.

## Auto Run Result

Status: done
Verification: pyforge-marshal-test, pyforge-doctor-scripts-test (worktree_sweep), lint-types, flag-gate-check green locally.

## Review Triage Log

- No review has run yet.
