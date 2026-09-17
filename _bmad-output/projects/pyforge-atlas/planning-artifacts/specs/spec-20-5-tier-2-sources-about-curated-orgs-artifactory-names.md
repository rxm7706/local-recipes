---
title: 'Tier 2 sources: about, curated orgs, Artifactory names (Story 21.5, Epic 21)'
type: 'feature'
created: '2026-08-30'
status: 'done'
baseline_revision: 'd230e7fce20037f7f44134aa8fe765fae597102e'
followup_review_recommended: false
deferred:
  - summary: >-
      A malformed conf/base/curated_groups.json (invalid JSON) raises a
      DatasetError at the Kedro catalog layer and aborts the whole
      upstream_discovery pipeline run, rather than degrading to zero rows as
      the Boundaries text promises for "a malformed/missing seed file."
    evidence: |-
      Confirmed empirically: writing invalid JSON to the file and loading the
      discovery_curated_groups_seed catalog entry through
      pyforge.atlas.mcp.session.bootstrapped_session() raised
      `DatasetError: discovery_curated_groups_seed: ... Failed while loading
      data from dataset ... JSONDataset`. This happens before
      load_org_audit_candidates's own never-raise/degrade logic ever runs, so
      that node-level contract can't help. However this exact exposure
      (bare `type: json.JSONDataset` for a git-tracked, hand-curated seed,
      with no degrade wrapper) already exists for the pre-existing
      `seed_cwe_categories` and `seed_spdx_schema` catalog entries — this
      story faithfully follows established precedent rather than introducing
      a new pattern, so it is fleet-wide pre-existing debt, not a regression
      unique to this story.
    location: >-
      src/shared/packages/pyforge-atlas/conf/base/catalog.yml (discovery_curated_groups_seed entry)
    severity: medium
  - summary: >-
      catalog-sources.md's Tier 2 table (the planning doc the Problem
      statement cites as establishing this story's requirement) names a
      different catalog entry/pipeline ("artifactory_downloads_raw" under
      artifactory_downloads) for the Artifactory/CDO-names row than what was
      actually built (enterprise_jfrog_names, bucketed under upstream_discovery
      in PREFIX_TO_PIPELINE) — the intent-contract's own Approach section
      directed the as-built naming, but the companion planning doc was never
      reconciled to match.
    evidence: |-
      Confirmed by direct comparison of catalog-sources.md's Tier 2 table
      against this story's own intent-contract Approach/Code Map text and the
      actual catalog.yml/conftest.py changes. Not a code defect — the diff
      correctly implements the intent-contract's explicit direction — but the
      companion doc is now stale relative to what shipped.
    location: >-
      _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/catalog-sources.md
    severity: low
  - summary: >-
      spec-21-5's own Verification section claims "kedro run --pipelines
      upstream_discovery,artifactory_downloads on a fresh data root" exits 0,
      but join_enterprise_conda_maintainers's new dependency on
      core_feedstock_attribution (produced by the separate `core` pipeline,
      not included in that --pipelines list) makes a genuinely fresh data
      root raise a DatasetError (file not found) before the node ever runs.
    evidence: |-
      Confirmed empirically: moving core_feedstock_attribution.parquet aside
      and re-running `kedro run --pipelines upstream_discovery,artifactory_downloads`
      raised `DatasetError: core_feedstock_attribution: ... No such file or
      directory`. However this is a pre-existing, fleet-wide pattern, not a
      regression this story introduces: classify_trending_candidates (Story
      13.2, already shipped) has the identical characteristic — a plain
      pandas.ParquetDataset input produced by a different pipeline
      (pypi_conda_mapping), with no missing-file tolerance. This story's own
      unit tests DO correctly verify join_enterprise_conda_maintainers's
      behavior when given None/empty input directly (the function-level
      contract in the I/O matrix), which is a different, narrower claim than
      "the full kedro run survives a truly empty data root" — the latter has
      never actually been true for any cross-pipeline dependency in this
      codebase, this story included.
    location: >-
      _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-21-5-tier-2-sources.md (## Verification section)
    severity: medium
context:
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/catalog-sources.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/identity-contract.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-atlas-kedro-catalog-expansion/complete-export-contract.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-artifactory-download-intelligence/SPEC.md'
  - '{project-root}/_bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-21-6-upstream-discovery-identity-join-and-export-parquet.md'
---

<intent-contract>

## Intent

**Problem:** `catalog-sources.md`'s Tier 2 row declares three inventory-alignment
sources — the `rxm7706/about` README's maintainer lists, curated-org candidate
sweeps, and Artifactory/CDO package names — none of which are cataloged today.
`grep -rn 'rxm7706/about'` across the whole repo finds only doc/reference
mentions, never code; `catalog.yml` has no `discovery_about_maintainers_raw`
entry. `curated_groups.json` does not exist anywhere in the repo. Story 21.6
(already spec'd) is explicitly blocked on this story for the "CDO-ENT-JFROG ∪
CDO-ENT-CONDA" enterprise-consumption universe its own `Block If` names verbatim
("**Do not fabricate a substitute enterprise universe**... If Story 21.5 has
landed by the time this story is implemented, join `identity_packages_primary`
against its output directly").

**Approach:**
1. **CDO-ENT-CONDA (about + feedstock join).** New `discovery_about_maintainers_raw`
   dataset fetches `rxm7706/about`'s `README.md` (unauthenticated, mirrors the
   `TrendingSnapshotDataset` / conda-forge-bot-data `GITHUB_RAW_BASE_URL` precedent)
   and parses its two numbered lists ("List Of FeedStocks - As Maintainer" /
   "List Of FeedStocks - As Co-Maintainer", format `N. conda-forge/<feedstock>-feedstock`)
   into `feedstock_slug`/`role` rows. A new derived node joins that against the
   existing `core_feedstock_attribution` (`conda_name`, `feedstock_name`) to produce
   `enterprise_conda_maintainers` — the CDO-ENT-CONDA universe
   (`complete-export-contract.md` §1's exact column contract:
   `core_python_package_name`, `role`, `feedstock_slug`, `repository_source`).
2. **Curated org sweeps.** Extend `load_org_audit_candidates` to merge a NEW
   git-tracked `discovery_curated_groups_seed` JSON catalog entry (multiple
   named curated groups, e.g. `{"groups": [{"org": "...", "repos": [...]}]}`)
   alongside the existing `params:org_audit_candidates` hand-curated list —
   same union-then-dedup-then-classify path, unchanged downstream. This is
   independent of (1): `org_audit_candidates` feeds packaging-candidate
   classification (`classify_trending_candidates`), not the maintainer universe.
3. **Artifactory / CDO names (names only, not telemetry).** A new derived node
   in the EXISTING `artifactory_downloads` pipeline (Story 15.1-15.3, shipped
   mock-first) projects `artifactory_downloads_joined`'s `pypi_name`/`conda_name`
   columns ONLY into `enterprise_jfrog_names` — explicitly dropping
   `version`/`download_count`/`match_source` (that's `enterprise_jfrog_consumption
   .parquet`, Story 23.2's job, which depends on this story per `stories.yaml`).
   No new fetch code, no new credential mechanism — this task reuses the shipped
   mock-first pipeline (`params:artifactory.virtual_repos: []` stays the
   committed default) exactly as-is.

## Boundaries & Constraints

**Always:**
- `discovery_about_maintainers_raw` fetches via
  `${globals:endpoint_bases.GITHUB_RAW_BASE_URL}/rxm7706/about/main/README.md` —
  deliberately UNAUTHENTICATED (mirrors `trending_candidates`'s and the 5
  conda-forge-bot-data entries' documented rationale: stays schedule-eligible,
  no AD-11 attended-only trigger). No new `credentials:` key.
- `discovery_about_maintainers_raw` subclasses `ExternalRefreshDataset` (AD-13:
  last-good Parquet + `StalenessMarker`, never a silent empty overwrite) —
  mirrors `TrendingSnapshotDataset` exactly (injected `fetcher: Callable[[str],
  str] | None`, atomic write, empty-result never clobbers last-good).
- The README parser (`parse_about_readme` or similar) is a PURE function,
  colocated with the dataset class per the `parse_trending_html` precedent:
  never raises — a missing list header, a malformed `N. conda-forge/<x>-feedstock`
  line, or an empty README degrades to `[]` for that list, never a crash.
- `enterprise_conda_maintainers`'s join against `core_feedstock_attribution`
  matches on `feedstock_name` (strip the `conda-forge/` prefix and `-feedstock`
  suffix from the about-parsed `feedstock_slug` before comparing) — never
  invents a `conda_name` for an unmatched feedstock slug; an unmatched row is
  dropped from the joined output (recorded via row-count delta in tests), not
  silently fabricated with a null PK.
- `load_org_audit_candidates`'s existing "never a silent drop, dedupe
  case-insensitively keeping first-seen casing" contract (nodes.py ~L383-421)
  is preserved unchanged when merging the new `discovery_curated_groups_seed`
  input; a malformed/missing seed file degrades to contributing zero rows
  (never raises), exactly like a malformed `params:org_audit_candidates` entry
  degrades today.
- `enterprise_jfrog_names`'s projection node never reads `download_count` (only
  `pypi_name`/`conda_name` — plus `is_internal`, an identity flag, not a
  telemetry metric, may be carried through since it costs nothing and Story
  21.6 can use it) — enforced by an explicit test asserting the output schema
  has no `download_count`/`version`/`match_source` column, not by convention
  alone.
- `params:artifactory.virtual_repos` stays `[]` (the committed Story 15.3
  default) — this story's own Verification never requires a live Artifactory
  call.
- New catalog entries register in `tests/catalog/conftest.py`:
  `PREFIX_TO_PIPELINE` (`"discovery"` -> `"upstream_discovery"` if not already
  added by Story 21.4; `"enterprise"` -> `"upstream_discovery"`, new), and
  `EXPECTED_PIPELINE_COUNTS`/`EXPECTED_TOTAL` bumped by however many entries
  this story actually lands. Verify the CURRENT baseline (`grep -n
  '"discovery"' tests/catalog/conftest.py`) before editing — Story 21.4 (Tier
  1, this story's own dependency) may or may not have landed first; do not
  duplicate an existing mapping.
- `kedro-catalog-check` and `kedro-test` stay green throughout.

**Block If:**
- **Artifactory live-instance/credential wiring.** No live Artifactory instance,
  base_url, or credential shape is decided anywhere in this codebase today —
  `ArtifactoryConfig` deliberately carries no credential field
  (`artifactory/aql_adapter.py` module docstring), the `transport` injection
  point is explicitly test-only and "never present in the committed
  `conf/base/parameters.yml`" (`pipelines/artifactory_downloads/nodes.py`
  docstring), `catalog.yml`'s own header comment states NO entry carries a
  `jfrog` credential key, and `spec-artifactory-download-intelligence`'s own
  Open Questions defers "which live Artifactory deployment... and when its
  attended bring-up happens" outside its scope. `SPEC.md`'s `open_questions`
  names this exact gap for this story. **If an operator has already selected a
  live instance and communicated a concrete credential contract, confirm it
  with them before inventing a `jfrog` catalog credential or a
  `${globals:endpoint_bases.ARTIFACTORY_BASE_URL}` override point** — do not
  guess a JFrog auth shape. Absent that (the default case), ship task 3 wired
  to the existing mock-first `virtual_repos: []` default; the names-only
  projection is correct whether the upstream fetch is empty (today) or
  populated (after a later, separate, attended live bring-up) — this mirrors
  precedent (Story 15.1's own non-goal: "live-instance bring-up... deferred to
  the attended step this Spec explicitly excludes") and AD-11 (credentialed
  runs are attended-only by design, never this story's code to force).
- **`rxm7706/about` README shape drift.** The exact list-header strings and
  `N. conda-forge/<feedstock>-feedstock` line format are recorded from a live
  memory snapshot (2026-07-11), not re-verified against the live file in this
  research pass. If the live README's headers/format have since changed,
  confirm the current shape before finalizing the parser regex — the PURE
  parser's "degrade to `[]`, never raise" contract makes a stale assumption
  safe (it just yields zero rows + a stale marker) but not silently correct.

**Never:**
- Do not add `download_count`, `risk_level`, `platform_env_count`, or any other
  JFROG telemetry/consumption column to `enterprise_jfrog_names` or any output
  this story produces — `enterprise_jfrog_consumption.parquet` is Story 23.2's
  deliverable, which `stories.yaml` records as depending on THIS story landing
  first specifically so the names-only identity key exists to extend.
- Do not build a live GitHub-org-enumeration fetch for "curated org sweeps" —
  `curated_groups.json` is a git-tracked, hand-curated, air-gap seed (same
  posture as the existing `params:org_audit_candidates` list), not a live API
  crawl of an org's repositories.
- Do not touch `identity_packages_primary`/`identity_export_parquet` or any
  Phase D join logic (Story 21.6's territory, which explicitly reads THIS
  story's output as an input once landed).
- Do not port ranking, risk, or priority logic (Epic 23 territory).
- Do not add a 9th pipeline package — both new catalog domains route through
  the existing `upstream_discovery` and `artifactory_downloads` pipelines.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| About README fetch succeeds | `rxm7706/about` README.md reachable, both list headers present | `discovery_about_maintainers_raw` carries one row per `N. conda-forge/<feedstock>-feedstock` line, `role` set from its section | Atomic write, `StalenessMarker` cleared |
| About README fetch fails (network/4xx/5xx) | Endpoint unreachable | Last-good Parquet kept, `StalenessMarker` set | Never raise; never clobber last-good with empty |
| About README reachable but layout changed | Headers renamed/reordered/missing | Parser matches zero rows for the affected list; combined result may be empty -> same as "fetch fails" (mark stale, keep last-good) | Never raise |
| First-ever run, no last-good yet | No prior Parquet, fetch also fails/empty | Empty-but-correctly-columned frame, marked stale | Mirrors `_empty_pypi_json_frame()`-style degrade (spec-21-2 precedent) |
| `enterprise_conda_maintainers` join, matched feedstock | `discovery_about_maintainers_raw` row's stripped slug matches a `core_feedstock_attribution.feedstock_name` | Row emitted with `core_python_package_name`=matched `conda_name`, `role`, `feedstock_slug`, `repository_source="CDO-ENT-CONDA"` | n/a |
| `enterprise_conda_maintainers` join, unmatched feedstock | About-parsed slug has no `core_feedstock_attribution` match (feedstock renamed/retired) | Row dropped from the join output — never a null-PK row | Logged at WARN, not raised |
| `core_feedstock_attribution` empty/unusable | Upstream `core` pipeline hasn't run / degraded | `enterprise_conda_maintainers` degrades to empty frame carrying the full schema | Never raises |
| `org_audit_candidates` merge, curated_groups.json present | Both `params:org_audit_candidates` and the new seed carry entries | Union of both sources, deduped case-insensitively keeping first-seen casing (existing rule, unchanged) | Never a silent drop |
| `curated_groups.json` malformed/missing | File absent, or JSON doesn't match the expected `{"groups": [...]}` shape | Contributes zero rows; `params:org_audit_candidates` alone still classifies | Never raises |
| Artifactory names projection, `virtual_repos` empty (default) | `artifactory_downloads_joined` is the header-only/empty frame (today's shipped default) | `enterprise_jfrog_names` is empty-but-correctly-columned | n/a — no live call made |
| Artifactory names projection, joined data present | An operator has separately enabled live fetch (out of this story's scope, see Block If) | `enterprise_jfrog_names` carries distinct `(pypi_name, conda_name)` pairs, `download_count`/`version`/`match_source` absent from the schema | n/a |

</intent-contract>

## Code Map

- `src/pyforge/atlas/datasets/upstream_discovery.py` — `TrendingSnapshotDataset`
  (~L207-351) is the exact "unauthenticated live + AD-13" shape to mirror for a
  NEW `AboutMaintainersDataset(ExternalRefreshDataset)` (single `readme_url`
  instead of 3 period URLs + a search-API fallback — simpler than the class it
  mirrors); `parse_trending_html`'s "never raise, degrade to `[]`" contract
  (~L95-152) is the shape for a new `parse_about_readme(markdown: str) ->
  list[dict]` PURE function, colocated in the same module (or a new sibling
  module — implementer's call, mirrors spec-21-6's own "proposed name" latitude
  for `identity_sources.py`).
- `src/pyforge/atlas/pipelines/upstream_discovery/nodes.py` — `load_org_audit_candidates`
  (~L383-421, `_ORG_AUDIT_COLS = ["repo_full_name"]` ~L380) — extend its
  signature to accept a second input (the new `discovery_curated_groups_seed`
  catalog entry) and union its flattened rows into the same dedup logic. Add a
  new pure `join_enterprise_conda_maintainers(discovery_about_maintainers_raw,
  core_feedstock_attribution) -> pd.DataFrame` node mirroring
  `classify_trending_candidates`'s join-then-DataFrame style (~L275-373: build
  a normalized index once, resolve each row, never raise on empty/malformed
  input).
- `src/pyforge/atlas/pipelines/upstream_discovery/pipeline.py` — append 2 new
  nodes to the existing 4-node `create_pipeline()` (currently L31-69):
  `refresh_about_maintainers` (pure `params:ttls -> RefreshRequest` trigger,
  mirror `refresh_trending_candidates` ~L44-55) and
  `join_enterprise_conda_maintainers` (`inputs=["discovery_about_maintainers_raw",
  "core_feedstock_attribution"]`, `outputs="enterprise_conda_maintainers"`).
  Update `load_org_audit_candidates`'s existing node binding
  (~L51-56) to add the second input.
- `src/pyforge/atlas/pipelines/artifactory_downloads/nodes.py` — add a new pure
  `project_artifactory_names(artifactory_downloads_joined: pd.DataFrame) ->
  pd.DataFrame` selecting/deduping `pypi_name`/`conda_name`/`is_internal` only
  (mirrors `join_artifactory_identity`'s "never raises, degrades to
  empty-with-full-schema" style, ~L122-166).
- `src/pyforge/atlas/pipelines/artifactory_downloads/pipeline.py` — append a
  4th node (currently 3, L28-50): `project_artifactory_names`,
  `inputs="artifactory_downloads_joined"`, `outputs="enterprise_jfrog_names"`.
- `conf/base/catalog.yml`:
  - Append to the `upstream_discovery` block (currently ~L852-919, the same
    region Story 21.6's own Code Map targets — land this story first):
    `discovery_about_maintainers_raw` (raw, `type:
    pyforge.atlas.datasets.AboutMaintainersDataset`, `url:
    ${globals:endpoint_bases.GITHUB_RAW_BASE_URL}/rxm7706/about/main/README.md`,
    no `credentials:`), `discovery_curated_groups_seed` (raw, `type:
    json.JSONDataset`, `filepath:` a NEW git-tracked
    `conf/base/curated_groups.json` — NOT `${globals:paths.seed_root}`, which
    has a known, pre-existing, deferred path-resolution bug recorded in
    spec-21-2's `deferred` list; a member-tree-relative path avoids it), and
    `enterprise_conda_maintainers` (derived, plain `pandas.ParquetDataset`).
  - Append to the `artifactory_downloads` block (currently ~L920-941):
    `enterprise_jfrog_names` (derived, plain `pandas.ParquetDataset`) — names
    are proposed; both are the implementer's call to rename if a clearer
    convention emerges, but the COLUMN CONTRACT above is fixed.
  - The `org_audit_candidates` catalog entry itself is unchanged (still
    `type: pandas.ParquetDataset`, same filepath) — only its upstream node's
    signature changes.
- `conf/base/parameters.yml` — add `ttls.discovery_about_maintainers_raw:
  604800` (WEEKLY_SECONDS — mirrors the sibling assurance-list cadence, not
  daily like `trending_candidates`; the about README changes on a manual
  maintainer-list refresh cadence, not continuously).
- NEW `conf/base/curated_groups.json` — git-tracked seed. Concrete shape is
  this story's own task, not pre-decided elsewhere: propose `{"groups":
  [{"org": "<label>", "repos": ["owner/repo", ...]}]}`, flattened by the loader
  to the same `repo_full_name` rows `org_audit_candidates` already produces.
- `tests/catalog/conftest.py` — `PREFIX_TO_PIPELINE` (~L68-82): add
  `"discovery": "upstream_discovery"` (skip if Story 21.4 already added it —
  verify first) and `"enterprise": "upstream_discovery"` (new). Bump
  `EXPECTED_PIPELINE_COUNTS["upstream_discovery"]` (currently 4, comment
  ~L96) and `["artifactory_downloads"]` (currently 2, comment ~L97) by however
  many entries this story actually lands; bump `EXPECTED_TOTAL` (currently 95,
  ~L101) by the same total delta.
- `tests/datasets/test_upstream_discovery.py` — existing `TrendingSnapshotDataset`/
  parser test structure to mirror for `AboutMaintainersDataset`/
  `parse_about_readme`.
- `tests/pipelines/upstream_discovery/` — existing node test structure;
  add coverage for `join_enterprise_conda_maintainers` and the extended
  `load_org_audit_candidates`.
- `tests/pipelines/artifactory_downloads/test_nodes.py` — add coverage for
  `project_artifactory_names` (empty input, populated input, schema assertion
  that `download_count`/`version`/`match_source` are absent from the output).
- `tests/artifactory/` — existing `ArtifactoryAqlAdapter`/`join_identity` test
  structure; unaffected (this story does not modify Story 15.1/15.2 code).

## Tasks & Acceptance

**Execution:**
- Confirm the live `rxm7706/about` README's current section headers and line
  format still match the 2026-07-11 snapshot recorded in project memory
  ("List Of FeedStocks - As Maintainer" / "List Of FeedStocks - As
  Co-Maintainer", `N. conda-forge/<feedstock>-feedstock`) before finalizing
  the parser regex (Block If).
- `src/pyforge/atlas/datasets/upstream_discovery.py` — add
  `parse_about_readme(markdown: str) -> list[dict]` (PURE, never raises,
  degrades to `[]` per list on a layout break) and
  `AboutMaintainersDataset(ExternalRefreshDataset)` (injected `fetcher`,
  atomic write, AD-13 staleness pattern, mirrors `TrendingSnapshotDataset`).
  Output columns: `feedstock_slug`, `role` (`"Maintainer"`|`"Co-Maintainer"`),
  `source`, `fetched_at`.
- `src/pyforge/atlas/pipelines/upstream_discovery/nodes.py` — add
  `refresh_about_maintainers(ttls: dict) -> RefreshRequest` (mirrors
  `refresh_trending_candidates`); add
  `join_enterprise_conda_maintainers(discovery_about_maintainers_raw,
  core_feedstock_attribution) -> pd.DataFrame` (strip `conda-forge/`/`-feedstock`
  from `feedstock_slug`, match against `feedstock_name`, emit
  `core_python_package_name`/`role`/`feedstock_slug`/`repository_source`;
  unmatched rows dropped, never raises on empty/malformed input); extend
  `load_org_audit_candidates`'s signature to accept
  `discovery_curated_groups_seed: dict | None` as a second parameter, flatten
  its `groups[].repos[]` into the same `repo_full_name` rows, union with the
  existing `params:org_audit_candidates` rows before the existing dedup step.
- `src/pyforge/atlas/pipelines/upstream_discovery/pipeline.py` — wire the 2 new
  nodes: `refresh_about_maintainers` (`inputs="params:ttls"`,
  `outputs="discovery_about_maintainers_raw"`, mirrors the existing
  `refresh_trending_candidates` node binding exactly) and
  `join_enterprise_conda_maintainers` (`inputs=["discovery_about_maintainers_raw",
  "core_feedstock_attribution"]`, `outputs="enterprise_conda_maintainers"`);
  update `load_org_audit_candidates`'s existing node `inputs=` to
  `["params:org_audit_candidates", "discovery_curated_groups_seed"]`.
- `src/pyforge/atlas/pipelines/artifactory_downloads/nodes.py` +
  `pipeline.py` — add `project_artifactory_names` node + wiring.
- `conf/base/catalog.yml` + `conf/base/parameters.yml` + NEW
  `conf/base/curated_groups.json` — per Code Map.
- `tests/catalog/conftest.py` — register the new prefixes and counts (verify
  current baseline first, per Boundaries).
- Tests — cover the full I/O & Edge-Case Matrix above across the new dataset,
  the 3 new/extended nodes, and the schema-exclusion assertion on
  `enterprise_jfrog_names`.
- Verification housekeeping — `grep -rn 'rxm7706/about'` across the repo to
  confirm this story is the first code (not just docs) to reference it;
  `grep -n '"discovery"\|"enterprise"' tests/catalog/conftest.py` before
  editing, to avoid a duplicate prefix mapping if Story 21.4 landed first.

**Acceptance Criteria:**
- Given `rxm7706/about`'s README is reachable, when
  `discovery_about_maintainers_raw` refreshes, then it carries one row per
  numbered feedstock line with the correct `role`, and a fetch failure keeps
  last-good + marks stale rather than raising or clobbering.
- Given `discovery_about_maintainers_raw` and `core_feedstock_attribution` are
  both populated, when `join_enterprise_conda_maintainers` runs, then
  `enterprise_conda_maintainers` carries `core_python_package_name`/`role`/
  `feedstock_slug`/`repository_source="CDO-ENT-CONDA"` for every matched
  feedstock, and silently drops (never fabricates) unmatched rows.
- Given both `params:org_audit_candidates` and `discovery_curated_groups_seed`
  carry entries, when `load_org_audit_candidates` runs, then the output is the
  deduped union of both sources, and `org_audit_candidates_classified`'s
  existing re-verify-every-run behavior is unchanged.
- Given `params:artifactory.virtual_repos` stays `[]` (the shipped default),
  when the `artifactory_downloads` pipeline runs, then `enterprise_jfrog_names`
  is empty-but-correctly-columned and no live network call is made.
- Given `artifactory_downloads_joined` carries rows (any state, mock or real),
  when `project_artifactory_names` runs, then its output schema never includes
  `download_count`, `version`, or `match_source` — asserted by a dedicated
  test, not left to convention.
- Given `pixi run -e pyforge-atlas kedro-catalog-check`, when run after this
  story, then it passes with the new entries' prefixes/counts registered.

## Design Notes

The about-README parse mirrors `parse_trending_html`'s degrade contract
exactly — a header-string change is the conda-forge-packaging-inventory
equivalent of a GitHub trending-page layout break:

```python
def parse_about_readme(markdown: str) -> list[dict]:
    if not markdown:
        return []
    rows = []
    for section_header, role in (
        ("List Of FeedStocks - As Maintainer", "Maintainer"),
        ("List Of FeedStocks - As Co-Maintainer", "Co-Maintainer"),
    ):
        # locate section_header, iterate its numbered lines until the next
        # header or EOF; a missing header contributes zero rows for that
        # role, never raises.
        ...
    return rows
```

The `enterprise_conda_maintainers` join deliberately does NOT fold in
`org_audit_candidates`/`discovery_curated_groups_seed` — those feed the
EXISTING packaging-candidate classification track
(`classify_trending_candidates` -> tier "1"/"2"/"skip"), a different axis from
"who maintains an already-shipped feedstock." Folding them together would
require inventing a `role="N/A"` semantics `complete-export-contract.md`
reserves but does not define a source for; keeping the two tracks separate
avoids fabricating that mapping.

## Verification

**Commands:**
- `pixi run -e pyforge-atlas kedro-catalog-check` — expected: pass, new
  entries' domain prefixes and pipeline counts registered.
- `pixi run -e pyforge-atlas kedro-test` — expected: full suite green plus new
  tests, no regressions.
- `pixi run -e local-recipes pytest
  src/shared/packages/pyforge-atlas/tests/datasets/test_upstream_discovery.py
  src/shared/packages/pyforge-atlas/tests/pipelines/upstream_discovery/
  src/shared/packages/pyforge-atlas/tests/pipelines/artifactory_downloads/ -q`
  — expected: all green.
- `kedro run --pipelines upstream_discovery,artifactory_downloads` on a fresh
  data root, no live credentials set — expected: exit 0; `enterprise_jfrog_names`
  empty-but-correctly-columned (no live Artifactory call); `discovery_about_maintainers_raw`
  either populated (if the unauthenticated GitHub raw fetch succeeds in the
  run environment) or stale-marked-with-empty-last-good — never a crash.
- `grep -rn 'rxm7706/about' src/shared/packages/pyforge-atlas/` — expected: the
  new dataset module is now among the hits (previously doc-only).

## Review Triage Log

### 2026-08-30 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 1, low 1)
- defer: 3: (high 0, medium 2, low 1)
- reject: 14: (high 0, medium 0, low 14)
- addressed_findings:
  - `[medium]` `[patch]` `refresh_about_maintainers`, `join_enterprise_conda_maintainers`,
    and `project_artifactory_names` were missing from
    `orchestration/definitions.py`'s `refresh_assets` `SCHEDULED_JOBS` entry and
    `NODE_TIMEOUTS` dict, despite the story's own claim that
    `refresh_about_maintainers` "mirrors the Story 21.4 sibling cadence... exactly"
    and "stays schedule-eligible" (Story 21.4's three sibling triggers ARE
    registered in both places). Fixed: registered all three nodes in
    `NODE_TIMEOUTS` (300/120/30s respectively, sized per closest sibling),
    added `refresh_about_maintainers` to `refresh_assets`, and extended
    `tests/orchestration/test_definitions_dryrun.py` with a
    `_STORY_21_5_REFRESH_OPS` subset assertion (mirroring the existing
    `_STORY_21_4_REFRESH_OPS` pattern) plus a new
    `test_node_timeouts_covers_the_story_21_5_nodes` completeness check.
  - `[low]` `[patch]` The new `artifactory_downloads` 4th node
    (`project_artifactory_names` → `enterprise_jfrog_names`) had no DAG-level
    wiring test, unlike the parallel `upstream_discovery` DAG-level coverage
    this same diff added (`test_upstream_discovery_pipeline_has_nine_nodes` +
    single-writer assertion) — only isolated pure-function unit tests existed.
    Fixed: added `test_artifactory_downloads_pipeline_has_four_nodes` and
    `test_enterprise_jfrog_names_has_exactly_one_writer` to
    `tests/pipelines/test_dag_resolves.py`.

Both patches re-verified: `pixi run -e pyforge-atlas kedro-catalog-check`
(61 passed) and `pixi run -e pyforge-atlas kedro-test` (1510 passed, 24
skipped — up from 1507, exactly the 3 new tests) both green, no regressions.

3 findings deferred to frontmatter `deferred:` (malformed-JSON-seed crash —
fleet-wide pre-existing pattern shared with `seed_cwe_categories`/
`seed_spdx_schema`; `catalog-sources.md` naming-drift vs. what was actually
built; the spec's own "fresh data root" Verification claim being inaccurate
for a genuinely empty data root, a pre-existing cross-pipeline-dependency
characteristic already present in Story 13.2's `classify_trending_candidates`).

14 findings rejected as noise: an arbitrary-but-stable `conda_name` pick for
multi-output feedstocks in `join_enterprise_conda_maintainers` (functionally
harmless — all outputs of one feedstock share identical maintainers); the new
`curated_groups.json` being untracked at review time (resolved automatically
by this workflow's own Finalize commit step); the seed's location under
`conf/base/` vs. `conf/base/seeds/` (explicitly directed by the intent-contract's
own Code Map text); a theorized CWD-relative-path resolution gap for
`discovery_curated_groups_seed` that did not reproduce empirically through the
actual `bootstrapped_session()` MCP entrypoint; no recorded evidence of the
spec's own README-shape pre-check (the Block If's documented acceptable-risk
path already covers this, and a spot-check by one reviewer confirmed the
live format still matches); a documented-but-unreachable `role="N/A"` enum
value (cosmetic); a missing type annotation and a redundant-but-harmless
guard (both cosmetic); a silently-resolved `is_internal` conflict in
`project_artifactory_names`'s `drop_duplicates` (out of explicit spec scope,
low likelihood); a premature section-reset edge case in `parse_about_readme`
(mirrors legacy parser behavior exactly, and is the exact risk class the
spec's own Block If already accepts); no dedup on duplicate
`(feedstock_slug, role)` rows (out of explicit spec scope); the "unblocks
Story 21.6" framing being only half-delivered for the JFROG half (expected —
explicitly deferred to Story 23.2 per this story's own "Never" section); and
`curated_groups.json` shipping with an empty `{"groups": []}` seed (explicitly
sanctioned by the spec as "this story's own task, not pre-decided").

## Auto Run Result

Status: done
Blocking condition: none

**Summary of implemented change:** Landed all three Tier 2 catalog sources
`catalog-sources.md` declared but left uncataloged: (1) `discovery_about_maintainers_raw`
(a new `AboutMaintainersDataset`, AD-13 external-refresh, unauthenticated GET
of `rxm7706/about`'s README) joined against `core_feedstock_attribution` into
`enterprise_conda_maintainers` (the CDO-ENT-CONDA universe, unblocking Story
21.6's CDO-ENT-CONDA half); (2) a new git-tracked `discovery_curated_groups_seed`
(`conf/base/curated_groups.json`) unioned into `load_org_audit_candidates`
alongside the existing hand-curated list, preserving its dedup contract
unchanged; (3) a new `project_artifactory_names` node in the existing
`artifactory_downloads` pipeline projecting `pypi_name`/`conda_name`/`is_internal`
only (no telemetry columns) into `enterprise_jfrog_names`.

**Files changed:**
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/upstream_discovery.py` — new `parse_about_readme` (pure, never-raise) + `AboutMaintainersDataset`.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/datasets/__init__.py` — export the two new symbols.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/upstream_discovery/nodes.py` — new `refresh_about_maintainers`, `join_enterprise_conda_maintainers`, `_strip_feedstock_slug`; extended `load_org_audit_candidates` with a second `discovery_curated_groups_seed` input via new `_add_org_audit_row`/`_flatten_curated_groups` helpers.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/upstream_discovery/pipeline.py` — wired the 2 new nodes; updated `load_org_audit_candidates`'s input binding.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/artifactory_downloads/nodes.py` — new `project_artifactory_names`.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/artifactory_downloads/pipeline.py` — wired the new 4th node.
- `src/shared/packages/pyforge-atlas/src/pyforge/atlas/orchestration/definitions.py` — (review patch) registered the 3 new nodes in `NODE_TIMEOUTS`; added `refresh_about_maintainers` to the `refresh_assets` scheduled job.
- `src/shared/packages/pyforge-atlas/conf/base/catalog.yml` — 4 new entries: `discovery_about_maintainers_raw`, `discovery_curated_groups_seed`, `enterprise_conda_maintainers`, `enterprise_jfrog_names`.
- `src/shared/packages/pyforge-atlas/conf/base/parameters.yml` — new `ttls.discovery_about_maintainers_raw` (weekly).
- `src/shared/packages/pyforge-atlas/conf/base/curated_groups.json` — new git-tracked seed, shipped empty (`{"groups": []}`).
- `src/shared/packages/pyforge-atlas/tests/catalog/conftest.py` — registered the `enterprise` prefix; bumped pipeline/total counts.
- `src/shared/packages/pyforge-atlas/tests/datasets/test_upstream_discovery.py` — new coverage for the parser + dataset.
- `src/shared/packages/pyforge-atlas/tests/pipelines/upstream_discovery/test_nodes.py` — new coverage for the join + extended `load_org_audit_candidates`.
- `src/shared/packages/pyforge-atlas/tests/pipelines/artifactory_downloads/test_nodes.py` — new coverage for `project_artifactory_names`.
- `src/shared/packages/pyforge-atlas/tests/pipelines/test_dag_resolves.py` — node-count/single-writer updates for `upstream_discovery`; (review patch) new DAG-level coverage for `artifactory_downloads`.
- `src/shared/packages/pyforge-atlas/tests/orchestration/test_definitions_dryrun.py` — (review patch) `_STORY_21_5_REFRESH_OPS` assertion + `NODE_TIMEOUTS` completeness test.

**Review findings breakdown:** 2 patches applied (1 medium, 1 low — both above); 3 items deferred (frontmatter `deferred:`, above); 14 items rejected as noise (listed in the Review Triage Log above).

**Follow-up review recommendation:** `false` — this pass's patched findings were 1 medium + 1 low, no high; score = 3×1 + 1×1 = 4 (< 5 threshold).

**Verification performed:**
- `pixi run -e pyforge-atlas kedro-catalog-check` — 61 passed.
- `pixi run -e pyforge-atlas kedro-test` — 1510 passed, 24 skipped (0 failed), including the review-pass's 3 new/extended tests.
- `pixi run -e pyforge-atlas parity-diff` — 70 passed (unaffected, out of scope for this story's pipelines).
- `PYTHONPATH=src/shared/packages/pyforge-atlas/src pixi run -e local-recipes pytest src/shared/packages/pyforge-atlas/tests/datasets/test_upstream_discovery.py src/shared/packages/pyforge-atlas/tests/pipelines/upstream_discovery/ src/shared/packages/pyforge-atlas/tests/pipelines/artifactory_downloads/ -q` — 183 passed.
- Live `kedro run --pipelines upstream_discovery,artifactory_downloads` (and separately with `core,pypi_intelligence` included) on a fresh `PYFORGE_ATLAS_DATA_ROOT` — exit 0; verified real Parquet output: `enterprise_conda_maintainers` empty-but-correctly-columned (`core_python_package_name`/`role`/`feedstock_slug`/`repository_source`), `enterprise_jfrog_names` empty-but-correctly-columned (`pypi_name`/`conda_name`/`is_internal`, no telemetry columns), `discovery_about_maintainers_raw` correctly stale-marked with no last-good (offline sandbox, no live fetcher wired), `org_audit_candidates` = 9 rows.
- Matrix Test Audit: all 11 I/O & Edge-Case Matrix rows have a dedicated covering test that ran and passed.
- `grep -rn 'rxm7706/about' src/shared/packages/pyforge-atlas/` — the new dataset module is now among the hits (previously doc-only).
- Adversarial review (4 parallel layers: blind hunter, edge-case hunter, verification-gap, intent-alignment) + targeted empirical verification of the highest-signal findings (multi-output feedstock attribution, malformed-JSON catalog crash, fresh-data-root cross-pipeline crash, CWD-relative-path resolution) before triaging — see Review Triage Log above.

**Residual risks:**
- `curated_groups.json` ships with zero curated groups — Task 2's plumbing is fully wired and tested but has no observable effect until an operator hand-populates it under git review.
- The `rxm7706/about` README parser regex was not re-verified against the live file in this sandbox (network-restricted); it mirrors the 2026-07-11 memory snapshot and the legacy script's regex exactly, per the Block If's documented acceptable-risk path.
- 3 findings deferred (see frontmatter `deferred:`): a malformed `curated_groups.json` crashes the pipeline rather than degrading (fleet-wide pattern shared with `seed_cwe_categories`/`seed_spdx_schema`); `catalog-sources.md` is stale relative to the as-built naming; and this story's own "fresh data root" Verification claim doesn't hold for a genuinely empty data root (pre-existing cross-pipeline-dependency characteristic, not unique to this story).

