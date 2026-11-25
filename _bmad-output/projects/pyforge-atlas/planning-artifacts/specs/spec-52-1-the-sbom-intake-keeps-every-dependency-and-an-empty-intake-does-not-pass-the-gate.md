---
title: '52.1: The SBOM intake keeps every dependency and an empty intake does not pass the gate'
type: 'fix'
created: '2026-11-25'
status: 'in-review'
story: 52-1-the-sbom-intake-keeps-every-dependency-and-an-empty-intake-does-not-pass-the-gate
spec: spec-pyforge-atlas
difficulty: 'medium'
review_loop_iteration: 0
followup_review_recommended: false
declared_low_risk: false
surface:
  - 'src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/sbom_intake.py'
  - 'src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/universal_sbom/gate.py'
  - 'src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/vcs_sources.py'
  - 'src/shared/packages/pyforge-atlas/src/pyforge/atlas/trending_candidates/__main__.py'
  - 'src/shared/packages/pyforge-atlas/src/pyforge/atlas/trending_candidates/query.py'
  - 'src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/basilisk.py'
  - 'src/shared/packages/pyforge-atlas/tests/unit/datasets/test_sbom_intake.py'
  - 'src/shared/packages/pyforge-atlas/tests/unit/policy_gate/test_policy_gate.py'
  - 'src/shared/packages/pyforge-atlas/tests/unit/datasets/test_vcs_sources.py'
  - 'src/shared/packages/pyforge-atlas/tests/unit/trending_candidates/test_main.py'
  - 'src/shared/packages/pyforge-atlas/tests/unit/datasets/test_basilisk.py'
  - '_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/contract.md'
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/deferred-work-ledger.md
  - docs/dreams/pyforge-atlas.md
warnings: []
deferred: []
---

<intent-contract>

## Intent

**Problem:** The repository review of 2026-11-24 at main `7da08791f3` left six atlas defects below high severity as one open deferred-work row, `DW-atlas-review-2026-11-24-1`. The session lead confirmed the first; the other five are reviewer-reported and were not re-traced.

1. `parse_pyproject_toml` (`datasets/sbom_intake.py`) ends the `dependencies` array at any line that holds `]`, so the first dependency with extras (`"uvicorn[standard]>=0.30",`) stops the parse and the packages after it never reach the SBOM or the gate.
2. `assemble_and_gate` (`pipelines/universal_sbom/gate.py`) reads a match report whose `components` list is empty as a clean currency rung, so a truncated or unparsable intake exits 0.
3. `parse_environment_yml` reads `- conda-forge::numpy` as a package named `conda-forge`, and never leaves the `- pip:` block, so a conda dependency listed after it is tagged pypi.
4. `_luarocks_extract` (`datasets/vcs_sources.py`) picks the latest version with `_version_sort_key`, which ranks a non-digit run above a digit run, so `scm-1` beats every numeric version.
5. `trending-candidates` (`trending_candidates/__main__.py`) returns 1 on any exception, where the frozen domain (`degradation-contract.md`, CAP-13) says 2 for an error; `contract.md`'s row for the entry point records the 1.
6. The Basilisk catalog walk (`datasets/basilisk.py`) treats a page shorter than the page size as the last page even when fewer rows than the reported total were collected, so a truncated walk ends complete and can write over a fuller last-good store.

**Approach:** Reproduce first. For each defect, write the test named in its acceptance criterion and see it fail on the tree as it is; then fix. A defect whose test passes before any fix is not a defect: keep the test, change no code for it, and record it under Spec Change Log as "not a defect" with what the tree does instead. The fixes the row names: parse `[project] dependencies` with `tomllib` (standard library; a leading byte-order mark is dropped first, so a file saved with one reads the same; a document that does not parse yields no dependencies and does not raise); a match report with a `components` list of zero entries contributes an indeterminate rung, which the frozen domain maps to 1, while a report with no `components` key stays not-applicable (FR-16); strip a `channel::` prefix before the name is read and end the pip block when the indentation returns to the dependency list's own; rank a numeric LuaRocks version above `scm` and `dev` ones, falling back to those only when no numeric version exists; validate the filters of `trending-candidates` on their own, before the query runs (`query.validate_filters`, which touches no session, catalog or dataset), so that a bad filter value alone exits 1 and every other failure, a `ValueError` or a subclass of it raised by the load included, exits 2 (a closed stdout pipe keeps its quiet 1), and move the entry point's row of `contract.md` to `0` `1` `2`; and end the Basilisk walk partial when a short page arrives with fewer items served than the reported total, judged on the items the server served and never on the rows the parser kept, so an item the parser drops (a blank `name`) does not make a full walk partial; each page is counted as served before it is judged, so a page whose items the parser all drops is not read as an empty one.

Ledger key: `52-1-the-sbom-intake-keeps-every-dependency-and-an-empty-intake-does-not-pass-the-gate`.

### Living CAP citations

- spec-pyforge-atlas CAP-13, CAP-55, CAP-65, CAP-66, CAP-73 (realized, no text change); no AD moves. CAP-13 owns the intake and the gate (defects 1, 2, 3 and the frozen exit domain of 5), CAP-55 the `trending-candidates` CLI (5), CAP-65 the registry fetches (4), CAP-66 the Basilisk population (6), and CAP-73 the `contract.md` row (5).

## Boundaries & Constraints

**Always:**
- See each defect's test fail on the tree as it is before changing the code it covers.
- Keep the test of a defect the tree does not reproduce, and record that defect as not a defect.
- Take every exit code from the frozen domain; the gate's still comes from `pyforge.warden.verdict`, never a literal.
- Keep a last-good Basilisk store when a walk ends partial.
- Judge a truncated Basilisk walk on the items the server served, never on the rows the parser kept.
- Exit 1 from `trending-candidates` for a bad filter value alone (and the closed stdout pipe); every other failure exits 2.

**Never:**
- Never add a flag, a dataset, a catalog entry, a pipeline or a dependency.
- Never change `parse_pixi_toml`, the requirements, pip-list and conda-list readers, the SBOM passthroughs, or a registry other than LuaRocks.
- Never make a match report with no `components` key a failure (FR-16: not-applicable).
- Never let a `ValueError` raised after the filters have passed exit 1.
- Never hand-edit `SPEC.md`; the `contract.md` row is the one Spec-folder line this story moves.

## Acceptance Criteria

**Given** `DW-atlas-review-2026-11-24-1` names six defects: `parse_pyproject_toml` ends the array at any line that holds `]`; `assemble_and_gate` reads a match of zero components as clean; `parse_environment_yml` reads `channel::name` as the channel and keeps the pip block after a dedent; `_luarocks_extract` ranks `scm-1` above numeric versions; `trending-candidates` returns 1 on a crash; and a Basilisk walk that meets a short page below the reported total ends complete
**When** each is first written as a test that fails on the tree as it is, and then fixed
**Then** a dependency with extras no longer hides the ones after it and a `pyproject.toml` saved with a byte-order mark reads the same as one without, a match of zero components exits 1 as indeterminate and halts the run while a report with no components stays not-applicable, `conda-forge::numpy` is the conda package `numpy` and a conda dependency after the pip block is conda, the LuaRocks latest of `scm-1` and `1.10-1` is `1.10-1`, a crash of `trending-candidates` exits 2 with one stderr line, a `ValueError` that is not a bad filter value included, while a bad filter value keeps 1, and a truncated Basilisk walk keeps the last-good store while a walk served every item is written even when the parser drops one of them or every item of a page
**And** a defect the tree does not reproduce is recorded as not a defect, with the test that shows it kept

Each command selects its test by name, so a test that was never written exits 5, not 0. A defect the tree does not reproduce is recorded under Spec Change Log as not a defect; its command still exits 0, on the test that shows what the tree does.

- **AC1 — Defect 1: a dependency with extras does not end the pyproject array, and a byte-order mark does not empty it.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/unit/datasets/test_sbom_intake.py -q -k "test_pyproject_dependency_with_extras_does_not_end_the_array or test_pyproject_with_a_byte_order_mark_parses_the_same"
  ```

- **AC2 — Defect 2: a match of zero components is indeterminate, never clean.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/unit/policy_gate/test_policy_gate.py -q -k test_zero_component_match_is_indeterminate_not_clean
  ```

- **AC3 — Defect 3: a channel prefix is stripped and the pip block ends on dedent.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/unit/datasets/test_sbom_intake.py -q -k "test_environment_yml_strips_a_channel_prefix or test_environment_yml_leaves_the_pip_block_on_dedent"
  ```

- **AC4 — Defect 4: the LuaRocks latest is a numeric version when one exists.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/unit/datasets/test_vcs_sources.py -q -k test_luarocks_latest_prefers_a_numeric_version_over_scm
  ```

- **AC5 — Defect 5: a crash of `trending-candidates` exits 2 (a `ValueError` that is not a bad filter included), a bad filter value alone keeps 1, and `contract.md` agrees with the code.** Expected: exit 0 from each.

  ```bash
  pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/unit/trending_candidates/test_main.py -q -k "test_crash_exits_2_with_one_stderr_line or test_bad_tier_exits_1_with_stderr_message or test_a_value_error_that_is_not_a_bad_filter_exits_2 or test_every_bad_filter_value_exits_1_before_any_load"
  pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/meta/test_public_contract.py -q
  ```

- **AC6 — Defect 6: a short page below the reported total ends the Basilisk walk partial and keeps last-good; a walk served every item is complete.** Expected: exit 0.

  ```bash
  pixi run --frozen -e pyforge-atlas pytest src/shared/packages/pyforge-atlas/tests/unit/datasets/test_basilisk.py -q -k "test_short_page_below_the_reported_total_is_a_partial_walk or test_full_walk_with_a_nameless_item_is_complete_not_partial or test_a_served_page_whose_items_are_all_dropped_is_counted_before_it_is_judged"
  ```

- **AC7 — Both halves of atlas's suite pass.** Expected: exit 0 from each.

  ```bash
  pixi run --frozen -e pyforge-atlas pyforge-atlas-test
  pixi run --frozen -e pyforge-atlas pyforge-atlas-live-test
  ```

</intent-contract>

## Binding

- Capabilities: spec-pyforge-atlas CAP-13, CAP-55, CAP-65, CAP-66, CAP-73 (realized, no text change); no AD moves.
- Dream: `docs/dreams/pyforge-atlas.md`, the 2026-11-25 entry (the review's atlas defects are reproduced, then fixed); operator ruling of 2026-11-25.
- Epic: Epic 52, minted with this story.
- Deferred work: closes `DW-atlas-review-2026-11-24-1` (each of its six defects fixed, or recorded here as not a defect).
- Ledger key: `52-1-the-sbom-intake-keeps-every-dependency-and-an-empty-intake-does-not-pass-the-gate`.
- Surface: `marshal-policy.toml` `[epic_surfaces]."52"`.

## Verification

**Commands:** the Acceptance Criteria above, each read from its exit code.

## Spec Change Log

- 2026-11-25: minted from the station Dream's 2026-11-25 entry and the operator's ruling of the same date; `ready-for-dev`. Of the six defects only the first was confirmed on the tree by the review's lead; the other five are reproduced, or closed as not a defect, by the story.
- 2026-11-25: lead's rulings after the independent review, folded into the intent, the Always and Never lists and AC1, AC5 and AC6: a truncated Basilisk walk is judged on items served, not rows kept; `parse_pyproject_toml` drops a leading byte-order mark before `tomllib`; `trending-candidates` validates its filters apart from the query, so only a bad filter value exits 1 and any other failure exits 2. The surface gains `trending_candidates/query.py` (`validate_filters`, the one place a bad filter value is raised).
- 2026-11-25: defect 1: reproduced and fixed - `test_pyproject_dependency_with_extras_does_not_end_the_array` failed on the unchanged tree (`['uvicorn'] == ['uvicorn', 'rich', 'httpx']`); the review's regression, a byte-order mark emptying the list, failed as `test_pyproject_with_a_byte_order_mark_parses_the_same` before the mark was dropped.
- 2026-11-25: defect 2: reproduced and fixed - `test_zero_component_match_is_indeterminate_not_clean` failed on the unchanged tree (no `DataContractViolation` raised for a match of zero components).
- 2026-11-25: defect 3: reproduced and fixed - `test_environment_yml_strips_a_channel_prefix` and `test_environment_yml_leaves_the_pip_block_on_dedent` failed on the unchanged tree (`conda-forge::numpy=1.26.0` read as the package `conda-forge`; `scipy` after the pip block tagged pypi).
- 2026-11-25: defect 4: reproduced and fixed - `test_luarocks_latest_prefers_a_numeric_version_over_scm` failed on the unchanged tree (`'scm-1' == '1.10-1'`).
- 2026-11-25: defect 5: reproduced and fixed - `test_crash_exits_2_with_one_stderr_line` failed on the unchanged tree (`1 == 2`); the review's residue, a `ValueError` subclass from the load still exiting 1, failed as `test_a_value_error_that_is_not_a_bad_filter_exits_2` and `test_every_bad_filter_value_exits_1_before_any_load` before the filters were validated apart from the query.
- 2026-11-25: defect 6: reproduced and fixed - `test_short_page_below_the_reported_total_is_a_partial_walk` failed on the unchanged tree (the 450-row last-good overwritten with 250 rows, not stale); the review's regression, one nameless item making every full walk partial, failed as `test_full_walk_with_a_nameless_item_is_complete_not_partial` before the walk counted items served.
- 2026-11-25: second review, one residue on defect 6, fixed: the empty-frame branch judged a page before its served items were counted, so a last page whose one item the parser drops read as `empty page at offset=400 with 400/401 served` and the complete walk was thrown away. `test_a_served_page_whose_items_are_all_dropped_is_counted_before_it_is_judged` failed on that tree (`300 == 400`); the walk now counts a page before judging it, a page that serves nothing short of the total stays partial, and a page whose items are all dropped is judged as the short or full page it is.
- 2026-11-25: the story is implemented and in review: all six defects of `DW-atlas-review-2026-11-24-1` fixed, none closed as not a defect, and the review's three findings closed under the lead's rulings.
