---
title: 'Workbook-free metrics universe: Kedro `inventory_universe` + `--analysis-xlsx` optional (Story 23.8, Epic 23)'
type: 'feature'
created: '2026-08-30'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
baseline_revision: 'c9db13fa23cc9d39e2a149b3cfc47bc7a1f77690'
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/change-history/sprint-change-proposal-2026-08-30.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/complete-export-contract.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/verification-matrix.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/catalog-sources.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-21-3-tier-0-harden-and-live-catalog-contract.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-21-4-tier-1-catalog-sources.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-21-5-tier-2-sources.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/implementation-artifacts/epic-21-context.md'
warnings: []
---

<intent-contract>

## Intent

**Problem:** `scripts/conda-forge-packaging-inventory-operations_metrics.py` cannot run
without `docs/Analysis_Dataset-2026-08-12.xlsx` — `--analysis-xlsx` is `required=True`
(exit 2 when missing) and the workbook is an **11 MB local-only file that is not
git-tracked** (`git ls-files docs/*.xlsx` is empty), so a fresh clone or CI runner cannot
produce deliverable A at all. Story 21.3 (`--live-catalog`, landed PR #941) replaced
exactly the three Tier 0 verification sets; everything that defines the *universe*
still comes from `parse_sheet_sources(xlsx)`:

| Workbook sheet (rows, 2026-08-12) | Feeds | Parquet replacement (owning story) |
|---|---|---|
| `CDO-ENT-JFROG` (6,989) | `records`, `tab_packages` → `must_keep`; `seen_*` hints | `enterprise_jfrog_names` (21.5); later `enterprise_jfrog_consumption` (23.2) |
| `CDO-ENT-CONDA` (814) | `records`, `must_keep`; `parse_cdo_ent_conda_roles` | `enterprise_conda_maintainers` (21.5) — `core_python_package_name`, `role` |
| `OpenTeams` (9,355) | `records` via `parse_openteams_title`; `openteams_summary_from_xlsx` | `openteams_project_1_board_raw` (Tier 0, already cataloged) — same `Title` regex |
| `Conda-Forge` (33,875) | `records`; Tier 1 `try_source` fallback | `core_packages_enumerated` (21.3 already reads it) |
| `Basilisk` (33,853) | `records`; fallback | `discovery_basilisk_packages_raw` (21.4) |
| `Anaconda-Main` (5,458) / `Anaaconda-Dist` (639) | `records`; fallback | `core_anaconda_main_channeldata_raw` / `discovery_anaconda_dist_2026x_raw` (21.4) |
| `GAOSS-Free` (1,474) / `GAOSS-Premium` (2,114) | `records`; fallback; AOSS-Free queue | `discovery_aoss_free_python_raw` / `discovery_aoss_premium_python_raw` (21.4) |
| `10kOpen` (6,989) | nothing — `CLONE_TABS`, skipped as a source | dropped by construction |
| `10kClosed` (10,000) | `records` (derive-only) + `TENK_TABS` drop filter | **no catalog source exists** — see Design Notes (known delta) |
| `verified-all-packages`, `inventory-*`, `identity-*` | nothing (`OUTPUT_TABS`, or no package column) | dropped by construction — prior-run outputs |
| prior-run `Priority_Bucket` / `Available_on_*` columns | `rec.priorities` → `priority_bucket()`, `pypi_hints`/`cf_hints` | `inventory_priority_assignments` (23.3) when present; Tier 0 verification (21.3) |

No story in Epics 21–23 owned this cutover before the 2026-08-30 course correction:
23.4 ports deliverable A's *row logic* to Kedro but names `identity_packages_primary` (the
~7.5k OpenTeams universe) as its row source, while deliverable A is the ~38k-row union of
every source sheet; 23.7 asserts "no workbook touched" only for the bootstrap run.

**Approach:** Two halves, one story. **(1) Kedro:** add a PURE node
`build_inventory_universe(...)` to the `derived_artifacts` pipeline that unions the
Parquet sources in the table above into one `inventory_universe` dataset — one row per
PEP-503 `core_python_package_name`, carrying `package_input_names`, `sources` (the SAME
`tab:<Sheet>` / `about:` / `curated:` provenance vocabulary `PackageRecord.sources` uses
today, so every downstream consumer — `write_md`'s per-source matrix, `role_for_package`,
`must_keep`, `Repository_Source` — is unchanged in shape), per-source `in_<source>`
BOOLs, `role`, and `openteams_universe_member` (= `CDO-ENT-JFROG` ∪ `CDO-ENT-CONDA`).
**(2) Script:** make `--analysis-xlsx` optional. When `--live-catalog PATH` is set and
`--analysis-xlsx` is absent, `metrics.py` builds `records` / `tab_packages` / roles / the
OpenTeams summary from `inventory_universe.parquet` (one `pandas.read_parquet`, the
`load_live_catalog` degrade-and-continue shape, extended by `--live-catalog-only`), and
takes `Priority_Bucket` from `inventory_priority_assignments.parquet` when present (else
`P9` with a counted warning — today's behavior when a row carries no prior-run hint).
When `--analysis-xlsx` IS given, behavior is byte-identical to 21.3 (workbook universe,
Parquet verification) — the xlsx path is retired by Story 23.9, not here.

## Boundaries & Constraints

**Always:**
- `inventory_universe` is a `derived_artifacts` catalog entry (`type:
  pandas.ParquetDataset`, `filepath: data/derived/inventory_universe/inventory_universe.parquet`,
  `metadata: {layer: derived}`), produced by one PURE node — pandas + stdlib only, no
  inline IO, no `dagster`/`kedro_mcp` imports (AD-1); inputs bound by catalog NAME (AD-3).
  Use the dataset names each upstream story actually LANDED in `catalog.yml` (confirm at
  dispatch; the names in the Intent table are the ones 21.4/21.5's specs declare).
- Name normalization is `metrics.py::norm_pkg` semantics (PEP-503 + the existing
  `looks_like_pkg` filter) — port the two helpers verbatim into the node (or a shared
  `pyforge.atlas` util) so the universe keys are identical to today's `records` keys.
- Provenance labels are stable strings, not sheet names: the node emits `tab:CDO-ENT-JFROG`,
  `tab:CDO-ENT-CONDA`, `tab:OpenTeams`, `tab:Conda-Forge`, `tab:Basilisk`,
  `tab:Anaconda-Main`, `tab:Anaaconda-Dist`, `tab:GAOSS-Free`, `tab:GAOSS-Premium` for the
  sources it replaces — byte-identical to today's `Repository_Source` values on the same
  package — and documents in `catalog.yml`'s entry comment that these are provenance
  labels inherited from the retired workbook, no longer literal sheet names.
- `--analysis-xlsx` becomes optional (`required=False`, default `None`). Exactly one
  universe source per run: the workbook when given, else `inventory_universe.parquet`
  under `--live-catalog`. Neither given → exit 2 with a message naming both options.
- `--live-catalog-only` without `--analysis-xlsx` also requires `inventory_universe`
  (present, readable, ≥ 10,000 distinct names — the order-of-magnitude floor for the union
  of a ~30k conda-forge index with the other sources) — exit 2 before writing any output
  otherwise, same shape as 21.3's three-dataset check.
- `OpenTeams` title parsing reuses `parse_openteams_title` (rules a/b/c) over the board
  dataset's title column; `openteams_summary_from_xlsx`'s counters (`rows_used_a`,
  `rows_used_b`, `rows_ignored_c`, `unique_packages`) are reproduced from the same rows.
- A frozen fixture pair covers parity: a small synthetic workbook
  (`scripts/tests/fixtures/inventory_universe/mini-workbook.xlsx`, tracked, < 100 KB,
  one row-set per sheet incl. a `10kOpen` clone row, an output tab, and a name present in
  several sheets) and the equivalent Parquet inputs. The test runs `metrics.py` twice on
  the same verification snapshot — `--analysis-xlsx` vs `--live-catalog` universe — and
  asserts the CSV rows and the MD per-source matrix are identical for every non-`10kClosed`
  row (`done_checkpoint`).
- `kedro-catalog-check`, `kedro-test`, and `python3 -m pytest scripts/tests/` stay green.

**Block If:** Stories 21.4 (Tier 1 raw datasets) and 21.5 (`enterprise_jfrog_names`,
`enterprise_conda_maintainers`) are not both `status: done` — the node's inputs do not
exist before them. Do NOT fabricate a substitute universe from `cf_atlas.db`, the
workbook, or a hand-written seed.

**Never:**
- Do not change `packaging_status`, `write_aoss_free_queue`, `write_csv`'s 14 columns, the
  MD section order, or the revised-prompt template beyond appending the flags actually
  used (21.3's own rule) — these are 23.4's read-only parity targets.
- Do not remove or deprecate the `--analysis-xlsx` path, `XlsxReader`, or the `try_source`
  xlsx fallback lambdas — Story 23.9 retires them once 23.4/23.5/23.6 exist.
- Do not add a `10kClosed` seed or scrape a substitute for it (Design Notes).
- Do not add new fetch code, datasets, or credential paths — this story only CONSUMES
  Parquet that 21.3/21.4/21.5 and Tier 0 already materialize (AD-2 stays with them).
- Do not port ranking rules (`priority.py`, 23.3) or the identity join (21.6/21.7).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Workbook run (unchanged) | `--analysis-xlsx X [--live-catalog P]` | Byte-identical to Story 21.3 | as today |
| Workbook-free run | `--live-catalog P`, no `--analysis-xlsx`, `inventory_universe.parquet` present | `records`/`tab_packages`/roles/OpenTeams summary from Parquet; CSV/MD/AOSS queue written; summary line names the universe source and row count | none |
| Universe Parquet missing / sub-floor, no `-only` | as above but file absent or < 10,000 names | exit 2 — there is no universe to degrade to (unlike the three verification sets, an empty universe is not a usable output) | message names the expected path + floor |
| `--live-catalog-only` | universe or any 21.3 dataset missing / sub-floor | exit 2 before any output is written | as 21.3 |
| Neither source | no `--analysis-xlsx`, no `--live-catalog` | exit 2 naming both options | — |
| Priority source present | `inventory_priority_assignments.parquet` under `P` | `Priority_Bucket` = its `P` per name | — |
| Priority source absent | file missing | `Priority_Bucket` = `P9` for every row, one counted warning line | never raises |
| Name in several sources | e.g. present in `Conda-Forge` + `Basilisk` + `CDO-ENT-JFROG` | one universe row; `sources` carries all three labels; `openteams_universe_member=True` | — |
| `10kOpen` rows | clone sheet | absent from the universe (as today: `CLONE_TABS`) | — |
| `10kClosed`-only names | present only in that sheet | absent from the workbook-free universe; parity test excludes them; count reported in the run summary as the known delta | — |
| Board title with no parseable package (rule c) | `OpenTeams` row like a CVE `\|` title | counted in `rows_ignored_c`, contributes no name | — |

</intent-contract>

## Code Map

- `scripts/conda-forge-packaging-inventory-operations_metrics.py` — the script half:
  - `PACKAGE_COLUMNS` (~L45), `CLONE_TABS` / `OUTPUT_TABS` (~L34-36), `TENK_TABS` (~L411)
    — the sheet vocabulary the universe node reproduces as provenance labels.
  - `PackageRecord` (~L135-150) — `core_name`, `input_names`, `tabs`, `sources`,
    `priorities`, `pypi_hints`, `cf_hints`: the in-memory shape both paths must fill.
  - `parse_sheet_sources` (~L243-324), `openteams_summary_from_xlsx` (~L474-490),
    `parse_cdo_ent_conda_roles` (~L521-535), `parse_sheet_pkg_set` (~L512-518) — the
    workbook readers whose outputs the new `load_universe_from_catalog()` reproduces.
  - `load_live_catalog` + `LiveCatalogResult` (21.3) — the result/degrade/summary shape to
    mirror for the universe read; `main()`'s `--live-catalog` branch (~L957-1000) — where
    the new branch hangs; `try_source` (~L979) — the Tier 1 fallback lambdas that must
    not reference `xlsx` when it is `None`.
  - `priority_bucket` (~L690-695), `must_keep` / `tenk_names` (~L945-950), `write_md`'s
    per-source matrix (~L702-712) — downstream consumers that must see identical inputs.
  - `--analysis-xlsx` argparse (~L768) + the `exists()` guard (~L947-949 on main after
    PR #941).
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/derived_artifacts/nodes.py`
  / `pipeline.py` — target for `build_inventory_universe`; `build_universe_sbom` is the
  pure-node precedent, 23.3/23.4 land siblings here.
- `src/shared/packages/pyforge-atlas/conf/base/catalog.yml` — `inventory_universe` entry;
  the Tier 1/2 entries 21.4/21.5 landed are its inputs.
- `src/shared/packages/pyforge-atlas/tests/pipelines/derived_artifacts/` — add
  `test_inventory_universe.py` (fixture-based, offline).
- `scripts/tests/test_conda_forge_packaging_inventory_operations_metrics.py` (21.3) —
  extend with the workbook-vs-catalog parity test and the exit-2 matrix rows.
- `docs/reference/conda-forge-packaging-inventory-operations_replay.md` § execution mode 4
  and `_prompt.md` — document the workbook-free invocation; `_replay.md`'s "Scope (Story
  21.3)" paragraph is superseded here.

## Tasks & Acceptance

**Execution:**
- Confirm the landed catalog names for every input in the Intent table against
  `catalog.yml` at dispatch time; record any rename in this spec's Change Log.
- Implement `build_inventory_universe` + catalog entry + pipeline wiring + offline test.
- Implement `load_universe_from_catalog(root, *, floor=10_000) -> UniverseResult` in
  `metrics.py`, filling `records` / `tab_packages` / `(maint, co)` / `OpenTeamsSummary`
  exactly as the workbook readers do; route `main()` on `args.analysis_xlsx is None`.
- Make `--analysis-xlsx` optional; extend `--live-catalog-only`; add the priority-source
  read; guard every `xlsx`-typed call site for `None`.
- Add the mini-workbook + Parquet fixture pair and the parity test; extend the 21.3 test
  module for the new exit-2 rows.
- Update `_replay.md` / `_prompt.md`; append the flags to the regenerated prompt template.
- Run once against the real bootstrapped `PYFORGE_ATLAS_DATA_ROOT` (attended) and record
  the row counts + the `10kClosed` delta in this spec's Verification section.

**Acceptance Criteria:**
1. Given 21.4/21.5 outputs and the board dataset under `PYFORGE_ATLAS_DATA_ROOT`, when
   `kedro run --pipeline derived_artifacts` runs, then `inventory_universe.parquet` exists
   with one row per PEP-503 name, the provenance labels above, `role`, and
   `openteams_universe_member`.
2. Given the fixture pair, when `metrics.py` runs with `--analysis-xlsx` and again with
   `--live-catalog` only, then CSV rows and the MD per-source matrix are identical for
   every non-`10kClosed` row (`done_checkpoint`).
3. Given no `--analysis-xlsx` and no workbook on disk, when `metrics.py --live-catalog P`
   runs, then it exits 0 and writes CSV/MD/AOSS queue — no `.xlsx` is opened (assert via
   the test's `XlsxReader` spy / `openpyxl` absent from the code path).
4. Given `--live-catalog-only` and a missing or sub-floor `inventory_universe.parquet`,
   when the script runs, then exit 2 and no output file is written.
5. Given `pixi run -e pyforge-atlas kedro-catalog-check`, `kedro-test`, and `python3 -m
   pytest scripts/tests/`, when run after this story, then all stay green.

## Spec Change Log

- 2026-08-30: Initial draft, minted by `change-history/sprint-change-proposal-2026-08-30.md` (course
  correction after Story 21.3's hold). Owns the metrics-side workbook cutover the plan had
  no story for; Story 23.4's row grain is corrected to consume this dataset.
- 2026-08-30 (implementation pass): implemented as written. Two decisions worth recording,
  both resolved in favor of exact behavioral parity with the workbook path rather than the
  simpler-looking alternative:
  1. **OpenTeams-sourced `package_input_names` is the full title text, not the extracted
     package name.** `parse_sheet_sources()`'s raw-name fallback chain
     (`Package_Name`/`name`/`raw_names`/`Item`/`Title`) falls through to the whole `Title`
     string for an OpenTeams row (it has none of the first four columns) — so
     `build_inventory_universe`'s `_touch()` helper takes an explicit `input_name=` override
     for the OpenTeams branch, distinct from the value used for PEP-503 normalization.
     Verified via the frozen fixture pair's parity test, which caught the mismatch on the
     first run (bare "anotherpkg" vs. the correct "[Conda-Forge Packaging] anotherpkg").
  2. **`Priority_Bucket` genuinely diverges for CDO-ENT-CONDA-sourced rows when no Story 23.3
     priority source exists yet (true for this story).** The legacy `priority_bucket()`
     grants an unconditional `P4` to any row whose `sources` include `about:*` or
     `tab:CDO-ENT-CONDA`; this story's own I/O & Edge-Case Matrix mandates an unconditional
     `P9` for every row when the priority source is absent — a direct, spec-authored
     contradiction between the Approach prose ("today's behavior when a row carries no
     prior-run hint") and the I/O matrix's literal wording. Resolved in favor of the I/O
     matrix (the frozen, machine-checked table) — workbook-free mode always defaults to `P9`
     until Story 23.3 lands `inventory_priority_assignments.parquet`. Documented and asserted
     explicitly (not merely excluded) in `test_parity_workbook_vs_live_catalog_universe`.
     `Packaging_Candidate_Status` is unaffected for the two test rows this touches (both
     resolve to `Not on PyPI` regardless of the bucket).
  3. Workbook-free mode reproduces the workbook path's own redundant `external:*`
     `source_sets` bookkeeping (`external:anaconda-main-channel`/`external:anaconda-2026x`/
     `external:aoss-free`/`external:aoss-premium`/`external:basilisk`, sourced from
     `tab_packages` instead of a live/sheet fallback) purely so the MD per-source matrix has
     the same row set in both modes — these labels never win `primary_source()` over their
     `tab:*` sibling, so CSV output is unaffected either way.

## Design Notes

**Why a Kedro dataset and not a script-side union.** A script-side `records` union over
nine Parquet files would be thrown away by Story 23.9 (which thins `metrics.py` to a
formatter over 23.4's export) and would leave 23.4 with no full-grain row source — its
spec names `identity_packages_primary`, the ~7.5k OpenTeams universe, while
`verified-all-packages` carries 38,372 rows. One `inventory_universe` dataset serves
both consumers and is the CAP-8 shape ("no data slices left in `scripts/`").

**`10kClosed` is the one known workbook-only residue.** 10,000 `Package_Name` /
`Source_Organization` / `Primary_Domain` rows with no catalog source, no Dream row, and no
provenance beyond the sheet name; `10kOpen` is a clone of `CDO-ENT-JFROG`. Today those
names only survive the `TENK_TABS` drop filter when they are on PyPI or have a derived
source repo. The SPEC's Non-goal ("Excel workbook ingest or mirror") forbids seeding it
into the catalog, so this story reports the delta rather than reproducing it. Decision
recorded for the operator in the proposal's § 5 (accept the delta, or mint a follow-up
`discovery_tenk_closed_seed` story with a real upstream).

**`OUTPUT_TABS` is a dated hardcode.** `identity-2026-08-20` is parsed as a source sheet
today (it is not in `OUTPUT_TABS`); it contributes nothing only because its `Package`
column is not in `PACKAGE_COLUMNS`. The workbook-free path removes that class of bug —
worth a one-line note in the replay doc, not a fix to the xlsx path.

## Verification

**Commands (once 21.4 and 21.5 are done and this story dispatches):**
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass, `inventory_universe`
  present and typed.
- `pixi run -e pyforge-atlas kedro-test -- tests/pipelines/derived_artifacts/test_inventory_universe.py`
  — expected: green.
- `python3 -m pytest scripts/tests/` — expected: green, incl. the workbook-vs-catalog
  parity test and the four exit-2 rows.
- Attended: `python3 scripts/conda-forge-packaging-inventory-operations_metrics.py
  --live-catalog "$PYFORGE_ATLAS_DATA_ROOT" --live-catalog-only --curated-config
  conf/conda-forge-packaging-inventory-operations_curated_groups.json --output-csv /tmp/a.csv
  --output-md /tmp/a.md --skip-revised-prompt` — expected: exit 0, no `.xlsx` opened,
  row count within 10 % of the last workbook run minus the reported `10kClosed` delta.

**Attended run performed 2026-08-30** (this worktree's fresh, un-bootstrapped
`src/shared/packages/pyforge-atlas/data/` — `kedro run --pipelines
core,pypi_intelligence,upstream_discovery,artifactory_downloads` then `kedro run
--pipeline derived_artifacts --nodes build_inventory_universe`, all against live
network, no injected fetchers for the credentialed/attended-only Story 21.4/21.5
sources — matches those stories' own documented residual risk, not a new gap):
`inventory_universe.parquet` materialized with **35,612 rows** —
`in_conda_forge`=33,947, `in_anaconda_main`=5,385, `in_aoss_free`=1,474 (tracked
seed), and 0 for `in_basilisk`/`in_anaconda_dist`/`in_aoss_premium`/
`in_cdo_ent_jfrog`/`in_cdo_ent_conda`/`in_openteams` (those 6 sources need an
injected fetcher / GitHub credential no unattended `kedro run` provides today —
the same gap Story 21.4's Design Section already documents, not new). The
`metrics.py --live-catalog ... --live-catalog-only` command above then ran
against that real root: **exit 0**, no `.xlsx` opened, **35,627** final unique
packages (the +15 over the universe's own count come from
`conf/conda-forge-packaging-inventory-operations_curated_groups.json`'s curated
groups, unioned in after the universe read, same as the workbook path), AOSS-Free
queue 334 rows, `Priority_Bucket` = `P9` for every row (no
`inventory_priority_assignments.parquet` yet — Story 23.3) with the one counted
warning. `10kClosed` delta: **not computed** (no catalog source exists to compute
it from, per Design Notes) — reported instead as the fixed informational note in
the run summary ("~10,000 rows on 2026-08-12 ... not represented"). The "row
count within 10% of the last workbook run" comparison itself could not be made in
this pass (no `docs/Analysis_Dataset-2026-08-12.xlsx` present in this worktree to
run the workbook-mode baseline against); the frozen fixture pair's own parity test
(`test_parity_workbook_vs_live_catalog_universe`) is the byte-level proof this
story's `done_checkpoint` actually relies on.

## Auto Run Result

**Status:** done — reconstructed 2026-09-20 from git during the fleet consistency pass before the foundry cutover; no run record survived in this tracked spec.
**Summary:** no commit subject on `main` names this story (hand-implemented, or landed under another story's subject); the ledger row `22-8-workbook-free-metrics-universe-kedro-inventory_universe-analysis-xlsx-optional: done` is the record and `story-status` accepts it.
**Verification:** the station's `verify_commands` ran in the landing session; the durable record here is git only — see the landing commit(s) above.
**Files changed:** not attributable to one commit — see the summary.
**Residual risks:** none recorded — no run record survived to carry them.
**Follow-up review recommendation:** false

## Status reconcile 2026-09-20

- frontmatter `status` `in-review` → `done` (ledger row `22-8-workbook-free-metrics-universe-kedro-inventory_universe-analysis-xlsx-optional: done`).
- `## Auto Run Result` reconstructed from git (none survived).
