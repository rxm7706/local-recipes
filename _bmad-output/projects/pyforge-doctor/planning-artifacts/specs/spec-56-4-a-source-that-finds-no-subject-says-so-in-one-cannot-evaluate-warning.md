---
title: '56.4: A source that finds no subject says so, in one cannot-evaluate warning'
type: 'fix'
created: '2026-11-10'
status: 'done'
story: 56-4-a-source-that-finds-no-subject-says-so-in-one-cannot-evaluate-warning
spec: spec-pyforge-doctor
difficulty: 'heavy'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a check that judges; a gated gate is a silent green (spec-feature-flag-governance Q1; roster list)
surface:
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/ledger.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/board.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/chain.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/deps.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/platform_policy.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/bmad_config.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/pixi_currency.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/general_docs_consistency.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/docs_shelf.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/hygiene.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/frontmatter_duplicate_keys.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/capability_effect.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/status_body_consistency.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/one_chain.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__init__.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/__main__.py'
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/factory.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_unmeasured.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_ledger_direction.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_marshal_story_status.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_chain_completeness.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dream_chain.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dreams_hygiene.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_deps_forward_dependency.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_platform_policy.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_config.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_pixi_currency.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_general_docs_consistency.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_shelf.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_hygiene.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_frontmatter_duplicate_keys.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_capability_effect_verified.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_capability_effect_caller_reach.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_consistency.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fold_complete.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fr_arrows.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_dispatch.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_sources_honest_reads_41_2.py'
  - 'tests/scripts/test_detectors_doctor_sources.py'
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

**Problem:** Audit defect, measured: over an empty tree ten sources answer OK over nothing, two return `()`, and nine cannot-evaluate WARNs lack the `unevaluable` key, so Story 56.3's aggregate could not tell them from a measurement.

**Approach:** Per-source decisions fixed from the audit's probe: (a) add `unevaluable: True` to the existing cannot-evaluate WARNs (dream-chain, deferred-work, dreams-hygiene, forward-dependency coverage, pixi-currency-ledger's unreadable Dream, chain-sprawl, fr-without-cap and fold-complete without baseline, platform-policy-suite's absent env and could-not-run); (b) an OK or `()` over an absent subject becomes one `<source>-unevaluable` WARN (ledger-direction, story-status, chain-completeness, bmad-render-config-ambiguity, general-docs-consistency, docs-shelf-occupancy, bmad-output-hygiene, frontmatter-duplicate-keys, capability-effect, platform-policy-suite with no src/platform, status-body-consistency); (c) unchanged, with the reason written in `test_sources_unmeasured.py`: dashboard-drift and check-layout (reintroduction gates), spec-surface and docs-map-hygiene (FAIL on a missing input), ledger-regression and bmad-drift (already marked), live-proof-surface and docs-currency (their WARN is `degrade_on_exception`'s).

Ledger key: `56-4-a-source-that-finds-no-subject-says-so-in-one-cannot-evaluate-warning`.
Type / Effort / Deps: fix / L / S-56.1, S-56.2, S-56.3.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-93** — amended 2026-11-10: a source whose subject is absent reports one `<source>-unevaluable` WARN, never an OK or nothing.
- **`spec-pyforge-doctor` AD-15** — the rule this story applies source by source.

## Boundaries & Constraints

**Always:**
- Change assertions in place and add no test function to a module Story 58.1 or 58.2 splits; new cases go to `test_sources_unmeasured.py`.
- No source changes scope and none leaves `detectors-ci`.

**Never:**
- Never turn a cannot-evaluate row into a FAIL; never change a source's exit domain (AD-2).
- Never hand-edit `SPEC.md` (memlog, then `bmad-spec` or the anchored script render with both self-validate passes logged); never append a `Surface reconcile` line to another Spec's memlog or run `spec_surface_check.py --write-baseline` (Story 58.4 stamps every Spec once, last on the branch); never add new behaviour or a kill switch beyond this story's capability text (operator ruling of 2026-11-10: each gap is a deferred-work row).

## Acceptance Criteria

- **AC1 — The empty-tree partition is pinned in the package half.** Expected: exit 0, 29 or more selected (one per detectors-ci name, listed in the module): over an empty `git init` tree under tmp_path every name returns at least one finding; `pass` = {dashboard-drift, check-layout}; `FINDINGS` = {spec-surface, docs-map-hygiene}; every other name returns only findings models.is_gather_failure accepts.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_unmeasured.py -q -m 'not live_tree' -p no:cacheprovider
  ```

- **AC2 — The module runs in the package half (no live_tree mark in any form).** Expected: exit 1 (no match).

  ```bash
  git grep -n live_tree -- src/shared/packages/pyforge-doctor/tests/unit/test_sources_unmeasured.py
  ```

- **AC3 — The registry agrees: no detectors-ci row is empty on an empty tree.** Expected: exit 0, 1 or more selected: every _DOCTOR_SOURCE_TASKS name gathers at least one finding and only dashboard-drift and check-layout read pass.

  ```bash
  pixi run --frozen -e pyforge-doctor python -m pytest tests/scripts/test_detectors_doctor_sources.py -q -k empty_tree -p no:cacheprovider
  ```

- **AC4 — No-feed story-status keeps its evidence and gains the marker.** Expected: exit 0; one WARN whose evidence is {"audited": 0, "unevaluable": true}.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_sources_marshal_story_status.py -q -p no:cacheprovider -k no_feeds
  ```

- **AC5 — On this tree only the two sources whose subject a checkout may lack read unmeasured.** Expected: exit 0; prints a subset of ['platform-policy-suite', 'story-status'] (the first without .pixi/envs/platform-ci-test, the second in a checkout with no Tier-3 feed).

  ```bash
  pixi run --frozen -e pyforge-guild python scripts/detectors.py --scope repo --json > "${TMPDIR:-/tmp}/doctor-detectors.json"; python3 -c "import json,os;r=json.load(open(os.environ.get('TMPDIR','/tmp')+'/doctor-detectors.json'))['results'];d=[x for x in r if x['path'].startswith('pyforge.doctor.sources:')];u=sorted(x['name'] for x in d if x['status']=='unmeasured');print(u);raise SystemExit(0 if set(u)<={'platform-policy-suite','story-status'} else 1)"
  ```

- **AC6 — Riders: the phantom module name and the literal station tuple are gone.** Expected: exit 1 (no match).

  ```bash
  git grep -nE 'pyforge\.doctor\.sources\.fleet_scan|\("herald", "marshal", "atlas"' -- src/shared/packages/pyforge-doctor/src
  ```

- **AC7 — The modules 58.1 and 58.2 split keep their test count (assertions change in place; new cases go to test_sources_unmeasured.py).** Expected: prints 1109 (595 + 514, grep-counted at f614d6a9b8).

  ```bash
  cat src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_deferred_work.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_dreams_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_due_for_verification.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_source_spec_resolution.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_chain_spec_surface.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_ledger_direction.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_board.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_board_chain_layers_audit.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_capability_effect_caller_reach.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fold_complete.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_one_chain_fr_arrows.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_consistency.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_open_questions.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_promissory.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_status_body_status_comment.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_hygiene_definitions.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_currency.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_map_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_docs_shelf.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_factory.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_bmad_method.py src/shared/packages/pyforge-doctor/tests/unit/test_checks_env_hygiene.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_pages_liveness.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_ci_pause_drift.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_live_proof_surfaces.py src/shared/packages/pyforge-doctor/tests/unit/test_sources_general_docs_consistency.py src/shared/packages/pyforge-doctor/tests/unit/test_flag_kill_switch.py | grep -cE '^\s*(async\s+)?def test_'
  ```

- **AC8 — The flag gate passes this story's spec.** Expected: exit 0; the printed JSON object has "verdict": "pass".

  ```bash
  pixi run --frozen -e pyforge-guild flag-gate-check -- --spec "$(ls _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-56-4-*.md)"
  ```

- **AC9 — Lint, types and the doctor suite halves stay green.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild lint-types && pixi run --frozen -e pyforge-doctor pyforge-doctor-test && pixi run --frozen -e pyforge-doctor pyforge-doctor-live-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-93 (amended 2026-11-10; this story realizes its `a source whose subject is absent says so` clause); FR-27 ← CAP-93.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-10 (the cutover readiness audit) entry; the operator's rulings of 2026-11-10 in `docs/dreams/pyforge-unifying-strategy.md` § *Realization log*.
- Epic: Epic 56, minted with this story.
- Ledger key: `56-4-a-source-that-finds-no-subject-says-so-in-one-cannot-evaluate-warning` (`backlog`).
- Deps: S-56.1, S-56.2, S-56.3.
- Surface: `marshal-policy.toml` `[epic_surfaces]."56"`.
- Minted 2026-11-10 in the one chain commit of the integration branch `cutover-readiness-2026-11-10`, before any doctor story builds.

## Notes

- Code is wrong (audit defect). `frozen-path-changed` and `capability-ledger` come from Stories 56.1 and 56.2.
- story-status: its no-feed row was pinned at OK `{audited: 0}` by an earlier story spec's I/O matrix; this story supersedes that row (status WARN, evidence `{audited: 0, unevaluable: true}`); marshal's `dispatch_verify` runs `story-status-check` and reads its exit code, which stays 0.
- `sources/marshal.py` and `sources/chain.py` are co-governed by `spec-pyforge-marshal` (its reconcile line through marshal's closer, Story 116.5).
- Riders: `one_chain._stations` falls back to `pyforge.core.roster.STATIONS`; the printed or written phantom name becomes `scripts/fleet_scan.py`.
- Test-count base: 1109 test functions in the 29 modules Stories 58.1 and 58.2 split (595 + 514, grep-counted at `f614d6a9b8`).
- Rulings of 2026-11-10 applied (`docs/dreams/pyforge-unifying-strategy.md` § Realization log, the second addendum, 'Accept all, run mint'): a source that measured nothing reads `unmeasured`, a warning the merge bar does not fail on; `doctor flags kill-switch` stays Doctor's one actuator; doctor's closed one-time campaigns retire; the marker grammar is CHAIN-STANDARD section 4 as steward Story 120.3 amends it (`(retired <date>[: <reason>])` and semicolon qualifiers, no `(unbuilt)` token); the operator flips `pyforge.cutover_root` by hand once the Launch slice is proven, and nothing flips it automatically.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code (never through a pipe).

**Run before the push:**
- `pixi run --frozen -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check` — expected: exit 0 each.

## Planned deferral (written at build)

The row below is not in the deferred-work ledger yet and is not in this spec's frontmatter (`deferred-work-check`
reds a frontmatter row with no tracked ledger twin). The doctor station closer of the cutover-readiness PR writes it
to `_bmad-output/projects/pyforge-doctor/planning-artifacts/deferred-work-ledger.md`.

- **`DW-doctor-56-4-1`** (low; owner doctor, a later story under `spec-pyforge-doctor:CAP-93`; locations
  `src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/marshal.py` (`gather_story_status`),
  `sources/pixi_currency.py` (`_gather`), `sources/chain.py` (`_gather_dreams_hygiene`), `sources/one_chain.py`
  (`_gather_chain_sprawl`)): four whole-source cannot-evaluate WARNs that an empty tree never reaches, so the
  audit's probe did not list them, still lack `evidence["unevaluable"]`, and each reads `pass` rather than
  `unmeasured` when it fires alone: story-status with feeds present but git unavailable, pixi-currency-ledger's
  unreadable `pixi.toml` (`pixi-currency-pixi-toml-unreadable`), dreams-hygiene's unreadable guild roster (its
  `roster_err` WARN), and chain-sprawl with no declared `fold_exemptions`. This story's per-source decisions were
  fixed from the probe, and the build adds nothing beyond them (operator ruling of 2026-11-10: each gap is a
  deferred-work row). The fix is one evidence key per WARN plus an in-place assertion each.

## Spec Change Log

- 2026-11-10: minted from the station Dream's 2026-11-10 entry (the cutover readiness audit) and the operator's rulings of 2026-11-10.
