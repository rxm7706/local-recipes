---
title: "85.2: The protected-ref list is declared once and the live rulesets are proven to match it"
type: 'feature'
created: '2026-10-04'
status: 'in-review'
baseline_revision: '2c22d23a06766dbc5c592ae81e046c6d062fa909'
flag-exempt: detector-or-gate   # a parity detector; a gated gate reports a silent green (spec-feature-flag-governance Q2)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-pyforge-steward/SPEC.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-steward/planning-artifacts/specs/spec-85-1-the-session-hook-refuses-deleting-protected-branches-and-loop-homes.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04.md
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/research/preserved-work-refs-2026-10-04-review.md
  - docs/governance/guild-roster.json
  - scripts/detectors.py
  - _bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml
deferred:
  - summary: >-
      Add a mocked successful gh ruleset list/detail test so fetch/normalize regressions fail in CI without calling GitHub.
    evidence: |-
      Live parity is operator-gated; only API failure is mocked today. A break in fetch_live_rulesets could pass fixture tests until an authenticated run.
    location: >-
      scripts/protected_refs_ruleset_check.py:63
    severity: medium (unverified)
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** The server-side guarantee for protected refs exists only in repository settings: ruleset 24451573. It is branch-only (deletion of `refs/heads/{loop,attempt-preserve,recover,rescue}/**`, no bypass), so it protects no tag and does not block a force-push of `loop/**`. Nothing compares it with the declared list Story 85.1 adds, so the two can drift unnoticed. The research found the ruleset's `recover/` and `rescue/` branch patterns protect an empty set, while 698 `rescue/*` and 45 `archive/*` tags have no protection.

**Approach:**
- **Rules per entry.** Each `protected_refs` entry in the roster gains the server rules it needs:
  - deletion, update and `non_fast_forward` for the `preserve-tag` and `archive-tag` entries, with no bypass actor;
  - the same for the legacy `rescue/` tags;
  - deletion and `non_fast_forward` for `refs/heads/loop/`;
  - deletion for the legacy `refs/heads/attempt-preserve/`.
- **Creation.** A `restrict-creation` rule covers `refs/heads/preserve/**` and `refs/heads/archive/**`, so neither prefix can become a branch (review minor 3).
- **Document.** A renderer writes `docs/governance/rulesets/protected-refs.json`, the GitHub ruleset JSON for the branch and tag rulesets, from the roster alone. Regeneration is byte-identical (marshal:AD-12: derived, never hand-edited).
- **Detector.** A new runtime-scope detector, `scripts/protected_refs_ruleset_check.py`, compares that document with the live rulesets through an authenticated `gh api`. It exits 0 on a match, 1 naming each difference, and 2 when `gh api rate_limit` shows no authenticated quota or any call fails, never passing (an unauthenticated probe fails open otherwise). It also reports as drift a protected-ref addition in marshal's station policy that the roster does not declare.
- **Applying.** Creating or editing a live ruleset is the operator's settings change, never this story's code and never a dispatched session's.

Ledger key: `85-2-the-protected-ref-list-is-declared-once-and-the-live-rulesets-are-proven-to-match-it`.
Type / Effort / Deps: feature / M / S-85.1.

### Living CAP citations

- `spec-pyforge-steward` CAP-165 (FR-38), extending CAP-5. Flag-exempt `detector-or-gate`. The operator ruled on 2026-10-04 that the parity check lives in steward (review Q17).

## Acceptance Criteria

- Given the roster and a live-ruleset fixture that match When the check runs Then it exits 0.
- Given a missing pattern, an extra pattern, a missing rule (`deletion`, `update`, `non_fast_forward`, `creation`), or a non-empty `bypass_actors` on a preserve or archive tag ruleset When the check runs Then it exits 1 and names each difference.
- Given `gh api rate_limit` showing no authenticated quota, or any API error When the check runs Then it exits 2 and never passes.
- Given the roster When the document is regenerated Then it is byte-identical to the tracked one; hand-editing the document fails the check.
- Given a marshal station-policy protected-ref addition the roster does not declare, or a roster branch entry that policy omits When the check runs Then it is drift (exit 1).
- Given the detector registry When `scripts/detectors.py` lists it Then it is registered as `runtime`, and the pixi task exists, with `pixi.lock` and `environment.yaml` regenerated in the same change.
- **Operator-gated (not a dispatch step), each by the operator's explicit confirmation:** create the tag ruleset for `preserve/**`, `archive/**` and `rescue/**` with `bypass_actors: []`; add `non_fast_forward` to the `loop/**` ruleset; restrict creation of `refs/heads/preserve/**` and `refs/heads/archive/**`; drop the empty `recover/**` and `rescue/**` branch patterns from ruleset 24451573. The check then exits 0 on the live repository.
- Given each rule removed When the tests run Then a test fails (mutation); tests use fixtures and never call GitHub.

## Boundaries & Constraints

**Always:** The roster is the one source. Fail closed on any unobservable read (AD-8).

**Ask First:** Every live ruleset change.

**Never:** Never write a ruleset through the API from code or a session. Never hand-edit the rendered document. Never pass on an unauthenticated probe.

</intent-contract>

## Binding

Parent: `spec-pyforge-steward` CAP-165 (FR-38); co-governs `spec-pyforge-marshal:CAP-287` / marshal:AD-81.
Dream: `docs/dreams/pyforge-steward.md` § *Realization log*, the 2026-10-04 (later) entry.
Research: drafts' Story 85.2; review M3 (union, scope), minor 3 (restrict branch creation), minor 16 (`non_fast_forward` on `loop/**`), Q9 and Q17.
Ledger key: `85-2-the-protected-ref-list-is-declared-once-and-the-live-rulesets-are-proven-to-match-it`.
Ledger status at mint: `backlog`.
Deps: S-85.1.
Minted 2026-10-04 under the operator's ruling of the same day.

## Verification

**Commands:**
- `pixi run --frozen -e pyforge-steward pyforge-steward-test` — expected: pass (the station's `verify_commands`; MRS-GATE-010 binding).
- `pixi run --frozen -e pyforge-guild lint-types` — expected: exit 0.

**Manual checks (not a dispatch gate):**
- `pixi run --frozen -e pyforge-guild python -m pytest tests/scripts/test_protected_refs_ruleset_check.py -q` — expected: pass.
- `pixi run --frozen -e pyforge-ci pyforge-doctor-scripts-test` — expected: pass (the CI `scripts-suite` twin).
- `pixi run --frozen -e pyforge-guild detectors-ci` — expected: exit 0.
- Operator, after landing and after applying the rulesets: run the check against the live repository with `gh` authenticated — expected: exit 0.

## Spec Change Log

- No intent-contract change. Review pass 2026-10-04 tightened comparator and exit-2 reporting (see triage log patches).

## Review Triage Log

### 2026-10-04 — Review pass
- verdicts: 28 findings — high 0, medium 6, low 8, false 10, maybe-false 4
- findings:
  - `[medium]` `[patch]` Live `enforcement` drift was not compared — added enforcement check in `compare_ruleset_maps` plus `test_enforcement_drift_exits_one`.
  - `[medium]` `[patch]` Live `ref_name.exclude` drift was not compared — added exclude check plus `test_exclude_drift_exits_one`.
  - `[medium]` `[patch]` Unauthenticated runs discarded document/marshal findings — `run_check` now returns accumulated diffs plus auth error on exit 2; `test_unauthenticated_preserves_local_findings`.
  - `[medium]` `[patch]` `environment.yaml` committed with pixi WARN prefix — regenerated via clean `pixi project export` without `PIXI_PROJECT_MANIFEST`.
  - `[medium]` `[reject]` Marshal policy omits per-entry `rules` — intentional; drift AC covers refname parity only, not rule arrays on policy tables.
  - `[medium]` `[defer]` No mocked successful `fetch_live_rulesets` test — operator-gated live AC; severity medium (unverified live integration shape).
  - `[low]` `[reject]` Restrict-creation ruleset hardcoded — matches review minor 3; roster has no branch rows for those prefixes.
  - `[low]` `[reject]` Tag `rules` arrays not rendered per-entry — all tag entries share TAG_RULES today; equivalent to roster.
  - `[low]` `[reject]` `scope` field unused in render/compare — out of story AC surface; future work if scope→ruleset mapping is needed.
  - `[low]` `[reject]` Runtime detector excluded from `detectors-ci` — spec and pixi task description require runtime scope.
  - `[low]` `[reject]` Tests rewrite fixture JSON in-tree — accepted pattern for this scripts suite; subprocess tests need stable paths.
  - `[low]` `[reject]` `--write-document` no-op branch after write — documents skip-live coupling; no behavior bug.
  - `[low]` `[reject]` `BRANCH_RULES_BY_KIND` unused tag keys — defensive map; no mis-render today.
  - `[low]` `[reject]` Story ledger not synced in diff — harness write-back; operator syncs ledger on land.
  - `[false]` `[reject]` `pixi.lock` missing from diff — lock already up-to-date at export time (`pixi lock` reported unchanged).
  - `[false]` `[reject]` `compare_ruleset_maps` ignores enforcement — fixed in patch (was true at review time).
  - `[false]` `[reject]` Auth path hides drift — fixed in patch.
  - `[false]` `[reject]` Memlog without baseline stamp — reconcile guard passed without `--write-baseline`; memlog + SPEC surface updated.
  - `[false]` `[reject]` SPEC surface under-lists paths — `docs/governance/**` allowlisted; scripts on steward SPEC surface.
  - `[false]` `[reject]` Marshal tag entries optional in compare — by design per AC wording (branch omission only).
  - `[false]` `[reject]` Duplicate ruleset names handling — edge case; GitHub API contract not shown broken in diff.
  - `[false]` `[reject]` Extra non-prefix rulesets — only `protected-refs-*` extras reported; intentional.
  - `[false]` `[reject]` `detectors.py` not edited — discovery is filesystem-based; detector registered at runtime.
  - `[false]` `[reject]` Marshal subprocess exit 1 not tested for policy drift — `compare_marshal_policy_to_roster` unit test covers drift signal; fixture path uses same function in `run_check`.
  - `[maybe-false]` `[reject]` Roster missing `protected_refs` KeyError — roster validated in production path via `load_roster()` and tests use real file.
  - `[maybe-false]` `[reject]` Invalid fixture JSON crashes — fixture path only used in tests with generated JSON.
  - `[maybe-false]` `[reject]` rate_limit int parse — gh returns numeric limits; would settle with malformed mock only.
  - `[maybe-false]` `[reject]` Tag rule tuple grouping — not required while all tags share rules.

## Auto Run Result

- **Summary:** Story 85.2 (CAP-165) adds roster `rules` on each `protected_refs` entry, renders `docs/governance/rulesets/protected-refs.json`, ships runtime detector `protected_refs_ruleset_check.py` with marshal-policy parity and authenticated live compare (fixtures in CI), plus pixi task and docs regeneration. Review patches compare `enforcement` and `exclude`, preserve local findings on exit 2, and clean `environment.yaml`.
- **Files changed:** `docs/governance/guild-roster.json`; `docs/governance/rulesets/protected-refs.json`; `scripts/_protected_refs_ruleset_lib.py`; `scripts/protected_refs_ruleset_check.py`; `tests/scripts/test_protected_refs_ruleset_check.py`; `tests/scripts/test_pre_shell_hook.py`; `tests/scripts/fixtures/protected_refs_ruleset/*`; `pixi.toml`; `environment.yaml`; `docs/reference/detectors.md`; `docs/map.yaml`; `_bmad-output/projects/pyforge-marshal/planning-artifacts/marshal-policy.toml`; spec memlogs and steward `SPEC.md` surface; story spec metadata.
- **Review:** 4 patches applied (3 medium comparator/auth/export fixes + tests). 1 defer (mocked live `gh` fetch). Remaining findings rejected as false, out of scope, or intentional by spec.
- **Follow-up review recommended:** `true` — three medium-severity patches landed in one pass (enforcement, exclude, auth reporting); live GitHub rulesets still operator-gated and unmocked fetch path remains unverified in CI.
- **Verification:** `spec_surface_reconcile.py` exit 0; pytest protected_refs + pre_shell shape 14 passed; `pyforge-doctor-scripts-test` 1169 passed; `lint-types` exit 0; `pyforge-steward-test` 2028 passed (prior checkpoint). `detectors-ci` exit 1 without NEW cap-citation — failures are pre-existing `pixi_version_check` import path in this worktree invocation and `ledger-direction` landed-but-unpromoted atlas row, not introduced by this story.
- **Residual risks:** Live repo rulesets still mismatch declared document until operator applies GitHub settings; authenticated live run will exit 1 until then. Runtime detector is not in `detectors-ci`.
