---
title: '58.1: The chain, ledger, board and one-chain tests that build their own tree run in the package half'
type: 'chore'
created: '2026-11-10'
status: 'backlog'
story: 58-1-the-chain-ledger-board-and-one-chain-tests-that-build-their-own-tree-run-in-the-package-half
spec: spec-pyforge-doctor
difficulty: 'heavy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # test modules and a test-only split, no runtime path (spec-55-4's form; roster list)
surface:
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dreams_hygiene.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_source_spec_resolution.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_spec_surface.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_ledger_direction.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_board.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_chain_layers_audit.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_capability_effect_caller_reach.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fold_complete.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fr_arrows.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_consistency.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_open_questions.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_promissory.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_status_comment.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_hygiene.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_hygiene_definitions.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_chain_deferred_work.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_chain_dreams_hygiene.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_chain_due_for_verification.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_chain_source_spec_resolution.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_chain_spec_surface.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_ledger_direction.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_board.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_board_chain_layers_audit.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_capability_effect_caller_reach.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_one_chain.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_one_chain_fold_complete.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_one_chain_fr_arrows.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_status_body_consistency.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_status_body_open_questions.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_status_body_promissory.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_status_body_status_comment.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_hygiene.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_hygiene_definitions.py'
context:
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/SPEC.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-pyforge-doctor/.memlog.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/prds/prd-pyforge-doctor-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-doctor/planning-artifacts/architecture/architecture-pyforge-doctor-2026-07-25/ARCHITECTURE-SPINE.md
  - docs/dreams/pyforge-doctor.md
  - docs/dreams/pyforge-unifying-strategy.md
  - docs/governance/spec-one-chain-per-station/CHAIN-STANDARD.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** Audit finding MUST 7, refined: 18 modules holding 595 test functions sit in the live half for about 16 that read the repository. Test-only; no source changes.

**Approach:** Per module: move each test, and the helpers only it uses, that reaches the repository through `parents[N]`, a `REPO_ROOT` name or a root hand-off into `tests/unit/test_live_<same name>.py` with `pytestmark = pytest.mark.live_tree`; delete the mark from the original; rewrite a fixture literal that names a tracked path as a path join or a made-up name (steward's scan_strings reads a bare literal of a tracked path as a read). In a test_live_ module a `pytest.skip` on an absent repository path becomes an assert with the same message. A shared helper goes to a private module under tests/unit/ only when both files need it. Record the final list of test_live_ modules in this spec: steward-station makes one re-key edit after Stories 56.2, 57.3, 58.1 and 58.2. No pixi.toml change: the two tasks select by marker.

Ledger key: `58-1-the-chain-ledger-board-and-one-chain-tests-that-build-their-own-tree-run-in-the-package-half`.
Type / Effort / Deps: chore / L / S-56.4.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-97** — the package-local half builds every tree it reads and is the rebuild oracle.

## Boundaries & Constraints

**Always:**
- Keep every test: the two halves together hold exactly the 595 functions grep-counted at `f614d6a9b8`.

**Never:**
- Never change a source; never delete or skip a test to meet the split.
- Never hand-edit `SPEC.md` (memlog, then `bmad-spec` or the anchored script render with both self-validate passes logged); never append a `Surface reconcile` line to another Spec's memlog or run `spec_surface_check.py --write-baseline` (Story 58.4 stamps every Spec once, last on the branch); never add new behaviour or a kill switch beyond this story's capability text (operator ruling of 2026-11-10: each gap is a deferred-work row).

## Acceptance Criteria

- **AC1 — None of the 18 modules carries the live_tree mark any more.** Expected: exit 1 (no match).

  ```bash
  git grep -l live_tree -- src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dreams_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_source_spec_resolution.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_spec_surface.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_ledger_direction.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_board.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_chain_layers_audit.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_capability_effect_caller_reach.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fold_complete.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fr_arrows.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_consistency.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_open_questions.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_promissory.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_status_comment.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_hygiene_definitions.py
  ```

- **AC2 — Every new test_live_ module is marked at module level.** Expected: exit 0, prints nothing.

  ```bash
  for f in $(ls src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_chain_deferred_work.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_chain_dreams_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_chain_due_for_verification.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_chain_source_spec_resolution.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_chain_spec_surface.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_ledger_direction.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_board.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_board_chain_layers_audit.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_capability_effect_caller_reach.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_one_chain.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_one_chain_fold_complete.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_one_chain_fr_arrows.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_status_body_consistency.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_status_body_open_questions.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_status_body_promissory.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_status_body_status_comment.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_live_hygiene_definitions.py 2>/dev/null); do grep -qE '^pytestmark\s*=.*live_tree' "$f" || { echo "$f"; exit 1; }; done
  ```

- **AC3 — No test was lost, and the fixture tests stay in the package half.** Expected: the two counts sum to 595 (grep-counted at f614d6a9b8, the plan's base; 56.4 adds no test function to these modules); the second is at most 60.

  ```bash
  cat src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dreams_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_source_spec_resolution.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_spec_surface.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_ledger_direction.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_board.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_chain_layers_audit.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_capability_effect_caller_reach.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fold_complete.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fr_arrows.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_consistency.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_open_questions.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_promissory.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_status_comment.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_hygiene_definitions.py | grep -cE '^\s*(async\s+)?def test_'; cat $(ls src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_chain_deferred_work.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_chain_dreams_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_chain_due_for_verification.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_chain_source_spec_resolution.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_chain_spec_surface.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_ledger_direction.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_board.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_board_chain_layers_audit.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_capability_effect_caller_reach.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_one_chain.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_one_chain_fold_complete.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_one_chain_fr_arrows.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_status_body_consistency.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_status_body_open_questions.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_status_body_promissory.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_status_body_status_comment.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_live_hygiene_definitions.py 2>/dev/null) /dev/null | grep -cE '^\s*(async\s+)?def test_'
  ```

- **AC4 — The package-half modules skip on no repository condition.** Expected: prints 0 (today these 18 modules hold 22 skip sites, every one a repository or git condition).

  ```bash
  cat src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dreams_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_source_spec_resolution.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_spec_surface.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_ledger_direction.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_board.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_chain_layers_audit.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_capability_effect_caller_reach.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fold_complete.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fr_arrows.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_consistency.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_open_questions.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_promissory.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_status_comment.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_hygiene_definitions.py | grep -cE 'pytest\.skip\(|pytest\.mark\.skipif|pytest\.importorskip'
  ```

- **AC5 — A repository-absence skip moved to a live module became a failure.** Expected: prints nothing (exit 1).

  ```bash
  cat $(ls src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_chain_deferred_work.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_chain_dreams_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_chain_due_for_verification.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_chain_source_spec_resolution.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_chain_spec_surface.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_ledger_direction.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_board.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_board_chain_layers_audit.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_capability_effect_caller_reach.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_one_chain.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_one_chain_fold_complete.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_one_chain_fr_arrows.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_status_body_consistency.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_status_body_open_questions.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_status_body_promissory.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_status_body_status_comment.py src/shared/packages/pyforge-doctor/tests/unit/test_live_sources_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_live_hygiene_definitions.py 2>/dev/null) /dev/null | grep -nE 'not running inside|not resolvable from this checkout|parents\[6\] out of range|is not present|not present in this checkout|no _bmad-output|not in this checkout|monorepo'
  ```

- **AC6 — Steward's rule for the package half holds.** Expected: exit 0 (doctor's package half derives no outside read and no hand-off); test_root_handoffs_are_declared_exactly and test_the_handoff_floor are expected red until steward-station's re-key (shared request).

  ```bash
  pixi run --frozen -e pyforge-steward pytest src/shared/packages/pyforge-steward/tests/meta/test_station_tests_trigger_map.py -q -p no:cacheprovider -k package_half_reads_nothing
  ```

- **AC7 — The flag gate passes this story's spec.** Expected: exit 0; the printed JSON object has "verdict": "pass".

  ```bash
  pixi run --frozen -e pyforge-guild flag-gate-check -- --spec "$(ls _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-58-1-*.md)"
  ```

- **AC8 — Lint, types and the doctor suite halves stay green.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild lint-types && pixi run --frozen -e pyforge-doctor pyforge-doctor-test && pixi run --frozen -e pyforge-doctor pyforge-doctor-live-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-97 (realizes its oracle clause for the modules it splits; no text change); FR-28 ← CAP-97.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-10 (the cutover readiness audit) entry; the operator's rulings of 2026-11-10 in `docs/dreams/pyforge-unifying-strategy.md` § *Realization log*.
- Epic: Epic 58, minted with this story.
- Ledger key: `58-1-the-chain-ledger-board-and-one-chain-tests-that-build-their-own-tree-run-in-the-package-half` (`backlog`).
- Deps: S-56.4.
- Surface: `marshal-policy.toml` `[epic_surfaces]."58"`.
- Minted 2026-11-10 in the one chain commit of the integration branch `cutover-readiness-2026-11-10`, before any doctor story builds.

## Notes

- `test_sources_chain_spec_surface.py` is co-governed by `spec-pyforge-marshal` (its reconcile line through marshal's closer, Story 116.5). The git-unavailable skips (test_sources_chain_due_for_verification.py, test_sources_board_chain_layers_audit.py) move with their repository readers.
- The test_live_ files in the surface are created only where the module keeps a repository reader.
- Rulings of 2026-11-10 applied (`docs/dreams/pyforge-unifying-strategy.md` § Realization log, the second addendum, 'Accept all, run mint'): a source that measured nothing reads `unmeasured`, a warning the merge bar does not fail on; `doctor flags kill-switch` stays Doctor's one actuator; doctor's closed one-time campaigns retire; the marker grammar is CHAIN-STANDARD section 4 as steward Story 120.3 amends it (`(retired <date>[: <reason>])` and semicolon qualifiers, no `(unbuilt)` token); the operator flips `pyforge.cutover_root` by hand once the Launch slice is proven, and nothing flips it automatically.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code (never through a pipe).

**Run before the push:**
- `pixi run --frozen -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check` — expected: exit 0 each.

## Spec Change Log

- 2026-11-10: minted from the station Dream's 2026-11-10 entry (the cutover readiness audit) and the operator's rulings of 2026-11-10.
