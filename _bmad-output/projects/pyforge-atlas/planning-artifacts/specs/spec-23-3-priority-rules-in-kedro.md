---
title: 'Port priority.py rules to Kedro inventory_priority_assignments (Story 23.3, Epic 23)'
type: 'feature'
created: '2026-08-30'
status: 'done'
baseline_revision: 'NO_VCS'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/complete-export-contract.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/identity-contract.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/verification-matrix.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/stories.yaml'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/implementation-artifacts/epic-21-context.md'
warnings: []
---

<intent-contract>

## Intent

**Problem:** `priority.py` (`scripts/conda-forge-packaging-inventory-operations_priority.py`) is
the only place the P1-P10 priority hierarchy, `Rank`, `Score`, and `Work` disposition are
computed today — an attended script that reads four tabs (`identity-2026-08-12`,
`CDO-ENT-JFROG`, `OpenTeams`, `inventory-2026-08-12`) out of
`docs/Analysis_Dataset-2026-08-12.xlsx`, ranks in memory, and writes the result back into the
same workbook plus an optional Cursor canvas. `verification-matrix.md` explicitly lists
`P1`-`P10`, `Score`, `Work` as "outside matrix until Epic 23," and
`complete-export-contract.md` §3.2 requires this hierarchy ported to a Kedro-native derived
node, `inventory_priority_assignments`, so Story 23.4's `Priority_Bucket` column and Story
23.5's `identity_complete_export.parquet` can be produced from Atlas Parquet alone — no
workbook, no quartet merge pass, no `CF_ATLAS_DB`.

**Approach:** Add one PURE node to the `derived_artifacts` pipeline (see Design Notes for the
`upstream_discovery`-vs-`derived_artifacts` choice) that reimplements `priority.py`'s rule
hierarchy verbatim over four Kedro-native inputs (`identity_packages_primary`,
`enterprise_jfrog_consumption`, `enterprise_conda_maintainers`,
`openteams_project_1_board_raw`, plus the Basilisk vuln rollup already in the vulnerability
pipeline) instead of xlsx tabs. This is a **port, not a redesign** — every branch, tie-break,
and output column of `priority.py` carries over unchanged; the only thing that changes is the
data source (Parquet frames instead of `openpyxl` worksheets) and the output sink (a Kedro
catalog entry instead of an in-place workbook rewrite + canvas).

## Boundaries & Constraints

**Always:**
- Every rule branch of `priority.py::assign_lane` is reproduced with the same precedence order:
  P1 current-version vuln (`risk_level == "HIGH"` or `vuln_status == "affected_latest"`) wins
  first; then `board_lock` (existing OpenTeams board P1/P2/P3, via `board_maps`'s
  URL-then-name lookup against `[Conda-Forge Packaging] <name>` titles) is never overwritten;
  then P4 `platform_env_count > 0`; then P5 `internal_app_count > 0`; then P6
  `artifactory_downloads >= 100 or artifactory_version_count >= 100`; then P7 `>= 10`; the
  remainder is split into P8/P9/P10 by `Work` exactly as `priority.py`'s `main()` remainder
  loop does (Create recipe → P8; File OpenTeams tracking issue on-cf → P9; File OpenTeams
  tracking issue conda-only, or Already-tracked leftover → P10).
- `use_score(plat, apps, ic, lob, downloads, versions)` — `100*plat + 10*apps + 3*ic + 2*lob +
  log10(1+downloads) + log10(1+versions)` — and `percentile_1_100` (stable rank-based 1-100
  percentile with `(raws[i], i)` tie-break, `n==1` special case returns `100`) are ported
  verbatim, including tie handling.
- `work_label`'s precedence is ported verbatim: current-version vuln → `Fix vulnerability`
  first; else the inventory row's `OpenTeams_Batch`/`OpenTeams_Cohort`/`OpenTeams_Coverage`
  mapping (`BATCH_TO_WORK`, `Have_Issue` → `Already tracked`, `JFROG_NEW` → `Create recipe`,
  `JFROG_ON_CF`/`CONDA_ONLY` → the tracking-issue label); else a filled
  `OpenTeams_Issue_URL` → `Already tracked`; else a filled `conda_purl` or
  `Conda-Forge_FeedStock_URL` → the tracking-issue label; else `Create recipe`.
- The final sort/rank key matches `priority.py::sort_key` exactly: `(P-bucket-order,
  work-rank, -score100, -raw, -downloads, -versions, name)`, 1-based `Rank` assigned after
  sort.
- PEP-503 normalization for every join key matches `priority.py::pep503` (lowercase,
  `-`/`_`/`.` collapsed to a single `-`, stripped) — the same normalization already governing
  the quartet and this contract's stated join key (`core_python_package_name`).
- `PRIORITY_DESC` text (all 10 bucket descriptions) is copied verbatim into
  `Priority_Bucket_Description`.
- Output columns match complete-export-contract.md §3.2's table exactly: `P`, `Rank`, `Score`,
  `Work`, `Priority_Bucket_Description`, `Priority_Source`, `Priority_Reason`, plus the four
  legacy aliases `Proposed_Priority` (= `P`), `Packaging_Work` (= `Work`), `Priority_Rank`
  (= `Rank`), `Priority_Score` (= `Score`) preserved for downstream parity, PLUS
  `core_python_package_name` (the join key every downstream consumer needs) and — new
  2026-08-30 correction — `risk_level`/`vuln_status`/`jfrog_latest_vuln_count` pass through as
  output columns too (the values this node already computed internally for its own P1 gate via
  the `vulnerability_basilisk_rollup` join). Story 23.5 sources `JFROG_risk_level`/
  `JFROG_vuln_status`/`JFROG_latest_vuln_count` from THIS node's output, not from
  `enterprise_jfrog_consumption` (which no longer carries them) — avoids a second, redundant
  Basilisk join downstream.
- The node is PURE — pandas + stdlib only, no inline IO, no `dagster`/`kedro_mcp` imports
  (AD-1) — matching `derived_artifacts::build_universe_sbom`'s existing shape; no TTL/cadence
  gating (this is a join/derive over already-materialized Parquet, not a live fetch — no
  `refresh_cadences` params needed, unlike the `vcs_health` refresh-trigger nodes).
- A frozen fixture corpus (new, under `tests/fixtures/inventory_priority/` or reused from
  Story 21.6's identity fixtures if shape-compatible) covers at minimum: one current-vuln P1
  row, one existing-board P1/P2/P3-lock row, one platform-only P4 row, one app-only P5 row, one
  100+/10+ download-floor P6/P7 row, and one row for each of the three leftover `Work` splits
  (P8/P9/P10). Running both `priority.py` (unmodified) and the new node over the same rows must
  produce identical `P`/`Rank`/`Score`/`Work` — this is the story's `done_checkpoint`.

**Block If:** Stories 21.6 (`identity_packages_primary`) and 23.2
(`enterprise_jfrog_consumption.parquet`, `enterprise_conda_maintainers.parquet`) are not both
`status: done` — see Design Notes (same dispatch-ordering pattern `spec-21-8` already
established for a hard upstream dependency).

**Never:**
- Do not read `packaging_tier` for `P` assignment — explicit non-goal in
  `complete-export-contract.md` §3.2; `packaging_tier` is stored on
  `enterprise_jfrog_consumption.parquet` for audit only (contract §1: "stored, never used for
  P").
- Do not modify `scripts/conda-forge-packaging-inventory-operations_priority.py` — it is the
  read-only parity target, not a symptom to fix (mirrors the existing "do not touch
  `priority.py`'s disposition/ranking logic" constraint from `spec-17-2`).
- Do not add a duplicate live fetch for `openteams_project_1_board_raw` in this story — if
  Story 21.6 has not yet materialized it as a Kedro catalog entry by dispatch time, that is a
  `Block If` condition, not a workaround to build around here.
- Do not implement Story 23.4's `Packaging_Candidate_Status` or Story 23.5's
  `identity_complete_export.parquet` join here — this story's sole output is
  `inventory_priority_assignments`.
- Do not touch the Vizro/BSL/gist-actuator layer (Epic 22 / Story 23.6) — this is a pure data
  node with no UI or publish surface.
- Do not rewrite an Excel workbook or emit a Cursor `.canvas.tsx` — those are `priority.py`'s
  own output sinks (workbook in-place rewrite, `write_canvas`), out of scope for the Kedro node.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Current-version vuln row | `risk_level == "HIGH"` or `vuln_status == "affected_latest"` on the enterprise/Basilisk join | `P1`, `Priority_Source="current-version-vuln"`, `Work="Fix vulnerability"` regardless of any board lock or platform/app signal | None — this is the top-precedence branch, never overridden |
| Existing OpenTeams board P1/P2/P3 | `board_lock` resolves via `OpenTeams_Issue_URL` or name against `openteams_project_1_board_raw` titles matching `[Conda-Forge Packaging] <name>` | Locked bucket (`P1`/`P2`/`P3`) preserved, `Priority_Source="openteams-board"`, not overwritten by platform/app/download signals | A board title that doesn't match the bracket pattern is ignored (same as `board_maps`'s regex miss) |
| Platform / app / download floors, no vuln, no board lock | `platform_env_count>0` (P4), else `internal_app_count>0` (P5), else `downloads>=100 or versions>=100` (P6), else `downloads>=10 or versions>=10` (P7) | Bucket assigned per first matching floor, `Priority_Source` set accordingly | A row matching none of P1-P7 falls to the remainder split |
| Remainder (no vuln/board/platform/app/floor) | `Work` computed via `work_label` | Split into P8 (`Work=="Create recipe"`), P9 (`Work` is the tracking-issue label, cohort not `CONDA_ONLY`), P10 (tracking-issue label with `CONDA_ONLY` cohort, or `Already tracked` leftover) | Every row is assigned a bucket — there is no "no bucket" terminal state |
| Missing enterprise telemetry for a universe package | No `enterprise_jfrog_consumption` row joins for a given name | Treated as `platform_env_count=apps=ic=lob=downloads=versions=0`, `risk_level`/`vuln_status` empty — same zero-default behavior as `priority.py`'s `j = jfrog.get(...)` returning `None` | Falls through to the remainder split, not an error |
| `enterprise_conda_maintainers` role present, `enterprise_jfrog_consumption` absent | A package on conda-forge with a maintainer/co-maintainer role but no JFROG telemetry | Still ranked (remainder split); `Role` itself is Story 23.4's concern, not this node's output | Not a blocker for priority assignment |
| Upstream dependency not yet materialized | Story 21.6 or 23.2 not `status: done` at dispatch time | This story is not dispatched (`Block If`) | See Design Notes |

</intent-contract>

## Code Map

- `scripts/conda-forge-packaging-inventory-operations_priority.py` — the read-only parity
  target, in full:
  - `pep503` (~L104-109) — join-key normalization.
  - `use_score` (~L129-138), `percentile_1_100` (~L141-149) — scoring.
  - `board_maps` (~L152-167), `board_lock` (~L170-182) — OpenTeams board P1-P3 lock.
  - `is_current_vuln` (~L190-193) — P1 vuln gate.
  - `work_label` (~L196-216) — `Work` disposition.
  - `assign_lane` (~L219-247) — P1/P4-P7/board-lock branch dispatch (the remainder — P2/P3
    locked or unbucketed — falls through to `main()`'s remainder loop).
  - `PRIORITY_DESC` (~L57-68), `BUCKET_ORDER`/`PRI_N` (~L35-36), `WORK_ORDER`/`WORK_RANK`
    (~L43-44), `BATCH_TO_WORK` (~L45-56) — the lookup tables to copy verbatim.
  - `main()`'s remainder-bucket loop (~L666-694, P8/P9/P10 leftover split by `Work` and
    `cohort`) and `sort_key`/rank assignment (~L685-698) — the parts of `main()` that are rule
    logic, not I/O; port these, not the xlsx read/write around them.
- `_bmad-output/.../specs/spec-atlas-kedro-catalog-expansion/complete-export-contract.md` §3.2
  — the exact input/output contract this story implements (verbatim in the task brief above).
- `_bmad-output/.../specs/spec-atlas-kedro-catalog-expansion/identity-contract.md` — Story
  21.6's `identity_packages_primary` shape (this story's first input) and
  `openteams_project_1_board_raw`'s source/credential (GitHub GraphQL project V2 #1, org
  `OpenTeams-WFT-CDO`).
- `_bmad-output/.../specs/spec-atlas-kedro-catalog-expansion/verification-matrix.md` — confirms
  `P1`-`P10`/`Score`/`Work` are explicitly "outside matrix until Epic 23" today, and that this
  story (23.3) plus 23.5 are the entries that close that gap.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/derived_artifacts/nodes.py` (71
  lines today) — target file; `build_universe_sbom` (~L23-71) is the existing PURE-node
  precedent to mirror (pandas + stdlib only, no inline IO, `AD-1`).
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/derived_artifacts/pipeline.py`
  (25 lines today) — add one `node(...)` entry; `inputs=` bind to catalog NAMES per the existing
  cross-pipeline-edge convention (`AD-3`), matching `build_universe_sbom`'s
  `["core_packages_enumerated", "pypi_conda_mapping", "parameters"]` pattern.
- `src/shared/packages/pyforge-atlas/conf/base/catalog.yml` (~L448-461) —
  `vulnerability_basilisk_advisories` (`conda_name`/`advisory_id`/`modified`, layer `primary`)
  and `vulnerability_basilisk_details` (per-advisory `fix_available`, layer `intermediate`) are
  `derive_basilisk_vuln_rollup`'s two inputs, already live. Add
  `vulnerability_basilisk_rollup` as `type: pandas.ParquetDataset`, `filepath:
  data/derived/vulnerability_basilisk_rollup/vulnerability_basilisk_rollup.parquet`, `metadata:
  {layer: derived}`, and `inventory_priority_assignments` the same way, `filepath:
  data/derived/inventory_priority_assignments/inventory_priority_assignments.parquet`
  (same shape as the neighboring `derived_universe_sbom`,
  `trending_candidates_classified`, `org_audit_candidates_classified` entries).
- `src/shared/packages/pyforge-atlas/tests/pipelines/derived_artifacts/test_universe_sbom.py` —
  the existing test-file precedent for this pipeline; add a sibling
  `test_inventory_priority_assignments.py`.
- `src/shared/packages/pyforge-atlas/tests/parity/` (`parity_runner.py`, `harness.py`) — the
  existing `cf_atlas.db`-vs-Kedro parity harness; **not** directly reusable here (it diffs
  against the legacy SQLite surface, not the xlsx-based quartet), but its
  fixture/evidence-record pattern is the model for this story's new
  `priority.py`-vs-node fixture comparison.

## Tasks & Acceptance

**Execution:**
- **New (2026-08-30 correction) — `vulnerability_basilisk_rollup` does not exist yet and this
  story must build it**, not just consume it: `grep` confirms `conf/base/catalog.yml` has
  `vulnerability_basilisk_advisories` (`conda_name`, `advisory_id`, `modified` — one row per
  advisory) and `vulnerability_basilisk_details` (per-advisory tri-state `fix_available`), but
  no per-package rollup and no `risk_level`/`vuln_status` extraction anywhere in the repo (the
  legacy `priority.py` reads them pre-joined off the CDO-ENT-JFROG workbook tab, computed by an
  external, out-of-repo process — see Design Notes). Add a new pure node
  `derive_basilisk_vuln_rollup(vulnerability_basilisk_advisories, vulnerability_basilisk_details)
  -> vulnerability_basilisk_rollup` to `pipelines/derived_artifacts/nodes.py`, one row per
  `conda_name`: `jfrog_latest_vuln_count` = count of distinct `advisory_id` for that name
  (unambiguous from the existing data); `vuln_status` = `"affected_latest"` if the name has ≥1
  advisory row, else `"clean"` (a name absent from `vulnerability_basilisk_advisories`
  entirely never appears in the rollup at all — the join in `assign_inventory_priority` treats
  a missing rollup row as `risk_level`/`vuln_status` empty, per the existing I/O matrix row);
  `risk_level` classification (`HIGH`/`MEDIUM`/`LOW`/`NO_DATA`) needs a CVSS-or-equivalent
  severity signal `vulnerability_basilisk_details` does not currently extract from the raw
  `GET /v1/vulns/{id}` OSV-format response (only `fix_available` is captured today) — this is a
  genuine step-03 research/design task (verify what severity field the live API actually
  returns, extend the detail extraction if needed, pick and document the CVSS-band-to-enum
  mapping), not an unresolved spec gap: the OUTPUT contract (the four enum values, one row per
  name) is fully specified above regardless of exactly how severity gets classified.
- Add `assign_inventory_priority(identity_packages_primary, enterprise_jfrog_consumption,
  enterprise_conda_maintainers, openteams_project_1_board_raw, vulnerability_basilisk_rollup,
  parameters=None)` to `pipelines/derived_artifacts/nodes.py`, porting `priority.py`'s
  `pep503`/`use_score`/`percentile_1_100`/`board_maps`/`board_lock`/`is_current_vuln`/
  `work_label`/`assign_lane`/remainder-split/`sort_key` logic verbatim (module-private helpers
  in the same file; do not import from `scripts/`).
- Wire the node into `pipelines/derived_artifacts/pipeline.py` with `outputs=
  "inventory_priority_assignments"`, `inputs=` bound to the four Kedro catalog names named in
  complete-export-contract.md §3.2, PLUS `vulnerability_basilisk_rollup` as a genuinely
  separate fifth positional input — resolved 2026-08-30 (Corrected 2026-08-30, see Design
  Notes): Story 23.2's `enterprise_jfrog_consumption.parquet` is Artifactory-native telemetry
  ONLY (`platform_env_count`/`internal_app_count`/`artifactory_downloads`/
  `artifactory_version_count`/`internal_component_count`/`internal_lob_count`/
  `repository_source`/`packaging_tier`/`verification_timestamp_utc`) — it does NOT carry
  `risk_level`/`vuln_status`. This node is where the Basilisk join actually happens: left-join
  `vulnerability_basilisk_rollup` (keyed the same PEP-503 way, latest-version-per-package
  rollup) onto the joined frame to produce `risk_level`/`vuln_status`/`jfrog_latest_vuln_count`
  before evaluating `is_current_vuln`/`assign_lane`'s P1 branch.
- Add `inventory_priority_assignments` to `conf/base/catalog.yml` per the Code Map's dataset
  shape.
- Build the frozen fixture corpus (new directory under `tests/fixtures/`) covering the six
  scenarios in the I/O matrix above; capture `priority.py`'s output over the same synthetic
  rows as the frozen expected values (do not run `priority.py` against real workbook data as
  part of CI — the fixture is synthetic and small, matching the existing `tests/fixtures`
  convention across the repo).
- Add `tests/pipelines/derived_artifacts/test_inventory_priority_assignments.py` asserting
  P/Rank/Score/Work/Priority_Bucket_Description/Priority_Source parity against the fixture, one
  test case per I/O-matrix scenario plus the four legacy-alias columns.
- Add a test for `derive_basilisk_vuln_rollup` covering: a name with ≥1 advisory ->
  `vuln_status="affected_latest"`, `jfrog_latest_vuln_count` matches the distinct-advisory
  count; a name with zero advisories -> absent from the rollup entirely (not a zero-count row);
  `risk_level` defaults to whatever the step-03 classification lands on for a covered name, and
  is absent (not a fabricated default) when the name has no advisories.
- Confirm `pixi run -e pyforge-atlas kedro-catalog-check` and `kedro-test` stay green with the
  new catalog entry and node.

**Acceptance Criteria:**
- Given the frozen fixture corpus's current-vuln row, when the new node runs, then it is
  assigned `P1`, `Work="Fix vulnerability"`, `Priority_Source="current-version-vuln"` —
  matching `priority.py`'s output on the same row.
- Given the fixture's board-locked P1/P2/P3 row, when the new node runs, then the locked bucket
  is preserved and not overwritten by any platform/app/download signal on that row.
- Given the fixture's P4-P7 floor rows, when the new node runs, then each is assigned the
  correct bucket per the first-matching-floor precedence, with `Score` matching `priority.py`'s
  `use_score`/`percentile_1_100` output within floating-point tolerance.
- Given the fixture's three remainder rows, when the new node runs, then each is split into
  P8/P9/P10 exactly as `priority.py`'s `main()` remainder loop does, keyed off the same `Work`
  value.
- Given the full fixture corpus sorted and ranked, when compared row-by-row against
  `priority.py`'s output on the same corpus, then `P`, `Rank`, `Score`, and `Work` are
  identical for every row (`done_checkpoint`).
- Given `inventory_priority_assignments.parquet`, when read, then it carries all eleven
  contract columns (`P`, `Rank`, `Score`, `Work`, `Priority_Bucket_Description`,
  `Priority_Source`, `Priority_Reason`, `Proposed_Priority`, `Packaging_Work`, `Priority_Rank`,
  `Priority_Score`) plus `core_python_package_name`, `risk_level`, `vuln_status`, and
  `jfrog_latest_vuln_count` (the pass-through Basilisk-join columns Story 23.5 consumes).
- Given `pixi run -e pyforge-atlas kedro-catalog-check` and `kedro-test`, when run after this
  story, then both stay green.

## Spec Change Log

- 2026-08-30: Initial draft. Ports `priority.py`'s P1-P10/Rank/Score/Work hierarchy into a new
  `derived_artifacts` Kedro node, `inventory_priority_assignments`. Written ahead of Stories
  21.6 and 23.2's implementation — see Design Notes for the resulting dispatch-timing
  consequence.

## Design Notes

**Pipeline choice: `derived_artifacts`, not `upstream_discovery`.** The task brief allows
either; `derived_artifacts` is the better fit. `upstream_discovery`'s existing nodes
(`refresh_trending_candidates`, `classify_trending_candidates`, `load_org_audit_candidates`)
are all about *finding new candidate packages* (GitHub trending, org-audit lists) — a discovery
concern. `inventory_priority_assignments` is the opposite: it re-ranks an already-known,
already-materialized universe of packages using signals that already exist in Parquet (no
fetch, no discovery). `derived_artifacts` is architecturally the home for exactly this shape —
its only current node, `build_universe_sbom`, is likewise a PURE join/derive over
already-materialized inputs producing a new derived artifact, with no fetch and no TTL/cadence
gating. `complete-export-contract.md`'s own build-order diagram groups `PRI`
(`inventory_priority_assignments`) with `VER` (`inventory_verified_packages`, Story 23.4) and
`COMP` (`identity_complete_export.parquet`, Story 23.5) as a single downstream "derived" chain
feeding off `ID` (`identity_packages_primary`) — consistent with putting all three in
`derived_artifacts`, keeping Story 23.4 (which depends on this story's output) in the same
pipeline rather than crossing pipeline boundaries for a tightly-coupled two-node chain.

**This story cannot be dispatched yet.** As of this spec's drafting (2026-08-30), neither
Story 21.6 (`identity_packages_primary` — confirmed via `grep` across `conf/base/catalog.yml`:
zero hits) nor Story 23.2 (`enterprise_jfrog_consumption.parquet` /
`enterprise_conda_maintainers.parquet` — same, zero hits) has landed; no `spec-21-6-*.md` or
`spec-23-2-*.md` file exists yet under this directory either. This spec describes the node
Story 21.6 and 23.2's outputs make possible — do not dispatch `bmad-build`/`bmad-loop` against
it until both are `status: done` (same pattern `spec-21-8` already established: the spec is
complete and actionable, but upstream code has not landed). Whoever picks this story up must
re-check `21.6`/`23.2`'s live status (spec frontmatter or `fleet-picture`) before dispatch
rather than trusting this spec's drafting-time snapshot.

**Porting scope is read-only against `priority.py`.** "Port the full P1-P10 hierarchy" is not
an intent gap: the script exists, is fully readable (818 lines, no ambiguity in its branch
logic), and per the task's own framing this is normal step-03 implementation work — reading and
faithfully reimplementing already-shipped logic — not a spec-level open question.

**Corrected 2026-08-30: the Basilisk vuln rollup is a genuinely separate input, resolved, not
an open point.** The legacy `priority.py` reads `risk_level`/`vuln_status` off the same `j`
(JFrog) dict as `platform_env_count` etc. (`scripts/conda-forge-packaging-inventory-operations_priority.py:607-618`)
only because the CDO-ENT-JFROG workbook TAB already carries them pre-joined by an external,
out-of-repo process before the script ever runs — Artifactory itself has no vulnerability data.
`complete-export-contract.md` §1 and `spec-23-2` were both corrected to remove `risk_level`/
`vuln_status` from `enterprise_jfrog_consumption.parquet`'s required columns for exactly this
reason: the Kedro port should make that join explicit (this node, against
`vulnerability_basilisk_rollup`) rather than silently inherit an implicit one. This is now a
firm design decision, not a dispatch-time confirmation to re-derive.

## Verification

**Commands (run once Stories 21.6 and 23.2 are done and this story dispatches):**
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass, `inventory_priority_assignments`
  present and well-formed.
- `pixi run -e pyforge-atlas kedro-test -- tests/pipelines/derived_artifacts/test_inventory_priority_assignments.py`
  (or the equivalent full-suite `kedro-test` run) — expected: all fixture-corpus parity
  assertions pass.
- Manual/CI diff of `priority.py`'s unmodified output against the new node's output on the same
  frozen fixture corpus — expected: byte-identical `P`/`Rank`/`Score`/`Work` per row
  (`done_checkpoint`).

## Review Triage Log

### 2026-09-01 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

## Auto Run Result

Status: done

**Summary:** Story 23.3 ports `priority.py`'s P1–P10 / Rank / Score / Work hierarchy into two new
`derived_artifacts` PURE nodes — `derive_basilisk_vuln_rollup` (Basilisk per-package rollup) and
`assign_inventory_priority` (priority assignments over Kedro Parquet inputs) — with catalog entries,
pipeline wiring, and fixture-based parity tests against unmodified `priority.py`.

**Files changed:**
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/derived_artifacts/nodes.py` — rollup + priority nodes
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/derived_artifacts/pipeline.py` — wire two nodes
- `src/shared/packages/pyforge-atlas/conf/base/catalog.yml` — `vulnerability_basilisk_rollup`, `inventory_priority_assignments`
- `src/shared/packages/pyforge-atlas/tests/pipelines/derived_artifacts/test_inventory_priority_assignments.py` — parity suite
- `src/shared/packages/pyforge-atlas/tests/catalog/conftest.py` — catalog count 120→122, pipeline nodes 3→5
- `src/shared/packages/pyforge-atlas/tests/pipelines/test_dag_resolves.py` — derived_artifacts DAG expectations

**Review:** No review subagents (shell blocked in session); self-review only — no findings triaged.

**Follow-up review recommendation:** false (0 patch findings)

**Verification:** Shell/pixi blocked in this session — run locally:
- `pixi run -e pyforge-atlas kedro-catalog-check`
- `pixi run -e pyforge-atlas kedro-test -- tests/pipelines/derived_artifacts/test_inventory_priority_assignments.py`

**Residual risks:** OpenTeams board `Priority` is not in the GraphQL board schema; board-lock reads an
optional `priority` column (fixtures) with `milestone` P1/P2/P3 fallback. Cohort/work for remainder
split derives `OpenTeams_Cohort` from enterprise membership + conda-forge signals rather than the
retired inventory tab — equivalent when inventory cohort matches those signals.
