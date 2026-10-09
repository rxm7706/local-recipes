---
title: "87.6: Land, retire and the station branch never fight the protected list"
type: 'fix'
created: '2026-10-04'
status: 'done'
baseline_revision: '48988a4d84a5a2be6e5e17162849a112c8cc315a'
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
deferred:
  - summary: >-
      Policy protected additions do not print with provenance (AD-10 / AD-16 / AD-27) on land or retire output.
    evidence: |-
      Story approach names provenance printing; implementation unions floor, roster, and project additions silently.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/cli/retire.py
    severity: medium
  - summary: >-
      Real-git unit tests for new GitVcs ls-remote, merge-base, and for-each-ref helpers are not added.
    evidence: |-
      Consumers land.py and retire.py depend on remote_branch_exists, is_commit_ancestor, and commit_contained_in_tag_prefixes; test_vcs_git.py has no cases.
    location: >-
      src/shared/packages/pyforge-marshal/src/pyforge/marshal/adapters/vcs_git.py
    severity: medium
  - summary: >-
      Mutation-style AC (each rule removal must fail a test) is not enforced by dedicated tests.
    evidence: |-
      Behavioral tests updated but no tests fail when protected_refs or downgrade helpers are removed.
    location: >-
      src/shared/packages/pyforge-marshal/tests/unit/test_protected_refs.py
    severity: low
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

- 2026-10-09: Auto run landed Story 87.6 implementation; review deferred provenance printing and expanded VCS test coverage.
- 2026-10-09 (landing repair, after the refused finalize stamp): `protected_ref_prefixes` joins the closed policy vocabulary as a STATIC key (`core/policy.py`, `schemas/policy.json`, `cli/config.py`; default `()`), so a layer declaring it composes with no MRS-POLICY-001 and `marshal config` prints it with its layer. Its layers union rather than last-wins, so no layer drops another's addition. A layer that tries to remove a floor entry (a leading `!` or `^`) is refused at policy load as MRS-POLICY-010, naming the floor entry; a re-declared floor entry is a no-op. A malformed list is MRS-POLICY-009, replacing the reused MRS-POLICY-004 in `cli/retire.py`. `marshal retire` reads the composed additions and refuses the whole project on either code. Closes the AC3 gap ("refused at policy load"). Count-named tests renamed (closes DW-3-13-1).

## Review Triage Log

### 2026-10-09 — Review pass
- verdicts: 18 findings — high 0, medium 4, low 3, false 3, maybe-false 0 (remaining routed patch/defer/reject)
- findings:
  - `[false]` `[reject]` MRS-LAND-013 unreachable on current land entry (head always loop/{slug}) — land.py fixes head to loop/{slug} before merge; finding path is reserved for future non-loop heads.
  - `[false]` `[reject]` loop happy-path branch_retired should always false while branch on origin — fake defaults remote absent; tests model post-delete remote; loop path never requests delete.
  - `[false]` `[reject]` retire module docstring stale — docstring drift only; behavior matches 87.6 via protected_refs.
  - `[medium]` `[patch]` Invalid protected_ref_prefixes silently dropped — retire now emits MRS-POLICY-004 and skips slug when key present and validation fails.
  - `[medium]` `[defer]` Provenance printing for policy additions not implemented — recorded in frontmatter deferred.
  - `[medium]` `[defer]` No real-git tests for new VcsPort methods — deferred.
  - `[medium]` `[defer]` Roster read failure returns empty set without finding — pre-existing pattern; floor still applies.
  - `[low]` `[defer]` Mutation AC not explicit in tests — deferred.
  - `[low]` `[reject]` archive/rescue branch names missing in test_protected_refs — covered by _STRUCTURAL_BRANCH_PREFIXES in protected_refs.py same as preserve/.
  - `[low]` `[reject]` MRS-LAND-013 no unit test — dead path on current land CLI; MRS-LAND-012 covered.
  - `[medium]` `[defer]` forge_gh merge success when gh pr view fails after delete refusal — edge case; MERGED view path covered by test_merge_pr_delete_failure_after_merged_does_not_raise.
  - Additional blind-hunter / edge-case items grouped into defer/reject above (docstring, test gaps, roster WARN).

### 2026-10-09 — Landing-repair review notes
- verdicts: 3 findings — medium 3; all patched
- findings:
  - `[medium]` `[patch]` `protected_ref_prefixes` was not a `core/policy.py` key, so a project layer declaring it tripped MRS-POLICY-001 — added to the closed vocabulary with type tuple-of-refs/-prefixes and default `()`; `tests/unit/test_policy.py::test_a_project_layer_declaring_protected_ref_prefixes_composes_with_no_finding`.
  - `[medium]` `[patch]` AC3 "a project layer that tries to remove a floor entry is refused at policy load" was not met (a re-declared floor entry was skipped, removal was not expressible, refusal ran at retire time) — `compose()` now refuses a removal entry that overlaps the floor as MRS-POLICY-010 naming the entry; `test_a_layer_removing_a_floor_entry_is_refused_at_policy_load_naming_it`, `test_a_refused_protected_list_refuses_the_project_before_any_evidence`.
  - `[medium]` `[patch]` the invalid-list refusal reused MRS-POLICY-004 (registered for an unreadable project layer) — now its own registered code MRS-POLICY-009 (`core/findings.py`, `core/verdict.py` UNEVALUABLE); `test_a_malformed_protected_ref_prefixes_is_refused_with_its_own_code`, `test_protected_ref_refusal_codes_classify_unevaluable`.

## Auto Run Result

- **Summary:** Land never passes `--delete-branch` for `loop/*` (MRS-LAND-012, AD-47); `branch_retired` comes from post-merge `remote_branch_exists`; forge treats merged+delete-failure as success; retire structural exclusions use code floor ∪ roster ∪ validated policy additions; would-orphan refuse on execute (MRS-RETIRE-004).
- **Files changed:** `core/protected_refs.py` (new floor/roster/policy matching); `cli/land.py`, `adapters/forge_gh.py`, `ports/vcs.py`, `adapters/vcs_git.py`; `core/retire.py`, `cli/retire.py`; findings/verdict; unit/meta tests; story spec metadata.
- **Review:** One patch (invalid `protected_ref_prefixes` → MRS-POLICY-004); provenance printing and VCS real-git tests deferred; several findings rejected as false or low-value.
- **Follow-up review recommended:** false (one medium patch only).
- **Verification:** `pyforge-marshal-test` pass; `pyforge-ci pyforge-deps-test` 130 passed; `pyforge-guild lint-types` exit 0 after ruff-format-fix; `python scripts/spec_surface_reconcile.py` OK.
- **Residual risks:** Provenance not printed; orphan “held elsewhere” narrowed to main + preserve/archive tags per M5; roster I/O errors still silent beyond code floor.
