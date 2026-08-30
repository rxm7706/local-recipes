---
title: 'identity_complete_export.parquet (canonical single export) (Story 23.5, Epic 23)'
type: 'feature'
created: '2026-08-30'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/complete-export-contract.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/identity-contract.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/verification-matrix.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/catalog-sources.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-23-3-priority-rules-in-kedro.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-23-4-deliverable-a-packaging-candidate-status.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-21-6-upstream-discovery-identity-join-and-export-parquet.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** The ~63 columns that today's pinned gist row catalog and the (post-Epic-21)
identity export collectively need are scattered across four surfaces that do not yet share one
Parquet: identity join columns will live in `identity_packages_primary` (Story 21.6, Phase D),
ranking columns (`P`/`Rank`/`Score`/`Work`) will live in `inventory_priority_assignments`
(Story 23.3, a Kedro port of `conda-forge-packaging-inventory-operations_priority.py`),
verification BOOLs + `Packaging_Candidate_Status` will live in `inventory_verified_packages.parquet`
(Story 23.4, deliverable A), and enterprise JFROG telemetry will live in
`enterprise_jfrog_consumption.parquet` + `enterprise_conda_maintainers.parquet` (Story 23.2).
Today, and through Epic 21/22.1, the ONLY place these four surfaces are actually merged into one
row-per-package view is at gist-publish time inside
`conda-forge-packaging-inventory-operations_openteams_identity.py` (`GIST_SCHEMA`, 35 columns) —
a `scripts/`-owned merge pass, exactly what CAP-8 exists to retire. Every additional consumer
(Vizro Epic 22 pages, the BSL gist actuator of Story 23.6, `--live-catalog` verification) would
otherwise have to re-implement that same four-way join itself.

**Approach:** One new PURE join node (`DataFrame × N → DataFrame`, AD-2) that consumes the four
already-materialized upstream Parquet outputs of Stories 21.6/23.2/23.3/23.4 plus the existing
and Story-23.1-extended cross-channel BOOL source(s), joins them on the PEP-503-normalized
`Core_Python_Package_Name` key, and writes exactly one Parquet:
`identity_complete_export.parquet`. Row grain is unchanged from today's identity tab: one row per
OpenTeams-universe (`CDO-ENT-JFROG` ∪ `CDO-ENT-CONDA`) name, plus board-only
`[Conda-Forge Packaging]` extras. This story adds **no new fetch, no new ranking rule, no new
verification rule** — it is a rename/join/alias pass over Parquet four other stories already
produce; all business logic (association matching, priority hierarchy, `packaging_status`,
enterprise rollups) is owned and ported verbatim by 21.6/23.2/23.3/23.4.

## Boundaries & Constraints

**Always:**
- Row grain = one row per universe `Core_Python_Package_Name` + board-only extras — identical
  semantics to today's `from_assoc` / `from_inventory` / `from_board_only` (see
  `identity-contract.md` § Join semantics; Story 21.6 owns producing this shape in
  `identity_packages_primary`, this story only consumes it).
- Every column named in `complete-export-contract.md` §4 is present with a byte-identical name
  (case, underscores, hyphens exactly as written in that section) — this is the parity gate, not
  a rename-for-Kedro-style pass. See Code Map's full 63-column table for the source of each.
- The node is pure `DataFrame → DataFrame` (AD-2) — no HTTP fetch, no file IO beyond the
  catalog-declared read/write. If an upstream Parquet is absent, degrade to blank/NULL columns
  for that group (never raise, never fabricate rows — mirrors every other AD-13-compliant node in
  this pipeline suite).
- `OpenTeams_Batch` is a literal alias of `Work` (same value, second column name) — not a second
  derivation, per `complete-export-contract.md` §4 "OpenTeams handoff" note `(alias of Work)`.
- `Platforms`/`Apps`/`Downloads`/`Versions`/`Vuln` (the "JFROG gist shorthand" group) and
  `platform_env_count`/`internal_app_count`/`artifactory_downloads`/`artifactory_version_count`/
  `JFROG_vuln_status` (the "Enterprise detail" group) are **both** present — this is an
  intentional alias duplication (short gist-facing names + full enterprise-facing names), not a
  bug to collapse; `complete-export-contract.md` §4 lists both groups explicitly.
- `OpenTeams_Cohort` is DERIVED at join time per `complete-export-contract.md` §1 rule
  (`JFROG_NEW` if JFROG ∧ ¬conda-forge; `JFROG_ON_CF` if JFROG ∧ conda-forge; absent if not in
  JFROG) — never read from a workbook-sourced `OpenTeams_Cohort` value (the Excel workbook is out
  of scope for this closure per §7).
- The `${PYFORGE_ATLAS_DATA_ROOT}/derived/identity_complete_export.parquet` path named in
  `complete-export-contract.md`'s "North star export" section is the operator-facing shorthand;
  the `catalog.yml` entry itself follows this codebase's existing `derived/`-layer convention —
  `data/derived/<dataset_name>/<dataset_name>.parquet` — the same shape as every other `derived`
  entry (`artifactory_downloads_joined`, `pypi_intelligence_scored`, `derived_universe_sbom`; see
  Code Map). No other `derived` entry in `catalog.yml` uses a flat, un-nested filepath; this story
  does not introduce the first one (catalog.yml's own header: "nodes never choose physical
  layout").
- Parity gate: byte-identical column NAMES to today's `GIST_SCHEMA` (35 columns,
  `conda-forge-packaging-inventory-operations_openteams_identity.py` L84-121) plus the 28
  additional columns `complete-export-contract.md` §4 adds beyond `GIST_SCHEMA`, verified against
  a fixed fixture corpus.

**Block If:** Stories 23.3 and 23.4 are not both `status: done` (this spec's own `depends_on`).
This spec may be authored and reviewed ahead of that — see Design Notes, mirroring
`spec-21-8-end-to-end-verification-gate.md`'s precedent for a closing-join story written before
its inputs exist.

**Never:**
- Do not add a second `Packaging_Candidate_Status` / `PyPI_Verified` / `CondaForge_Verified`
  derivation — read `inventory_verified_packages.parquet`'s columns verbatim (Story 23.4 already
  ports `metrics.py::packaging_status`).
- Do not add a second priority/ranking derivation — read `inventory_priority_assignments`'s
  columns verbatim (Story 23.3 already ports `priority.py`'s hierarchy). Do not re-derive `P`,
  `Rank`, `Score`, or `Work` here.
- Do not fetch anything over the network — every input to this node is an already-materialized
  Parquet from an upstream story; if one is missing, degrade, do not fetch it yourself.
- Do not touch `openteams_identity_dashboards.py`, gist-markdown generation, or the `gh gist edit`
  actuator — that is Story 23.6's territory exclusively.
- Do not read `packaging_tier` for any derived column here (mirrors Story 23.3's own non-goal,
  restated because this story's enterprise join re-surfaces that column).
- Do not modify `identity_packages_primary`, `inventory_priority_assignments`,
  `enterprise_jfrog_consumption`, `enterprise_conda_maintainers`, or `inventory_verified_packages`
  themselves — this story is a pure downstream consumer of all five.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|----------------|----------------------------|-----------------|
| All five upstream Parquet present | `identity_packages_primary`, `inventory_priority_assignments`, `enterprise_jfrog_consumption`, `enterprise_conda_maintainers`, `inventory_verified_packages` all materialized | One row per universe name; all 63 columns populated per the §4 groups | — |
| Enterprise Parquet absent/empty (JFROG creds not attended) | `enterprise_jfrog_consumption.parquet` missing or zero-row | JFROG/enterprise-group columns (`Platforms`…`internal_lob_count`, `JFROG_vuln_status`) blank/NULL for every row; identity is the join anchor so no row is dropped | Never raise; log a shape note, degrade to blank columns (AD-13 spirit) |
| A universe name has no priority-assignment row | `inventory_priority_assignments` missing a name present in `identity_packages_primary` (should not happen given 23.3's full-coverage contract, but defended against) | Ranking columns (`P`/`Rank`/`Score`/`Work`/`Priority_Bucket_Description`/`Priority_Source`/`Priority_Reason`) blank for that row; row is not dropped | Never raise; row survives with blank ranking |
| Board-only extra (OpenTeams board issue, not in either universe) | `identity_packages_primary` board-only row (`identity_source=openteams-board`) | Row present in export; enterprise + verification-BOOL columns blank (never applicable to board-only, matches today's `from_board_only`) | Matches today's semantics exactly |
| Tier 3 cross-channel source not yet materialized | e.g. `discovery_debian_packages_raw` absent (Story 23.1 not yet run) | `in_debian` (and siblings) blank/`False`, not a join failure | Never raise |
| `Verification_Timestamp_UTC` conflicts between upstream sources | `identity_packages_primary` and `inventory_priority_assignments` each carry their own snapshot timestamp | This node re-stamps `Verification_Timestamp_UTC` once, at export-build time — never propagates a stale upstream timestamp | — |

</intent-contract>

## Code Map

**Upstream inputs (produced by other stories — this story is a pure consumer):**
- `identity_packages_primary` (Story 21.6, `upstream_discovery` pipeline per
  `identity-contract.md` Phase D) — 18 identity-core columns (group 3 below) + row-grain anchor.
- `inventory_priority_assignments` (Story 23.3, confirmed `derived_artifacts` pipeline per
  `spec-23-3-priority-rules-in-kedro.md`'s own Design Notes — see this story's Design Notes) —
  `P`, `Rank`, `Score`, `Work`, `Priority_Bucket_Description`, `Priority_Source`,
  `Priority_Reason`, plus the legacy-alias columns
  (`Proposed_Priority`/`Packaging_Work`/`Priority_Rank`/`Priority_Score`, not carried into this
  export per §4's group list). Note: Story 23.3's own spec flags the Basilisk-vuln-rollup input
  (feeding `JFROG_latest_vuln_count`) as possibly a separate catalog entry rather than folded into
  `enterprise_jfrog_consumption` — confirm at dispatch time which shape landed (see this story's
  row 33 below).
- `enterprise_jfrog_consumption.parquet` (Story 23.2, extends the existing `artifactory_downloads`
  pipeline — see `conf/base/catalog.yml` L930-940's `artifactory_downloads_joined` for the
  existing precedent this new entry sits beside) — `platform_env_count`, `internal_app_count`,
  `artifactory_downloads`, `artifactory_version_count`, `risk_level`, `vuln_status`,
  `internal_component_count`, `internal_lob_count`, `jfrog_latest_vuln_count` (Basilisk overlay,
  `complete-export-contract.md` §1).
- `enterprise_conda_maintainers.parquet` (Story 23.2, Tier 2 "CDO-ENT-CONDA maintainer universe")
  — `role`, `repository_source` (`CDO-ENT-CONDA`).
- `inventory_verified_packages.parquet` (Story 23.4, deliverable A, 14 columns per
  `complete-export-contract.md` §2) — `Repository_Source`, `Role`, `PyPI_Verified`,
  `CondaForge_Verified`, `Packaging_Candidate_Status` sourced from here verbatim.
- Cross-channel BOOL source(s) — existing `pypi_cross_channel_flags` (Tier 0/1, Epic 21) extended
  by Story 23.1 with the 5 Tier 3 sources (`discovery_homebrew_packages_raw`,
  `discovery_nixpkgs_packages_raw`, `discovery_spack_packages_raw`, `discovery_debian_packages_raw`,
  `discovery_fedora_packages_raw`). **Open at drafting time:** `catalog-sources.md`'s Tier 3 row
  says the new BOOLs land "on verification export", which could mean Story 23.1 appends them
  directly onto `inventory_verified_packages.parquet` rather than onto `pypi_cross_channel_flags`.
  This story's join must be written against whichever shape 23.1/23.4 actually land — the fixed
  contract is the 15 `in_*` column NAMES in §4, not a specific upstream table; confirm at dispatch
  time (see Design Notes; do not assume this spec's drafting-time guess).

**Legacy parity target (read-only reference, not modified):**
- `scripts/conda-forge-packaging-inventory-operations_openteams_identity.py` — `GIST_SCHEMA`
  (L84-120, 35 `(name, type, required, meaning)` tuples) and `COLUMNS` (L47-66, the 18-column
  identity-tab-only list) — the literal parity target for column NAMING. `GIST_COLUMNS` (L121) is
  the flattened name list this story's parity test diffs against.
- `scripts/conda-forge-packaging-inventory-operations_priority.py` — `PRIORITY_DESC` (L57),
  `assign_lane` (L219-247), `work_label` (L196-216) — read for context on `OpenTeams_Cohort` /
  `OpenTeams_Coverage` semantics this story must preserve at join time (see Design Notes;
  `OpenTeams_Coverage` in particular has no landed Kedro producer yet).
- `scripts/conda-forge-packaging-inventory-operations_metrics.py` — `packaging_status` (L607) —
  the function Story 23.4 ports; this story only consumes its output column
  (`Packaging_Candidate_Status`), never re-implements it.

**This story's own surface:**
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/derived_artifacts/nodes.py` —
  add `build_identity_complete_export(identity_packages_primary, inventory_priority_assignments,
  enterprise_jfrog_consumption, enterprise_conda_maintainers, inventory_verified_packages,
  cross_channel_flags, parameters) -> pd.DataFrame`, mirroring the existing
  `build_universe_sbom` (L23) precedent — the one other node in this pipeline that joins outputs
  from multiple upstream pipelines by catalog dataset name (AD-3 cross-pipeline edges).
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/derived_artifacts/pipeline.py` —
  add one `node(func=build_identity_complete_export, inputs=[...], outputs="identity_complete_export",
  name="build_identity_complete_export")` entry alongside the existing `build_universe_sbom` node.
- `conf/base/catalog.yml` — new entry near L846 (`derived_universe_sbom`) or L939
  (`artifactory_downloads_joined`):
  ```yaml
  identity_complete_export:
    type: pandas.ParquetDataset
    filepath: data/derived/identity_complete_export/identity_complete_export.parquet
    metadata:
      layer: derived
  ```
- `src/shared/packages/pyforge-atlas/tests/catalog/conftest.py` — `PREFIX_TO_PIPELINE` (L66-79)
  has NO `identity` / `inventory` / `enterprise` domain prefix registered as of this spec's
  drafting (confirmed by reading the file directly). This dataset's name (`identity_complete_export`)
  needs its domain prefix (`identity`) mapped to whichever pipeline houses the node
  (`derived_artifacts` per this story's recommendation) — coordinate with Stories 21.6 (which may
  already register `identity` → `upstream_discovery` for `identity_packages_primary`) and 23.2-23.4
  (`enterprise`/`inventory` prefixes) so the convention stays 1:1 and is not double-registered. If
  Story 21.6 has already claimed `identity` → `upstream_discovery`, this story's node either moves
  to `upstream_discovery` instead of `derived_artifacts`, or the dataset is exempted with a
  documented reason (see Design Notes) — resolve at dispatch time against the then-current
  `conftest.py`, not this spec's drafting-time snapshot.
- `EXPECTED_PIPELINE_COUNTS` (same file, L82-93) — increment whichever pipeline's count this
  story's dataset lands under, by 1.
- `tests/fixtures/inventory_identity/` — does **not** exist yet as of this spec's drafting
  (confirmed via `find`); `identity-contract.md` names it as the parity fixture corpus location
  and attributes its associator-hit / inventory-derived / board-only fixture rows to Story 21.6.
  This story EXTENDS that fixture set (once 21.6 creates it) with priority (`P`/`Rank`/`Score`/
  `Work`), enterprise (JFROG columns), verification (`PyPI_Verified`/`CondaForge_Verified`/
  `Packaging_Candidate_Status`), and cross-channel (`in_*`) fixture rows needed for the
  complete-export parity gate — it does not replace 21.6's existing rows.
- New test file: `src/shared/packages/pyforge-atlas/tests/pipelines/derived_artifacts/
  test_identity_complete_export.py` (sibling of the existing `test_universe_sbom.py` in the same
  dir) — column-name parity vs `GIST_COLUMNS` + the 28 additional §4 columns; edge-case coverage
  per the I/O matrix above (absent enterprise, missing priority row, board-only, absent Tier 3).

## Tasks & Acceptance

**Execution:**
- Confirm Stories 23.3 and 23.4 are `status: done` before dispatch (see Design Notes — this spec
  is written ahead of them, mirroring `spec-21-8`'s precedent).
- Resolve the `PREFIX_TO_PIPELINE` / pipeline-placement question (`derived_artifacts` vs
  `upstream_discovery`) against the then-current `conftest.py` and Story 21.6's landed shape;
  document the resolution in this story's own Design Notes / Auto Run Result once decided.
- Add `build_identity_complete_export` to `derived_artifacts/nodes.py` (or the resolved
  alternative pipeline): a pure join on PEP-503-normalized `Core_Python_Package_Name`, anchored on
  `identity_packages_primary` (left join — every identity row survives regardless of
  priority/enterprise/verification coverage), producing all 63 columns from
  `complete-export-contract.md` §4 with byte-identical names. Use the full column table below as
  the literal column list and source mapping.
- Wire the node into `derived_artifacts/pipeline.py` (or the resolved alternative), add the
  `identity_complete_export` catalog entry, and register/verify the domain-prefix mapping.
- `Package` column: alias of `Core_Python_Package_Name` (display name), per `GIST_SCHEMA`'s own
  documented meaning — do not derive it independently.
- `OpenTeams_Batch` column: alias of `Work` (literal copy), per §4's `(alias of Work)` note.
- `OpenTeams_Cohort`: derive per `complete-export-contract.md` §1's rule using
  `enterprise_jfrog_consumption` membership ∧ `CondaForge_Verified` (from
  `inventory_verified_packages`).
- `OpenTeams_Coverage`: no landed Kedro producer exists for this column as of this spec's
  drafting. Propose deriving it at join time as `"Have_Issue"` when `OpenTeams_Issue_URL` is
  non-empty, else blank — this mirrors the *consuming* semantics `priority.py::work_label` (L206)
  already reads from the legacy workbook-sourced value (`coverage == "Have_Issue"` routes to
  `WORK_TRACKED`). Verify this derivation against `priority.py`'s frozen fixture corpus during
  implementation (cross-reference Story 23.3's own parity test) — if the legacy value carries
  additional states beyond `Have_Issue`/blank that the frozen corpus reveals, extend the
  derivation rather than narrowing the column's meaning silently.
- Full column table (source of truth: `complete-export-contract.md` §4's eight groups; every name
  copied verbatim):

  | # | Column | Group | Producer / rule |
  |---|--------|-------|------------------|
  | 1 | `P` | Ranking | `inventory_priority_assignments.P` |
  | 2 | `Rank` | Ranking | `inventory_priority_assignments.Rank` |
  | 3 | `Score` | Ranking | `inventory_priority_assignments.Score` |
  | 4 | `Package` | Ranking | alias of `Core_Python_Package_Name` |
  | 5 | `Work` | Ranking | `inventory_priority_assignments.Work` |
  | 6 | `Platforms` | JFROG shorthand | `enterprise_jfrog_consumption.platform_env_count` |
  | 7 | `Apps` | JFROG shorthand | `enterprise_jfrog_consumption.internal_app_count` |
  | 8 | `Downloads` | JFROG shorthand | `enterprise_jfrog_consumption.artifactory_downloads` |
  | 9 | `Versions` | JFROG shorthand | `enterprise_jfrog_consumption.artifactory_version_count` |
  | 10 | `Vuln` | JFROG shorthand | `enterprise_jfrog_consumption.vuln_status` |
  | 11 | `Core_Python_Package_Name` | Identity core | `identity_packages_primary.Core_Python_Package_Name` (PK) |
  | 12 | `OpenTeams_Title` | Identity core | `identity_packages_primary.OpenTeams_Title` |
  | 13 | `identity_source` | Identity core | `identity_packages_primary.identity_source` |
  | 14 | `associator_key` | Identity core | `identity_packages_primary.associator_key` |
  | 15 | `associator_status` | Identity core | `identity_packages_primary.associator_status` |
  | 16 | `primary_purl` | Identity core | `identity_packages_primary.primary_purl` |
  | 17 | `primary_type` | Identity core | `identity_packages_primary.primary_type` |
  | 18 | `alternative_purls` | Identity core | `identity_packages_primary.alternative_purls` |
  | 19 | `cpes` | Identity core | `identity_packages_primary.cpes` |
  | 20 | `conda_purl` | Identity core | `identity_packages_primary.conda_purl` |
  | 21 | `source_repository_url` | Identity core | `identity_packages_primary.source_repository_url` |
  | 22 | `OpenTeams_Issue_URL` | Identity core | `identity_packages_primary.OpenTeams_Issue_URL` |
  | 23 | `Conda-Forge_FeedStock_URL` | Identity core | `identity_packages_primary.Conda-Forge_FeedStock_URL` |
  | 24 | `Conda-Forge_Metadata_URL` | Identity core | `identity_packages_primary.Conda-Forge_Metadata_URL` |
  | 25 | `Staged_Recipes_PR_URL` | Identity core | `identity_packages_primary.Staged_Recipes_PR_URL` |
  | 26 | `Local_Recipes_URL` | Identity core | `identity_packages_primary.Local_Recipes_URL` |
  | 27 | `Local_Build_Status` | Identity core | `identity_packages_primary.Local_Build_Status` |
  | 28 | `Verification_Timestamp_UTC` | Identity core | re-stamped at this node's own build time |
  | 29 | `Priority_Bucket_Description` | Priority detail | `inventory_priority_assignments.Priority_Bucket_Description` |
  | 30 | `Priority_Source` | Priority detail | `inventory_priority_assignments.Priority_Source` |
  | 31 | `Priority_Reason` | Priority detail | `inventory_priority_assignments.Priority_Reason` |
  | 32 | `JFROG_risk_level` | Enterprise detail | `enterprise_jfrog_consumption.risk_level` |
  | 33 | `JFROG_latest_vuln_count` | Enterprise detail | `enterprise_jfrog_consumption.jfrog_latest_vuln_count` |
  | 34 | `internal_component_count` | Enterprise detail | `enterprise_jfrog_consumption.internal_component_count` |
  | 35 | `internal_lob_count` | Enterprise detail | `enterprise_jfrog_consumption.internal_lob_count` |
  | 36 | `platform_env_count` | Enterprise detail | `enterprise_jfrog_consumption.platform_env_count` (full name, alias of `Platforms`) |
  | 37 | `internal_app_count` | Enterprise detail | `enterprise_jfrog_consumption.internal_app_count` (alias of `Apps`) |
  | 38 | `artifactory_downloads` | Enterprise detail | `enterprise_jfrog_consumption.artifactory_downloads` (alias of `Downloads`) |
  | 39 | `artifactory_version_count` | Enterprise detail | `enterprise_jfrog_consumption.artifactory_version_count` (alias of `Versions`) |
  | 40 | `JFROG_vuln_status` | Enterprise detail | `enterprise_jfrog_consumption.vuln_status` (alias of `Vuln`) |
  | 41 | `OpenTeams_Cohort` | OpenTeams handoff | derived (see rule above) |
  | 42 | `OpenTeams_Batch` | OpenTeams handoff | alias of `Work` |
  | 43 | `OpenTeams_Coverage` | OpenTeams handoff | derived (see rule above; open item) |
  | 44 | `Repository_Source` | OpenTeams handoff | `inventory_verified_packages.Repository_Source` |
  | 45 | `Role` | OpenTeams handoff | `inventory_verified_packages.Role` |
  | 46 | `PyPI_Verified` | Verification BOOLs | `inventory_verified_packages.PyPI_Verified` |
  | 47 | `CondaForge_Verified` | Verification BOOLs | `inventory_verified_packages.CondaForge_Verified` |
  | 48 | `Packaging_Candidate_Status` | Verification BOOLs | `inventory_verified_packages.Packaging_Candidate_Status` |
  | 49 | `in_basilisk` | Cross-channel | cross-channel flags source (Tier 1) |
  | 50 | `in_aoss_free` | Cross-channel | cross-channel flags source (Tier 1) |
  | 51 | `in_aoss_premium` | Cross-channel | cross-channel flags source (Tier 1) |
  | 52 | `in_anaconda_main` | Cross-channel | cross-channel flags source (Tier 1) |
  | 53 | `in_anaconda_dist` | Cross-channel | cross-channel flags source (Tier 1) |
  | 54 | `in_selfexplainml` | Cross-channel | cross-channel flags source (Tier 1) |
  | 55 | `in_bioconda` | Cross-channel | cross-channel flags source (Tier 1, hardened) |
  | 56 | `in_pytorch` | Cross-channel | cross-channel flags source (Tier 1, hardened) |
  | 57 | `in_nvidia` | Cross-channel | cross-channel flags source (Tier 1, hardened) |
  | 58 | `in_robostack` | Cross-channel | cross-channel flags source (Tier 1, hardened) |
  | 59 | `in_homebrew` | Cross-channel | Tier 3 (Story 23.1) |
  | 60 | `in_nixpkgs` | Cross-channel | Tier 3 (Story 23.1) |
  | 61 | `in_spack` | Cross-channel | Tier 3 (Story 23.1) |
  | 62 | `in_debian` | Cross-channel | Tier 3 (Story 23.1) |
  | 63 | `in_fedora` | Cross-channel | Tier 3 (Story 23.1) |

- New test `test_identity_complete_export.py`: parity test asserting the output column set
  (order-independent) equals the 63-name set above, byte-identical strings; plus the 35-name
  `GIST_COLUMNS` subset is a strict subset (parity with the legacy gist schema); plus the 5
  I/O-matrix edge cases (absent enterprise, missing priority row, board-only, absent Tier 3,
  re-stamped timestamp).
- Extend `tests/fixtures/inventory_identity/` with the priority/enterprise/verification/
  cross-channel rows this story's node needs (once Story 21.6 has created the directory's base
  associator/inventory-derived/board-only rows).
- Document the `identity_complete_export.parquet` path in the operator env block
  (`src/shared/packages/pyforge-atlas/README.md` § "Operator env block", extended most recently by
  Story 21.8) — one row noting where the complete export lands under `PYFORGE_ATLAS_DATA_ROOT`.

**Acceptance Criteria:**
- Given `identity_packages_primary`, `inventory_priority_assignments`,
  `enterprise_jfrog_consumption`, `enterprise_conda_maintainers`, and `inventory_verified_packages`
  all materialized, when the bootstrap chain runs, then `identity_complete_export.parquet` exists
  with exactly the 63 columns in the table above, byte-identical names.
- Given the 35 `GIST_SCHEMA` column names from
  `conda-forge-packaging-inventory-operations_openteams_identity.py`, when diffed against
  `identity_complete_export.parquet`'s columns, then every `GIST_SCHEMA` name is present
  unchanged (parity gate).
- Given `enterprise_jfrog_consumption.parquet` absent or empty, when the export node runs, then
  every row still appears (anchored on identity) with enterprise-group columns blank, and the
  node does not raise.
- Given a board-only row from `identity_packages_primary`, when exported, then it appears with
  enterprise + verification-BOOL columns blank, matching today's `from_board_only` semantics.
- Given the fixed `tests/fixtures/inventory_identity/` corpus (extended by this story), when the
  new parity test runs, then column names, types, and representative row values match the frozen
  corpus.
- Given this story's README documentation task, when read by an operator, then the operator env
  block documents where `identity_complete_export.parquet` lands under
  `PYFORGE_ATLAS_DATA_ROOT`.

## Spec Change Log

- 2026-08-30: Initial draft. Written ahead of Stories 23.3 and 23.4 (`depends_on`), per the
  `spec-21-8-end-to-end-verification-gate.md` precedent for a closing-join story specced before
  its inputs exist — see Design Notes.
- 2026-08-30 (same-day reconciliation pass): `spec-23-3-priority-rules-in-kedro.md` and
  `spec-23-4-deliverable-a-packaging-candidate-status.md` landed concurrently with this spec's
  first draft (both `status: ready-for-dev`). Reconciled against their now-settled dataset shapes:
  confirmed `derived_artifacts` pipeline placement (previously hedged as open in this spec's first
  draft — now corroborated by two independent sibling stories reaching the same conclusion for the
  same reasons); confirmed `inventory_priority_assignments`'s 11-column shape and
  `inventory_verified_packages`'s 14-column deliverable-A shape match this spec's own source
  table; flagged the shared (not story-specific) `PREFIX_TO_PIPELINE` domain-prefix gap and the
  `identity` prefix's two-pipeline split (`upstream_discovery` for Story 21.6's join,
  `derived_artifacts` for this story's export) as an explicit open item for dispatch-time review.
  No change to this story's own column table, scope, or Acceptance Criteria was required — the
  reconciliation strengthened confidence in decisions already made, it did not overturn any.
  Self-review against a READY-FOR-DEVELOPMENT bar (Intent/Boundaries/I-O-matrix completeness,
  Code Map groundedness, verifiable Tasks & Acceptance, honest Design Notes) passed; `status` set
  to `ready-for-dev`.

## Design Notes

**This story cannot be dispatched yet.** As of this spec's drafting (2026-08-30), Epic 23 has no
`status: done` stories (only Epic 21's 21.1 and 21.2 are done repo-wide). Stories 23.3
(`spec-23-3-priority-rules-in-kedro.md`) and 23.4
(`spec-23-4-deliverable-a-packaging-candidate-status.md`) now exist as complete, reviewed specs
(`status: ready-for-dev`, written concurrently with this one) — this is a significant improvement
over drafting this story in a vacuum, since their Code Maps now pin down
`inventory_priority_assignments`'s exact 11 columns and `inventory_verified_packages`'s exact
14-column deliverable-A shape used throughout this spec's own column table. Neither is yet
`status: done`, though — both are themselves blocked on Stories 21.6/23.2 per their own Design
Notes. Confirmed by grep that none of `inventory_priority_assignments`,
`enterprise_jfrog_consumption`, `inventory_verified_packages`, or `identity_packages_primary`
exist anywhere in `catalog.yml` or the pyforge-atlas source tree today — only the SPECS exist, not
the code. Do not dispatch `bmad-build`/`bmad-loop` against this spec until Stories 23.3 and 23.4
(`depends_on`) are both `status: done` — re-verify their live status at dispatch time, not against
this spec's drafting-time snapshot, exactly as `spec-21-8`'s Design Notes instructs for its own
analogous hard dependency.

**Pipeline placement: `derived_artifacts`, now confirmed by sibling stories, not just this spec's
own guess.** `spec-23-3-priority-rules-in-kedro.md` and
`spec-23-4-deliverable-a-packaging-candidate-status.md` (both now exist, `status: ready-for-dev`,
written concurrently with this spec) independently settled on `derived_artifacts` for
`inventory_priority_assignments` and `inventory_verified_packages`/`inventory_aoss_free_queue`
respectively, with the same reasoning this spec independently arrived at: a PURE join/derive over
already-materialized Parquet, no fetch, no discovery concern, and `complete-export-contract.md`'s
own build-order diagram groups `PRI`/`VER`/`COMP` as one downstream derived chain. This story's
`build_identity_complete_export` therefore lands in the SAME file
(`pipelines/derived_artifacts/nodes.py`), alongside 23.3's `assign_inventory_priority` and 23.4's
`build_inventory_verified_packages`/`build_inventory_aoss_free_queue` — no remaining ambiguity on
pipeline choice.

**The `PREFIX_TO_PIPELINE` domain-prefix gap is real but shared, not unique to this story.**
`tests/catalog/conftest.py`'s `PREFIX_TO_PIPELINE` dict (L66-79, confirmed by direct read) still
has no `identity`, `inventory`, or `enterprise` domain prefix registered as of this drafting, and
neither `spec-23-3` nor `spec-23-4`'s own Code Map/Design Notes address registering `inventory` →
`derived_artifacts` for their own new dataset names either — this is an unaddressed gap across all
of 23.3/23.4/23.5 alike, not something this story introduced or must solve alone. This story
registers `identity` → `derived_artifacts` for `identity_complete_export` as part of its own
`EXPECTED_PIPELINE_COUNTS` bump; whoever implements 23.3/23.4/23.5 (likely in dependency order)
should register `inventory` and `identity` together the first time either is touched, to avoid a
double-edit. Story 21.6's `identity_packages_primary`/`identity_export_parquet` live in
`upstream_discovery` (confirmed: `spec-21-6-upstream-discovery-identity-join-and-export-parquet.md`
adds its nodes to `pipelines/upstream_discovery/pipeline.py`) — meaning the `identity` prefix maps
to TWO different pipelines once this story lands (`upstream_discovery` for the join,
`derived_artifacts` for the complete export). This is a genuine, documented exception to the
stated 1:1 domain-prefix rule; flag it for review at dispatch time rather than silently working
around it — the simplest resolution is a one-line comment in `conftest.py` next to the `identity`
entries noting the two-pipeline split, or renaming this story's dataset to a `derived_`-prefixed
alias while keeping `identity_complete_export.parquet` as the physical filename (the contract's
own naming, preserved either way).

**Why `status: ready-for-dev` is appropriate despite the hard dependency.** The spec itself —
Intent, Boundaries, I/O matrix, the full 63-column source table, Tasks & Acceptance — is complete
and actionable; what is missing is not spec clarity but upstream Parquet that has not been
produced yet (a dispatch-ordering constraint, recorded in `Block If` above), the same reasoning
`spec-21-8` used for its own status.

## Verification

**Commands (run once Stories 23.3 and 23.4 are done and this story dispatches):**
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass, new `identity_complete_export`
  entry resolves, domain-prefix convention satisfied.
- `pixi run -e pyforge-atlas kedro-test` — expected: new
  `test_identity_complete_export.py` passes, including the 63-column parity assertion and the 5
  I/O-matrix edge cases.
- `kedro run --pipelines <the pipeline housing this node>` on a data root with the four upstream
  Parquet already materialized — expected: `identity_complete_export.parquet` written, non-empty,
  correct column set.
- Manual diff of `GIST_COLUMNS` (from
  `conda-forge-packaging-inventory-operations_openteams_identity.py`) against
  `identity_complete_export.parquet`'s column list — expected: every `GIST_SCHEMA` name present,
  byte-identical.
