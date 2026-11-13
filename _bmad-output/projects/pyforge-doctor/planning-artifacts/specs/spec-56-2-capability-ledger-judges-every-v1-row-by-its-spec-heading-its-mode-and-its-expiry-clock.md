---
title: '56.2: capability-ledger judges every v1 row by its Spec heading, its mode and its expiry clock'
type: 'fix'
created: '2026-11-10'
status: 'done'
story: 56-2-capability-ledger-judges-every-v1-row-by-its-spec-heading-its-mode-and-its-expiry-clock
spec: spec-pyforge-doctor
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
flag-exempt: detector-or-gate   # a check that judges; a gated gate is a silent green (spec-feature-flag-governance Q1; roster list)
surface:
  - 'src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/capability_ledger.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_capability_ledger.py'
  - 'src/shared/packages/pyforge-doctor/tests/unit/test_live_capability_ledger_case_list.py'
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

**Problem:** Ruling 4 of 2026-11-10 gives the `A-only` expiry a detector (warn 30 days ahead, a finding after); ruling 3 takes rows on archived Specs out; control-plane's v1 adds governance Spec rows, a `cells:` list and `flip` expiries. The source matches ids only, reads station Spec folders only, judges no expiry and holds a vacuous OK (audit defect).

**Approach:** Add CAP-95's row checks beside CAP-87's post-PIN rule in the same source: id, heading, path and mode truth, and the expiry clock with an injected `today`. Expiry forms follow steward Story 120.2's modes.md Schema v1, the one definition; the `flip` form reads `pyforge.core.cutover_root.root_of_record(target).root` (marshal Story 117.2's published API). The form of a row (`bad-expiry-form`, `bad-state`, `rebuilding-without-frozen-paths`) is control-plane's validator's; this source judges truth and time.

Ledger key: `56-2-capability-ledger-judges-every-v1-row-by-its-spec-heading-its-mode-and-its-expiry-clock`.
Type / Effort / Deps: fix / M / —; cross-station: marshal:S-117.2, steward:S-120.2.

### Living CAP citations

- **`spec-pyforge-doctor` CAP-95** — every ledger row is true to its capability, its Spec and its expiry (minted 2026-11-10).
- **`spec-pyforge-doctor` CAP-87** — the post-PIN check reads only live Specs; amended 2026-11-10 so CAP-95's row checks run beside it.
- **`spec-foundry-capability-ledger:CAP-2`** and **`spec-foundry-capability-ledger:CAP-4`** — the ledger's truth and its expiry, which this source mechanizes.

## Boundaries & Constraints

**Always:**
- Inject the clock; read the ledger, the Specs and each station's `sprint-status-ledger.yaml` as data (AD-1, AD-11).
- Compare headings against `extract_caps`' own output (the heading-case table in `spec-foundry-capability-ledger/extract.md` is the one fixture both extractors are tested against).
- Fixture Specs use made-up project names; the module loses its `live_tree` mark and its tracked-path literals.

**Never:**
- Never judge a row's `state` or read a header `states:`; never treat a bare `<E>.<S>` as a steward key (it is control-plane's `bad-expiry-form`; here it is `a-only-expiry-unresolved`).
- Never decide when the flag flips: `flip` only reports after the flag reads foundry.
- Never hand-edit `SPEC.md` (memlog, then `bmad-spec` or the anchored script render with both self-validate passes logged); never append a `Surface reconcile` line to another Spec's memlog or run `spec_surface_check.py --write-baseline` (Story 58.4 stamps every Spec once, last on the branch); never add new behaviour or a kill switch beyond this story's capability text (operator ruling of 2026-11-10: each gap is a deferred-work row).

## Acceptance Criteria

- **AC1 — Row checks run in the package half.** Expected: pytest exit 0; grep prints 35 or more.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_capability_ledger.py -q -m 'not live_tree' -p no:cacheprovider && grep -cE '^\s*(async\s+)?def test_' src/shared/packages/pyforge-doctor/tests/unit/test_capability_ledger.py
  ```

- **AC2 — The module runs in the package half (no live_tree mark in any form).** Expected: exit 1 (no match).

  ```bash
  git grep -n live_tree -- src/shared/packages/pyforge-doctor/tests/unit/test_capability_ledger.py
  ```

- **AC3 — Every expiry form and boundary with an injected clock.** Expected: exit 0, 11 or more selected: today+31 none; today+30 WARN a-only-expiring; today WARN; today-1 FAIL a-only-expired; key done FAIL a-only-expiry-lapsed; key blocked none; key absent FAIL a-only-expiry-unresolved; float FAIL a-only-expiry-unquoted; flip none under local-recipes; flip FAIL a-only-expiry-flipped under foundry; a row naming `steward:44.8` resolved in steward's ledger.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_capability_ledger.py -q -p no:cacheprovider -k expiry
  ```

- **AC4 — Row truth, governance Specs, cells and the absent ledger.** Expected: exit 0, 9 or more selected; each FAIL carries its own evidence kind, pending is one WARN, a docs/governance/spec-*/SPEC.md row resolves, the two absent cases are single WARNs with evidence['unevaluable'] is True.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_capability_ledger.py -q -p no:cacheprovider -k 'heading_drift or archived_spec_row or orphan_row or bad_mode or pending_mode or governance_spec_row or cells_entry or no_ledger_is_unevaluable or no_capabilities_is_unevaluable'
  ```

- **AC5 — The vacuous OK is gone.** Expected: exit 1 (no match).

  ```bash
  git grep -n 'nothing to classify yet' -- src/shared/packages/pyforge-doctor/src/pyforge/doctor/sources/capability_ledger.py
  ```

- **AC6 — The case-list reader keeps its live proof, alone in a live module.** Expected: exit 0, 1 test.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_live_capability_ledger_case_list.py -q -m live_tree -p no:cacheprovider
  ```

- **AC7 — The flag gate passes this story's spec.** Expected: exit 0; the printed JSON object has "verdict": "pass".

  ```bash
  pixi run --frozen -e pyforge-guild flag-gate-check -- --spec "$(ls _bmad-output/projects/pyforge-doctor/planning-artifacts/specs/spec-56-2-*.md)"
  ```

- **AC8 — Lint, types and the doctor suite halves stay green.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-guild lint-types && pixi run --frozen -e pyforge-doctor pyforge-doctor-test
  ```

- **AC9 — a qualified Story expiry resolves against its own station's ledger (fixture: `mason:39.2` done -> FAIL, backlog -> OK).** Expected: exit 0 with at least one test selected.

  ```bash
  pixi run --frozen -e pyforge-doctor pytest src/shared/packages/pyforge-doctor/tests/unit/test_capability_ledger.py -q -k qualified
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-doctor CAP-95 (minted 2026-11-10), CAP-87 (amended 2026-11-10); FR-26 ← CAP-95, CAP-87.
- Dream: `docs/dreams/pyforge-doctor.md` § *Realization log*, the 2026-11-10 (the cutover readiness audit) entry; the operator's rulings of 2026-11-10 in `docs/dreams/pyforge-unifying-strategy.md` § *Realization log*.
- Epic: Epic 56, minted with this story.
- Ledger key: `56-2-capability-ledger-judges-every-v1-row-by-its-spec-heading-its-mode-and-its-expiry-clock` (`backlog`).
- Deps: —; cross-station: marshal:S-117.2, steward:S-120.2.
- Surface: `marshal-policy.toml` `[epic_surfaces]."56"`.
- Minted 2026-11-10 in the one chain commit of the integration branch `cutover-readiness-2026-11-10`, before any doctor story builds.

## Notes

- Code incomplete against rulings 3 and 4, plus a vacuous OK (audit defect).
- Expiry forms (steward Story 120.2, modes.md Schema v1): a Story expiry is the quoted, qualified `<station>:<E>.<S>` and resolves against that station's `sprint-status-ledger.yaml` key prefix `<E>-<S>-` (`steward:44.8` in steward's, `mason:39.2` in mason's); `YYYY-MM-DD`; `flip`. A `CutoverRootError` is one cannot-evaluate WARN for the flip rows only.
- Governance Spec ids are the folder name minus `spec-` (as `_cite_id` does) unless `extract.md` says otherwise.
- A heading mismatch and an archived row FAIL at once: steward Story 121.3 regenerates the ledger inside this same PR, so `capability-ledger-check` is red on the branch from this story until 121.3, and its exit 0 is judged at steward Story 121.7 (regeneration after every Spec sweep); until then new CAP ids read `unclassified` by design. The PR bar sits on Story 58.4.
- The one repo reader (steward's case-list.md through `parents[6]`) moves to `test_live_capability_ledger_case_list.py` (an explicit path, no root hand-off). Qualify bare CAP ids in the module.
- Cross-station deps: marshal:S-117.2 (root_of_record), steward:S-120.2 (modes.md Schema v1).
- Rulings of 2026-11-10 applied (`docs/dreams/pyforge-unifying-strategy.md` § Realization log, the second addendum, 'Accept all, run mint'): a source that measured nothing reads `unmeasured`, a warning the merge bar does not fail on; `doctor flags kill-switch` stays Doctor's one actuator; doctor's closed one-time campaigns retire; the marker grammar is CHAIN-STANDARD section 4 as steward Story 120.3 amends it (`(retired <date>[: <reason>])` and semicolon qualifiers, no `(unbuilt)` token); the operator flips `pyforge.cutover_root` by hand once the Launch slice is proven, and nothing flips it automatically.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code (never through a pipe).

**Run before the push:**
- `pixi run --frozen -e pyforge-guild chain-completeness-check`, `story-status-check`, `flag-gate-check` — expected: exit 0 each.

## Spec Change Log

- 2026-11-10: minted from the station Dream's 2026-11-10 entry (the cutover readiness audit) and the operator's rulings of 2026-11-10.
