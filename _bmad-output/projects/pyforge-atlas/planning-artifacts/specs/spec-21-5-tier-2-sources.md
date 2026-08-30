---
title: 'Tier 2 sources: about, curated orgs, Artifactory names (Story 21.5, Epic 21)'
type: 'feature'
created: '2026-08-30'
status: 'in-review'
baseline_revision: 'd230e7fce20037f7f44134aa8fe765fae597102e'
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

