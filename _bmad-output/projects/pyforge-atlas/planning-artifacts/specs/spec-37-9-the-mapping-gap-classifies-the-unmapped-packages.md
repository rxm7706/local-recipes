---
title: "37.9: The mapping-gap classifies the unmapped packages"
type: 'feature'
created: '2026-10-23'
status: 'done'
baseline_revision: '884d7f1106439c1a3090d1921ea83c2b4afe346f'
flag:
  key: pyforge.atlas.board_projections            # existing; minted by Story 37.4, extended to this board
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through src/platform/config/flag-overlays.json
  scope: global                                   # v1 is global only
  fallback: 'the mapping-gap reads primary/mapping_gap as before, which nothing writes, and renders empty'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - docs/reference/story-spec-flag-block.md
  - .claude/skills/conda-forge-expert/scripts/mapping_gap.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/pypi_intelligence/nodes.py
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/dashboard/app.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** the mapping-gap board reads `primary/mapping_gap/`, and no node writes it (DW-atlas-37-9-1). On Story
37.2's live data root, 12,362 of 34,720 enumerated packages have no row in `pypi_conda_mapping`. Nothing says why.

Legacy `mapping_gap.py` (read-only without `--write`) answers it in two steps:
- `classify` puts each unmapped package in one of three buckets: `python_track` (a `run` dependency on python, or
  a PyPI upstream), `non_python_with_identity` (another upstream) or `non_python_no_identity`.
- `recover` looks each python-track name up in the PyPI universe under four spellings: bare, and without a `-py`,
  `-python` or `python-` affix, PEP 503 folded. It then sorts each package into an outcome:
  - one hit that no mapped package claims (the hit writes as `g10_spelling`);
  - several hits (ambiguous);
  - a hit another package already maps to (a collision);
  - a hit only under an affix (needs a corroborator);
  - no hit.

**Approach:**
1. **A node,** `classify_mapping_gap`, in `pypi_intelligence` (the pipeline that owns the mapping and the universe),
   reads:
   - `core_packages_enumerated`, `pypi_conda_mapping` and `core_dependencies`;
   - `vcs_upstream_versions` (its `host`) and `vcs_registry_versions` (its `registry`), as legacy's upstream sources;
   - `pypi_universe`.

   It writes `derived_mapping_gap`, with `conda_name`, `classification`, `match_source`, `match_confidence`,
   `candidate` and `transform`. For a python-track package, `match_confidence` is one of:
   - `likely`, with `match_source` `g10_spelling`;
   - `ambiguous`, `collision`, `uncorroborated` or `unrecovered`.

   A non-python package has none.
2. **The board,** behind `pyforge.atlas.board_projections` as Stories 37.4 and 37.5's boards are: on, mapping-gap
   reads `derived/derived_mapping_gap/` with a note that says how it is built; off, it reads `primary/mapping_gap/`
   as before.

**Deviations from legacy:**
- Legacy corroborates a hit with the grayskull cache and the purl-associator bundle, each keyed by conda name, and
  writes `verified` when one agrees. Atlas holds neither keyed by conda name, so no row is `verified`, and an
  affix-only hit stays `uncorroborated`.
- The working set is every enumerated package with no mapping row. Legacy's is `v_actionable_packages`, which also
  leaves out archived feedstocks.
- Nothing is written back to the mapping (legacy's `--write`).

Ledger key: `37-9-the-mapping-gap-classifies-the-unmapped-packages`.
Type / Effort / Deps: feature / M / Story 37.1 (the data root).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-69** (FR-77, the boards no pipeline feeds). **AD-8** (BSL over DuckDB; no metric
  computed in the app), **AD-14** (the node is a new rider, not parity-gated), **AD-17** (the page's stamp from the
  dataset it reads).

## Acceptance Criteria

- **AC1 — Working set.** Every enumerated package with no mapping row, and only those, gets a row.
- **AC2 — Classes.** The three buckets are legacy's: a `run` dependency on python or a PyPI upstream is python-track; any
  other upstream is `non_python_with_identity`; none is `non_python_no_identity`.
- **AC3 — Recovery.** Legacy's four spellings and outcomes, with its claim index: a name a mapped package already folds
  to, or one another unmapped package claimed earlier in the run, is a `collision`.
- **AC4 — Empty.** No enumerated package, or none unmapped, writes an empty typed table.
- **AC5 — Board.** With the flag on, mapping-gap reads `derived_mapping_gap` and its AD-17 stamp names that file; off,
  it reads `primary/mapping_gap/` as before.

## Boundaries & Constraints

**Always:** read-only; the mapping is never written.

**Never:** reach the network; mark a row `verified` without a corroborator.

**Residual risk:**
- Without corroborators, `likely` rests on PEP 503 name equality alone, which legacy also accepts for `bare`.
- `non_python_with_identity` depends on `vcs_upstream_versions`, which a public run without the GitHub token leaves
  empty, so most packages read `non_python_no_identity` there.

## I/O & Edge-Case Matrix

| Package | Universe | Result |
|---------|----------|--------|
| mapped | any | no row |
| run dependency on python | its folded name, unclaimed | python_track, likely, g10_spelling |
| python-track `x-py` | `x` only | uncorroborated, candidate `x`, transform strip-py |
| python-track | two spellings hit | ambiguous |
| python-track | a name another package maps to | collision |
| python-track | nothing | unrecovered |
| upstream on GitHub, no python | any | non_python_with_identity |
| nothing known | any | non_python_no_identity |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-69 (FR-77). No CAP is minted, and no `SPEC.md` text changes.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, the 2026-10-19 entry (the Vizro boards read their data).
- Epic: Epic 37 (in progress). Closes DW-atlas-37-9-1.
- Ledger key: `37-9-the-mapping-gap-classifies-the-unmapped-packages`.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas pyforge-atlas-test` — expected: pass.
- From the repo root: `src/shared/packages/pyforge-atlas/tests/unit/pipelines/pypi_intelligence/test_mapping_gap.py`
  and `src/shared/packages/pyforge-atlas/tests/unit/test_board_projections.py` (both flag states) — expected: pass.

## Run results

Run 2026-10-23 in the landing worktree on `884d7f1106`, every verdict read from its exit code.

- **AC1–AC5, tests:** `test_mapping_gap.py` (17) and `test_board_projections.py` pass; `pyforge-atlas-test` gives
  3,128 passed and 20 skipped, plus the planning-record test re-run after the ledger sync (9 passed).
- **Pins moved:** `pypi_intelligence` has 18 nodes (17 before), the combined DAG 68 (67), the catalog 135 entries
  (134). The node joins the parity harness's AD-14 rider set and has a timeout; it runs in the whole-DAG bootstrap
  job, as `map_pypi_conda` does.
- **Mutations**, each restored, each failing a named test (10 of 10): mapped packages kept, any python dependency
  (not `run`), the PyPI upstream ignored, no PEP 503 fold, no strip-py spelling, ambiguous read as likely, no
  collision check, no intra-run claim, an affix hit read as likely, and the board path not switched.
- **Real data:** over Story 37.2's live data root (34,720 enumerated packages, 22,358 mapped, a PyPI universe of
  919,975 names) the node writes 12,362 rows in 6.9 s: 10,962 `non_python_no_identity`, 1,395 `python_track` and 5
  `non_python_with_identity` (that root's `vcs_upstream_versions` is empty). Of the python-track rows, 112 are
  `likely`, 62 `collision`, 37 `uncorroborated` and 1,184 `unrecovered`. `load_mapping_gap` reads all 12,362.
- **After merging main** (`2c0b2ac79f`, Story 37.5): `pyforge-atlas-test` gives 3,151 passed and 20 skipped, then
  103 passed (exit 0); the combined DAG has 70 nodes and the catalog 137 entries.

## Spec Change Log

- 2026-10-23: drafted from Story 37.9 and DW-atlas-37-9-1.

## Review Triage Log
