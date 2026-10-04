---
title: "87.6: Land, retire and the station branch never fight the protected list"
type: 'fix'
created: '2026-10-04'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/SPEC.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/architecture/architecture-pyforge-marshal-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04-review.md
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/land.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/forge_gh.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/retire.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/retire.py
  - src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/policy.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** Three shipped rules contradict the protected list.
- **Land deletes `loop/*`.** `marshal land` merges the `loop/<slug>` PR with `gh pr merge --delete-branch` whenever `landing_branch_retirement` is on, which is the default (`cli/land.py:438, 507`; `core/policy.py:611`; `adapters/forge_gh.py:375-376`). Ruleset 24451573 now forbids deleting `loop/**` with no bypass. The status GitHub returns for a ruleset-refused ref delete is unverified. If it is 422, `gh` reports success and marshal journals `branch_retired: true` for a branch that still exists (`cli/land.py:1050, 1088`). Otherwise `gh` exits non-zero after the merge, and marshal raises on a merged PR (`forge_gh.py:378-387`).
- **Retire excludes too little.** `marshal retire` excludes only `loop/` structurally (`core/retire.py:53, 97-105`), not tags or the declared protected refs.
- **Retire can orphan commits.** It force-deletes a squash-proven local branch whose commits may then be reachable from nothing (AD-47 as amended).

**Approach:**
- **Land.** For a `loop/*` head, landing never requests a branch delete, and it emits a WARN finding that names AD-47. Any requested delete is recorded as `branch_retired` only from a post-merge `git ls-remote` fact, never from the request, and a refused delete is a reported outcome, never a crash.
- **Exclusions.** `marshal retire` excludes candidates structurally, before evidence-gathering and with no policy key that can loosen it: `refs/tags/**`, every `preserve/`, `archive/` or `rescue/` name, and every protected ref. The protected refs are the code floor (`refs/heads/main`, `refs/heads/loop/`) unioned with the policy layer's additions. The project layer may only extend those additions, and they print with provenance (AD-10, AD-16, AD-27).
- **Orphans.** A candidate whose deletion would make commits unreachable (its tip is not an ancestor of `refs/remotes/origin/main` and no other durable ref contains it) is refused. The refusal is reported as `would-orphan`, naming the archive-twin route (the sweeper's `--retire`, Stories 87.1 and 87.8); it is never deleted here.

Ledger key: `87-6-land-retire-and-the-station-branch-never-fight-the-protected-list`.
Type / Effort / Deps: fix / S / —.

### Living CAP citations

- FR-59 / AD-40 (landing policy) and FR-63 / AD-47 (proof-gated retirement), both amended 2026-10-04 under `spec-pyforge-marshal` CAP-287 / AD-81. A defect of shipped behaviour, so it is a `fix` with no flag. The operator ruled on 2026-10-04 that 87.6 ships unflagged.

## Acceptance Criteria

- Given `landing_branch_retirement = true` and a `loop/<slug>` head When `marshal land` merges Then `gh pr merge` is called without `--delete-branch` and a WARN finding names AD-47.
- Given a non-`loop/*` head whose merge requested a branch delete When the journal entry is written Then `branch_retired` comes from a post-merge `ls-remote` fact: still present → `false` with a finding; gone → `true`; a refused delete never raises on a merged PR.
- Given a candidate named `refs/tags/…`, `preserve/…`, `archive/…`, `rescue/…`, `main`, `loop/…` or a policy-declared protected prefix When `marshal retire` evaluates it Then it is excluded before evidence-gathering; a project layer that tries to remove a floor entry is refused at policy load.
- Given a patch-id-proven candidate whose tip is not an ancestor of `origin/main` and that no other ref contains When retire runs with `--execute` Then it is refused as `would-orphan`, naming the archive-twin route, and the branch still exists.
- Given an ancestor-of-`origin/main` candidate with all three facts proven When retire runs with `--execute` Then it is deleted as today.
- Given each rule removed When the tests run Then a test fails (mutation); the forge is the Story 59.1 fake, never GitHub.

## Boundaries & Constraints

**Always:** Dry run by default. Structural exclusions come before evidence. A remote fact beats a request.

**Never:** Never delete a `loop/*` head from a landing. Never touch a tag. Never default an unproven or orphaning retirement to delete.

</intent-contract>

## Binding

Parent: FR-59 / AD-40, FR-63 / AD-47 (amended 2026-10-04); `spec-pyforge-marshal` CAP-287 / AD-81.
Dream: `docs/dreams/pyforge-marshal.md` § *Realization log*, the 2026-10-04 (preserved-work refs) entry.
Research: drafts' Story 87.6; review M3 (floor plus policy additions), M5 (one orphan criterion).
Ledger key: `87-6-land-retire-and-the-station-branch-never-fight-the-protected-list`.
Ledger status at mint: `backlog`.
Deps: —.
Minted 2026-10-04 under the operator's ruling of the same day.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-marshal pyforge-marshal-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-ci pyforge-deps-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- The land and retire tests: `src/shared/packages/pyforge-marshal/tests/unit/test_land.py`, `tests/unit/test_forge_gh.py`, `tests/unit/test_retire.py`.

## Spec Change Log

- No change yet.

## Review Triage Log

- No review has run yet.
