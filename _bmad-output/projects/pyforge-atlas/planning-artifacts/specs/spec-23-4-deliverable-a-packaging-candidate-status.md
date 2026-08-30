---
title: 'Deliverable A + Packaging_Candidate_Status derived export (Story 23.4, Epic 23)'
type: 'feature'
created: '2026-08-30'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/complete-export-contract.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/verification-matrix.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/stories.yaml'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-23-3-priority-rules-in-kedro.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/implementation-artifacts/epic-21-context.md'
warnings: []
---

<intent-contract>

## Intent

**Problem:** The exact 14-column "deliverable A" row shape (`write_csv`'s `cols` list) and the
`Packaging_Candidate_Status` classification (`packaging_status`) only exist today inside the
attended `scripts/conda-forge-packaging-inventory-operations_metrics.py` xlsx-merge run, and
the AOSS-Free extra-Mason-queue derivation (`write_aoss_free_queue`) only runs as a side effect
of that same script's `main()`. `complete-export-contract.md` §2/§3.1 requires both moved into
Kedro-native derived exports — `inventory_verified_packages.parquet` (the 14-column deliverable
A) and its sibling `inventory_aoss_free_queue.parquet` — sourced from already-materialized
Atlas Parquet (verification BOOLs, `inventory_priority_assignments.P` from Story 23.3, Tier 1
AOSS raw, enterprise conda-maintainer roles) instead of xlsx tabs, live HTML scraping, or a
merge pass over the workbook.

**Approach:** Add PURE nodes to the `derived_artifacts` pipeline (same pipeline as Story 23.3,
for the reasons in that story's Design Notes) that: (1) verbatim-port
`metrics.py::packaging_status(pypi_ok, cf_ok, pbucket)` as the `Packaging_Candidate_Status`
rule; (2) assemble the exact 14-column `inventory_verified_packages.parquet` row shape from
already-Kedro-native inputs — verification BOOLs (`PyPI_Verified`/`CondaForge_Verified`),
`inventory_priority_assignments.P` (23.3), `enterprise_conda_maintainers.role` (23.2/21.5),
and provenance/URL columns; (3) verbatim-port `write_aoss_free_queue`'s set-difference
semantics — including the candidate pre-filter that lives in `metrics.py::main()`, not inside
`write_aoss_free_queue` itself — as a second node writing `inventory_aoss_free_queue.parquet`.
This is a **port, not a redesign**: every column, PURL/URL format string, and classification
branch of `metrics.py`'s existing logic carries over unchanged.

## Boundaries & Constraints

**Always:**
- `inventory_verified_packages.parquet`'s column order matches `complete-export-contract.md`
  §2's 14-column table exactly, which is itself byte-identical to `metrics.py::write_csv`'s
  `cols` list: `Repository_Source`, `Role`, `Package_Input_Name`, `Core_Python_Package_Name`,
  `PyPI_Verified`, `CondaForge_Verified`, `Priority_Bucket`, `Packaging_Candidate_Status`,
  `PyPI_PURL`, `PyPI_Package_URL`, `Conda-forge_PURL`, `Conda-Forge_Package_URL`,
  `Conda-Forge_FeedStock_URL`, `Verification_Timestamp_UTC`.
- `packaging_status` is ported verbatim: parse `pbucket` as `int(pbucket[1:])` when it starts
  with `P` and the remainder is digits, else default `9`; then the four-branch decision —
  `pypi_ok and cf_ok` → `"Already Packaged"`; `pypi_ok and not cf_ok` → `"High Priority
  Candidate"` when `P<=8` else `"Low Priority Candidate"`; `not pypi_ok and cf_ok` →
  `"Conda-Forge Only"`; else `"Not on PyPI"`.
- PURL/URL construction is ported verbatim and only populated when verified, `"N/A"` otherwise:
  `PyPI_PURL = f"pkg:pypi/{pkg}"`, `PyPI_Package_URL = f"https://pypi.org/project/{pkg}/"`,
  `Conda-forge_PURL = f"pkg:conda/{pkg}?channel=conda-forge"`, `Conda-Forge_Package_URL =
  f"https://anaconda.org/conda-forge/{pkg}/"`, `Conda-Forge_FeedStock_URL =
  f"https://github.com/conda-forge/{pkg}-feedstock"`.
- `write_aoss_free_queue`'s set semantics are ported in full, including the pre-filter step
  that happens in `metrics.py::main()` before the call (`aoss_free_candidates = {pkg for pkg in
  aoss_free if pypi_verified.get(pkg, False) and pkg not in cf_or_pm}`) and the universe
  subtraction inside the function itself (`queue = sorted(aoss_free_names - universe_names)`,
  `universe_names` = `CDO-ENT-JFROG` ∪ `CDO-ENT-CONDA` membership, sourced from
  `enterprise_jfrog_consumption` + `enterprise_conda_maintainers` in the Kedro-native version).
  The literal `Reason` string, `"On PyPI, not on conda-forge, not in CDO consumption
  (GAOSS-Free)"`, is preserved for parity.
- `Role` is sourced from `enterprise_conda_maintainers.role` (`Maintainer` / `Co-Maintainer` /
  `N/A`), matching `metrics.py::role_for_package`'s three-way mapping.
- Both nodes are PURE — pandas + stdlib only, no inline IO, no `dagster`/`kedro_mcp` imports
  (AD-1) — same shape as `build_universe_sbom` and this epic's Story 23.3 node.
- A frozen fixture corpus (reusing or extending Story 23.3's fixture directory) covers each of
  the four `Packaging_Candidate_Status` branches plus at least one AOSS-Free-queue-eligible row
  and one row correctly excluded from the queue (already in the OpenTeams universe). Running
  both `metrics.py`'s relevant functions (unmodified) and the new nodes over the same rows must
  produce identical column values — this is the story's `done_checkpoint`.

**Block If:** Stories 21.3 (Tier 0 hardening + verification BOOLs available as Kedro Parquet)
and 23.3 (`inventory_priority_assignments`, this story's `Priority_Bucket` source) are not both
`status: done` — see Design Notes (same dispatch-ordering pattern `spec-21-8` and
`spec-23-3-priority-rules-in-kedro.md` already established).

**Never:**
- Do not modify `metrics.py::packaging_status` or `write_aoss_free_queue` — both are read-only
  parity targets.
- Do not let the AOSS-Free queue expand the OpenTeams universe — it is a separate, Mason-facing
  supplementary artifact by design (`write_aoss_free_queue`'s own docstring, restated in
  `complete-export-contract.md` §2: "Never merges into or expands that universe").
- Do not implement Story 23.5's `identity_complete_export.parquet` join here — this story's
  outputs are exactly `inventory_verified_packages.parquet` and
  `inventory_aoss_free_queue.parquet`.
- Do not add Tier 3 bulk-OS cross-channel BOOLs (`in_homebrew`, `in_nixpkgs`, etc., Story 23.1)
  to deliverable A's 14 columns — those live only in the wider `identity_complete_export.parquet`
  (§4), not this 14-column contract.
- Do not read live HTML sources (AOSS/Basilisk/Anaconda-release pages) directly in the Kedro
  node — those are Tier 1 catalog sources (Story 21.4's territory); this story only consumes
  their already-materialized Parquet output.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| PyPI-yes, conda-forge-yes | `PyPI_Verified=True`, `CondaForge_Verified=True` | `Packaging_Candidate_Status="Already Packaged"` | None |
| PyPI-yes, conda-forge-no, high priority | `PyPI_Verified=True`, `CondaForge_Verified=False`, `Priority_Bucket` ∈ P1-P8 | `"High Priority Candidate"` | None |
| PyPI-yes, conda-forge-no, low priority | `PyPI_Verified=True`, `CondaForge_Verified=False`, `Priority_Bucket` ∈ P9-P10 | `"Low Priority Candidate"` | None |
| PyPI-no, conda-forge-yes | `PyPI_Verified=False`, `CondaForge_Verified=True` | `"Conda-Forge Only"` | None |
| PyPI-no, conda-forge-no | both `False` | `"Not on PyPI"` | None |
| Malformed/missing `Priority_Bucket` | e.g. empty string, not `P<digits>` | Treated as `P9` (matches `packaging_status`'s `pbucket[1:].isdigit()` guard defaulting to `9`) | Never raises |
| AOSS-Free candidate | On PyPI, not on conda-forge, not in `CDO-ENT-JFROG` ∪ `CDO-ENT-CONDA` | Row appears in `inventory_aoss_free_queue.parquet` with the literal `Reason` string and a snapshot `Verification_Timestamp_UTC` | None |
| AOSS-listed but already in universe | On PyPI, not on conda-forge, but IS in `CDO-ENT-JFROG` or `CDO-ENT-CONDA` | Excluded from the AOSS-Free queue (universe membership always wins) | None — this is the set-difference itself, not an error path |
| Upstream dependency not yet materialized | Story 21.3 or 23.3 not `status: done` at dispatch time | This story is not dispatched (`Block If`) | See Design Notes |

</intent-contract>

## Code Map

- `scripts/conda-forge-packaging-inventory-operations_metrics.py` — the read-only parity
  target:
  - `packaging_status` (~L607-615) — the `Packaging_Candidate_Status` rule, port verbatim.
  - `write_csv` (~L626-646) — the 14-column `cols` list defining deliverable A's exact order.
  - `role_for_package` (~L618-623) — `Role` three-way mapping.
  - `write_aoss_free_queue` (~L649-678) — universe-subtraction + CSV write; port the
    subtraction logic (`queue = sorted(aoss_free_names - universe_names)`), not the CSV-write
    mechanics (the Kedro node writes Parquet via the catalog, not `csv.DictWriter`).
  - `main()`'s pre-filter for AOSS-Free candidates (~L948-956): `aoss_free_candidates = {pkg
    for pkg in aoss_free if pypi_verified.get(pkg, False) and pkg not in cf_or_pm}` and
    `must_keep = tab_packages.get("CDO-ENT-JFROG", set()) | tab_packages.get("CDO-ENT-CONDA",
    set())` — this pre-filter lives in `main()`, not inside `write_aoss_free_queue` itself; the
    Kedro node must replicate both steps, not just the function body.
  - `main()`'s per-row assembly (~L971-1008) — the field-by-field construction of each output
    row, the reference for the new node's row-builder.
- `_bmad-output/.../specs/spec-atlas-kedro-catalog-expansion/complete-export-contract.md` §2 and
  §3.1 — the exact contract this story implements (verbatim in the task brief above).
- `_bmad-output/.../specs/spec-atlas-kedro-catalog-expansion/verification-matrix.md` — confirms
  `Packaging_Candidate_Status` is mapped to `inventory_verified_packages` (Epic 23.4) and
  `PyPI_Verified`/`CondaForge_Verified` are already mapped to `pypi_simple_index_raw` +
  `pypi_json_raw` / `core_channeldata_raw` + `pypi_conda_mapping` (Story 21.3's territory, this
  story's upstream input).
- `_bmad-output/.../specs/spec-23-3-priority-rules-in-kedro.md` — this story's `Priority_Bucket`
  input is `inventory_priority_assignments.P` from that story; do not re-derive priority here.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/derived_artifacts/nodes.py` —
  target file, alongside Story 23.3's `assign_inventory_priority`.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/derived_artifacts/pipeline.py`
  — add two `node(...)` entries (verified-packages export, AOSS-free-queue export); `inputs=`
  bind to catalog NAMES per `AD-3`, including `inventory_priority_assignments` as a
  cross-node-within-pipeline dependency on Story 23.3's output.
- `src/shared/packages/pyforge-atlas/conf/base/catalog.yml` — add
  `inventory_verified_packages` (`type: pandas.ParquetDataset`, `filepath:
  data/derived/inventory_verified_packages/inventory_verified_packages.parquet`, `metadata:
  {layer: derived}`) and `inventory_aoss_free_queue` (same shape, `filepath:
  data/derived/inventory_aoss_free_queue/inventory_aoss_free_queue.parquet`) — same convention
  as the neighboring `derived_universe_sbom` / `inventory_priority_assignments` (23.3) entries.
- `src/shared/packages/pyforge-atlas/tests/pipelines/derived_artifacts/test_universe_sbom.py` —
  existing test-file precedent; add
  `test_inventory_verified_packages.py`/`test_inventory_aoss_free_queue.py` siblings.

## Tasks & Acceptance

**Execution:**
- Add `build_inventory_verified_packages(identity_packages_primary, verification_bools,
  inventory_priority_assignments, enterprise_conda_maintainers, parameters=None)` (exact input
  set/order confirmed against the live shape of Story 21.3's verification-BOOL Parquet output
  and Story 23.3's landed `inventory_priority_assignments` at dispatch time) to
  `pipelines/derived_artifacts/nodes.py`, porting `packaging_status` and the 14-column row
  assembly verbatim.
- Add `build_inventory_aoss_free_queue(discovery_aoss_free_python_raw, verification_bools,
  enterprise_jfrog_consumption, enterprise_conda_maintainers, parameters=None)` porting
  `write_aoss_free_queue`'s universe-subtraction semantics plus `main()`'s candidate pre-filter,
  verbatim.
- Wire both nodes into `pipelines/derived_artifacts/pipeline.py` with `outputs=
  "inventory_verified_packages"` and `outputs="inventory_aoss_free_queue"` respectively.
- Add both catalog entries per the Code Map's dataset shape.
- Extend the frozen fixture corpus (Story 23.3's directory, or a sibling) with rows covering
  all nine I/O-matrix scenarios above.
- Add `tests/pipelines/derived_artifacts/test_inventory_verified_packages.py` and
  `test_inventory_aoss_free_queue.py` asserting column-order and value parity against the
  fixture, one test case per I/O-matrix scenario.
- Confirm `pixi run -e pyforge-atlas kedro-catalog-check` and `kedro-test` stay green with the
  two new catalog entries and nodes.

**Acceptance Criteria:**
- Given the fixture corpus's four `Packaging_Candidate_Status` scenarios (already-packaged,
  high-priority candidate, low-priority candidate, conda-forge-only, not-on-PyPI — five total
  branches), when the new node runs, then each row's status matches `packaging_status`'s output
  on the same inputs.
- Given `inventory_verified_packages.parquet`, when read, then its column order is exactly the
  14 columns listed in `complete-export-contract.md` §2, with `PyPI_PURL`/`Conda-forge_PURL`/
  etc. populated or `"N/A"` per verification state.
- Given the fixture's AOSS-Free-eligible and AOSS-Free-excluded rows, when the queue node runs,
  then the eligible row appears in `inventory_aoss_free_queue.parquet` with the literal `Reason`
  string, and the excluded (already-in-universe) row does not appear.
- Given the full fixture corpus, when `inventory_verified_packages.parquet` and
  `inventory_aoss_free_queue.parquet` are compared against `metrics.py`'s unmodified output on
  the same corpus, then every column value matches (`done_checkpoint`).
- Given `pixi run -e pyforge-atlas kedro-catalog-check` and `kedro-test`, when run after this
  story, then both stay green.

## Spec Change Log

- 2026-08-30: Initial draft. Ports `metrics.py::packaging_status` and `write_aoss_free_queue`
  into two new `derived_artifacts` Kedro nodes producing `inventory_verified_packages.parquet`
  (14-column deliverable A) and its `inventory_aoss_free_queue.parquet` sibling. Written ahead
  of Stories 21.3 and 23.3's implementation — see Design Notes for the resulting dispatch-timing
  consequence.

## Design Notes

**Pipeline choice: `derived_artifacts`, matching Story 23.3.** Same reasoning as
`spec-23-3-priority-rules-in-kedro.md`'s Design Notes: this is a PURE join/derive over
already-materialized Parquet, not a discovery concern, and it has a direct same-pipeline
dependency on Story 23.3's `inventory_priority_assignments` output — keeping both in
`derived_artifacts` avoids a needless cross-pipeline edge for a two-node chain the contract's
own build-order diagram (`VER` fed by `T0`/`T1`/`T2`/`T3`, joined with `PRI` downstream into
`COMP`) already groups together.

**This story cannot be dispatched yet.** As of this spec's drafting (2026-08-30), Story 21.3
(the `--live-catalog` contract and Tier-0-hardened verification BOOLs) has not landed —
confirmed via `grep` for `live.catalog`/`live_catalog` across `scripts/` and `src/`, zero hits
— and Story 23.3 (this story's `Priority_Bucket` source) is itself blocked on 21.6/23.2 per its
own Design Notes. Do not dispatch `bmad-build`/`bmad-loop` against this spec until both 21.3 and
23.3 are `status: done`. As with `spec-21-8` and `spec-23-3-priority-rules-in-kedro.md`, the
spec itself is complete and actionable now; what's missing is upstream code, not clarity —
whoever picks this up must re-check `21.3`/`23.3`'s live status before dispatch.

**Porting scope is read-only against `metrics.py`.** `packaging_status` is nine lines with an
unambiguous four-branch decision table; `write_aoss_free_queue` is a straightforward
set-difference plus CSV write. Porting both verbatim (Parquet write instead of CSV, Kedro
catalog inputs instead of xlsx tabs / live HTML) is normal step-03 implementation work, not an
open spec question — the one non-obvious detail worth flagging (and flagged above in the Code
Map) is that the AOSS-Free candidate pre-filter lives in `metrics.py::main()`, not inside
`write_aoss_free_queue` itself, so a naive "port the function" pass would miss it if read in
isolation.

## Verification

**Commands (run once Stories 21.3 and 23.3 are done and this story dispatches):**
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass,
  `inventory_verified_packages` and `inventory_aoss_free_queue` present and well-formed.
- `pixi run -e pyforge-atlas kedro-test -- tests/pipelines/derived_artifacts/test_inventory_verified_packages.py tests/pipelines/derived_artifacts/test_inventory_aoss_free_queue.py`
  (or the equivalent full-suite `kedro-test` run) — expected: all fixture-corpus parity
  assertions pass.
- Manual/CI diff of `metrics.py`'s `packaging_status`/`write_aoss_free_queue` unmodified output
  against the new nodes' output on the same frozen fixture corpus — expected: identical column
  values per row (`done_checkpoint`).
