# CFE Rebuild — Slice Map

Story 6.1 output. Derives the authoritative division of `.claude/skills/conda-forge-expert/`
(as of skill version **v8.82.3**, 2026-08-21) into rebuild slices for Epic 6, and confirms/
corrects the Dream's hypothesized three seams (recipe-authoring, atlas-intelligence,
project-scanning/MCP). Governing contract: `../SPEC.md` — this file derives CAP-1's slice map
specifically; `campaign-state.yaml` (alongside this file) is the fuller CAP-1-through-CAP-4
tracker that also carries the campaign-state (CAP-4), and the equivalence/audit status later
slices will populate (CAP-2, CAP-3).

## Method

Read `.claude/skills/skf-analyze-source/SKILL.md` (and its `_bmad/skf/skf-analyze-source/`
stage files) before deriving anything by hand. `skf-analyze-source` is designed to onboard a
**fresh external repo or package** into new skill-brief.yaml recommendations, written to skf's
own configured `skills_output_folder` — its "Stages" (Scan Project → Identify Units → Map &
Detect → Recommend → Generate Briefs) and headless contract assume the analysis target is not
already a BMAD skill, and its output shape (`analysis-report.md` + one `skill-brief.yaml` per
recommended *new* skill) does not fit "re-seam an existing in-repo skill for a rebuild
campaign, and land the result as two named files inside this Spec's own directory." Per the
Design Notes this story's spec explicitly sanctions the fallback in this situation, so this
map was derived directly from the live tree instead: `find`/`grep` over
`.claude/skills/conda-forge-expert/scripts/*.py`, `.claude/scripts/conda-forge-expert/*.py`,
and `@mcp.tool` registrations in `.claude/tools/conda_forge_server.py`; cross-checked against
import graphs (`grep -rl "import <module>"`), the `pixi.toml` task table, SKILL.md's own
"Core Tools Reference" / "Atlas Intelligence Layer" sections, and
`src/shared/packages/pyforge-mason/src/pyforge/mason/cfe.py`'s `_CFE_SCRIPTS` table. Every
classification below traces to one of those sources, not to naming intuition alone (naming
intuition is used only as a first pass, always confirmed against actual imports/wrappers/pixi
tasks/MCP registrations before it counts as "derived").

## Coverage Reconciliation

**Scope of the 68/57/46 totals below**, stated explicitly here rather than left to be
discovered piecemeal in the Mason Caller Inventory's footnotes: they cover exactly three
counted surfaces — `.claude/skills/conda-forge-expert/scripts/*.py` (canonical scripts),
`.claude/scripts/conda-forge-expert/*.py` (CLI wrappers), and `@mcp.tool` registrations in
`.claude/tools/conda_forge_server.py` (MCP tools). Two CFE-root build artifacts Mason calls
today — `native-build.sh` and `build-locally.py` — sit outside all three counted surfaces
(bash, and CFE-root top-level respectively) and are therefore outside this story's coverage
universe entirely; see Slice 2 and the Mason Caller Inventory below for where they are still
tracked in role even though no coverage total includes them.

Live-tree counts as of this run (re-verify at any later run — do not trust these as
permanently fixed):

| Surface | Count | Command |
|---|---|---|
| Canonical scripts | **68** | `find .claude/skills/conda-forge-expert/scripts -name "*.py" \| wc -l` |
| CLI wrappers | **57** | `find .claude/scripts/conda-forge-expert -name "*.py" \| wc -l` |
| MCP tool registrations | **46** | `grep -c "@mcp.tool" .claude/tools/conda_forge_server.py` |

Per-slice totals below sum to these three counts exactly, with zero unclassified files
(CAP-1's "derive, don't declare" success criterion):

| Slice | Scripts | Wrappers | MCP tools |
|---|---|---|---|
| 1. Recipe Generation | 3 | 3 | 3 |
| 2. Recipe Lifecycle | 22 | 17 | 19 |
| 3. Atlas Intelligence | 37 | 35 | 22 |
| 4. Project Scanning & Security | 2 | 2 | 2 |
| 5. Shared Infrastructure | 4 | 0 | 0 |
| **Total** | **68** | **57** | **46** |

The Spec's own prose estimate ("~67 scripts") undercounted by one against the live 68; the
57 wrapper / 46 MCP-tool figures the Spec's Design Notes carried forward from this session's
prior investigation are both confirmed exactly against the live tree.

## Confirmation vs. Correction of the Dream's 3-Seam Hypothesis

The Dream hypothesized three seams: **recipe-authoring**, **atlas-intelligence**,
**project-scanning/MCP**. Derivation result:

- **atlas-intelligence** — CONFIRMED as a single coherent seam (Slice 3 below): the 15
  pipeline phases (B→N), `cf_atlas.db`, and their 22 MCP tools / 35 wrappers form one clearly
  bounded subsystem with its own SKILL.md section ("Atlas Intelligence Layer"), its own
  reference docs (`atlas-phases-overview.md`, `atlas-phase-engineering.md`), and its own guide
  (`guides/atlas-operations.md`).
- **project-scanning/MCP** — CONFIRMED as a real, distinct seam (Slice 4), but much smaller
  than the Dream implied: it is exactly `scan_project.py` + `env_inspect.py` (2 scripts, 2
  wrappers, 2 MCP tools). `scan_project.py` reads `cf_atlas.db` read-only for enrichment
  (confirmed: `_atlas_connect_ro()`, line 1743) but is not one of the atlas pipeline's own
  phases (B–N) and is not owned by `conda_forge_atlas.py` — it is a downstream *consumer* of
  the atlas DB, plus ~3700 lines of independent scanning logic (manifests, container images,
  SBOMs, live envs, GitOps) that has nothing to do with fleet-wide package intelligence. Kept
  separate from atlas-intelligence for that reason, with the cross-slice DB-read dependency
  called out explicitly (see Slice 4 below).
- **recipe-authoring** — CORRECTED / SPLIT. The Dream treated this as one seam; the live tree
  does not support that — it splits cleanly into two, per the Spec's own explicit instruction
  to name a first slice scoped narrowly to **recipe generation**:
  - **Slice 1: Recipe Generation** — `recipe-generator.py` and its true import-graph
    satellites, tightly scoped.
  - **Slice 2: Recipe Lifecycle** — everything else recipe-authoring does after a recipe
    exists: validate, optimize, update/autotick, build, migrate, submit, and the
    pre-submission feedstock-context checks. This is the single largest domain slice by file
    count (22 scripts / 17 wrappers / 19 MCP tools) — a legitimate rebuild-campaign candidate
    for further splitting in a later story, not attempted here since CAP-1 only asks this
    story to confirm/correct the Dream's seams, not to invent new sub-seams beyond what the
    live tree's own coupling (imports, wrapper pairing, MCP grouping) forces.
- **New seam not in the Dream: Slice 5, Shared Infrastructure.** Four canonical scripts
  (`_http.py`, `_paths.py`, `_cfy_template.py`, `_sbom.py`) are imported across two or more of
  the domain slices above (see each slice's "Cross-slice dependencies" note) and have no MCP
  tool or CLI wrapper of their own — they exist purely to be imported. The Dream's 3-seam
  hypothesis had no place for these; a 4th bucket per domain slice would have force-assigned
  genuinely-shared code to one arbitrary owner, which is a guess, not a derivation. Named as
  its own slice instead.

## Slice Ordering (fixed)

1. **Recipe Generation** — named explicitly by the Spec as the first slice. Already a Mason
   caller (`generate_recipe`/`update_recipe_from_github` adapters in `cfe.py`).
2. **Recipe Lifecycle** — the natural second slice: every other stage of the autonomous loop
   after a recipe exists, and the other domain slice Mason already calls into today (8 of its
   10 `_CFE_SCRIPTS` adapters resolve here — see Mason Caller Inventory below).
3. **Atlas Intelligence** — the largest remaining domain slice; zero current Mason callers.
4. **Project Scanning & Security** — smallest remaining domain slice; zero current Mason
   callers.
5. **Shared Infrastructure** — ordered last: it has no MCP tool or wrapper surface of its own
   and is not an independent rebuild unit in the same sense as 1–4 — each of its four modules
   is pulled along opportunistically whenever the domain slice(s) that import it are ported.
   Tracked as its own campaign entry purely for total-coverage completeness (CAP-1), not
   because a Story 6.3-style compile pass is expected to target it standalone before slices
   1–4 exist.

**Known ordering risk (not resolved by this story):** Slice 2 is ordered before Slice 3 even
though `scan_for_vulnerabilities` (Slice 2) consumes the CVE database `cve_manager.py` (Slice
3) builds — the same class of cross-slice dependency that puts Slice 4 *after* Slice 3 for its
`cf_atlas.db` read. This is acceptable for now only because no slice beyond Slice 1 is being
briefed or compiled in this campaign phase (CAP-4: no second brief before the re-scope gate);
whoever briefs Slice 2 should re-confirm this ordering still holds up against Slice 3's actual
compile state at that time.

This order is what `campaign-state.yaml` tracks; briefing (Story 6.2) targets Slice 1 first.

---

## Slice 1: Recipe Generation

**Scope:** creating a brand-new recipe from an upstream package source. Deliberately narrow —
see "Recipe Generation vs. Recipe Lifecycle boundary" below for what was deliberately left out.

**Canonical scripts (3):**

| Script | Role | Wrapper | Notes |
|---|---|---|---|
| `recipe-generator.py` | The generator itself (PyPI/npm/CRAN/CPAN/LuaRocks; `main()` dispatches by ecosystem) | `generate-recipe` (+ `generate-cran`/`generate-cpan`/`generate-luarocks`/`generate-npm`, all `recipe-generator.py <ecosystem>`) | 2332 lines; largest single script in the skill |
| `name_resolver.py` | PyPI→conda name resolution (cache-first); imported directly by `recipe-generator.py` | `resolve-name` | Also backs `get_conda_name` MCP tool directly (see below) — confirmed by reading `conda_forge_server.py::get_conda_name`, which calls `NAME_RESOLVER_SCRIPT` |
| `github_updater.py` | GitHub-release-based recipe version/SHA update | `autotick-github` | Imports Slice 2's `github_version_checker.py` (sibling import, sanctioned cross-slice dependency -- see "Cross-slice dependencies" below and Slice 5's cross-slice-shared-imports table); included here (not Slice 2) because the Spec's intent-contract explicitly names `update_recipe_from_github` as a Slice-1 MCP tool |

**MCP tools (3):** `generate_recipe_from_pypi`, `update_recipe_from_github`, `get_conda_name`
(the third one is a derived addition, not guessed — see the `name_resolver.py` row above; it
would be inconsistent to split a tool from the one script that implements it).

**Wrappers (3):** `generate-recipe`, `resolve-name`, `autotick-github` pixi tasks (all
`.claude/scripts/conda-forge-expert/{recipe-generator,name_resolver,github_updater}.py`), plus
the four `recipe-generator.py <ecosystem>` sub-invocations (`generate-cran`/`-cpan`/
`-luarocks`/`-npm`) — same one wrapper file, not additional files.

**Knowledge (SKILL.md, verified by section content, not just gotcha number):**
- **G54** (line 3006) — "Source preference is sdist > GitHub-source > wheel" — generator
  source-selection logic.
- **G91** (line 3721) — "PEP 517 backend + plugin host deps the generator misses" — fixed in
  `recipe-generator.py`'s `_extract_build_system_requires_from_sdist`/host-dep mirroring per
  CHANGELOG v8.69.0 item 7.
- **G94's third sub-item** (line 3755, "Case-variant generator output dirs" under "Why —
  three verified classes") — not a separately-numbered gotcha ID in SKILL.md itself (no
  literal "G94c" exists there; don't grep for that string) — confirmed live in
  `recipe-generator.py:2490` (`# G94c: lowercase feedstock-style dir`, the script's own
  internal shorthand comment) and CHANGELOG v8.69.0 item 8.
- **G98** (line 3790) — repo-wide cfe-metadata batch-edit conventions; `recipe-generator.py`'s
  `_render_cfe_block()` is the emission side of this gotcha (CHANGELOG v8.69.0 item 1).
- SKILL.md "Core Tools Reference § Recipe Creation & Modification" (line 1251).
- `reference/recipe-yaml-reference.md`, `reference/meta-yaml-reference.md`,
  `reference/jinja-functions.md` (generation-time format references).
- `guides/getting-started.md`.

**Recipe Generation vs. Recipe Lifecycle boundary (derived, not assumed):** the SKILL.md
"Core Tools Reference § Recipe Creation & Modification" table also lists
`generate_recipe_from_npm`/`_cran`/`_cpan`/`_luarocks` and (under § Security & Maintenance)
`update_recipe_from_npm` as if they were tools on par with the three above — **they are not
MCP-registered**. Grepping `conda_forge_server.py` for each name returns nothing; npm/CRAN/
CPAN/LuaRocks generation are `recipe-generator.py` CLI subcommands only, and
`update_recipe_from_npm` is `npm_updater.py`'s CLI-only capability (`autotick-npm` pixi task).
Both facts matter for the rebuild campaign: the doc table overstates the MCP surface by 5
entries, and `npm_updater.py` is classified under Slice 2, not here (see that slice's notes).

**Cross-slice dependencies:** none inbound. Slice 1 itself depends on Slice 5's
`_cfy_template.py` (imported directly by `recipe-generator.py` for `conda-forge.yml`
rendering) and on Slice 2's `github_version_checker.py` (imported directly by
`github_updater.py`'s `update_recipe()` for GitHub release/tag lookups; ported into the
compiled Slice-1 package as a sanctioned cross-slice runtime dependency, same shape as
`_cfy_template.py` -- see the cross-slice-shared-imports table under Slice 5 below;
`github_version_checker.py` itself stays Slice 2 canonical, not reclassified).

---

## Slice 2: Recipe Lifecycle

**Scope:** everything that happens to a recipe after it exists — validate, optimize,
autotick/update, build, diagnose failures, security-scan, migrate v0→v1, and submit — plus the
pre-submission feedstock-context checks (G58: check before you submit) and general dev-env
health/reference tooling that supports this stage of the loop.

**Canonical scripts (22):** `validate_recipe.py`, `recipe_editor.py`, `recipe_optimizer.py`,
`recipe_updater.py`, `npm_updater.py`, `dependency-checker.py`, `license-checker.py`,
`mapping_manager.py`, `feedstock-migrator.py`, `local_builder.py`, `failure_analyzer.py`,
`submit_pr.py`, `feedstock_lookup.py`, `feedstock_context.py`, `feedstock_enrich.py`,
`_path_guard.py`, `gen_yml_reference.py`, `test-skill.py`, `vulnerability_scanner.py`,
`pr_artifacts.py`, `github_version_checker.py`, `health_check.py`.

**Wrappers (17):** `validate_recipe.py`, `recipe_optimizer.py`, `recipe_updater.py`,
`npm_updater.py`, `dependency-checker.py`, `license-checker.py`, `mapping_manager.py`,
`feedstock-migrator.py`, `local_builder.py`, `failure_analyzer.py`, `submit_pr.py`,
`prepare_pr.py` (delegates to `submit_pr.py --prepare-only` — the one wrapper with no
same-named canonical script), `gen_yml_reference.py`, `vulnerability_scanner.py`,
`pr_artifacts.py`, `github_version_checker.py`, `health_check.py`. (`recipe_editor.py`,
`feedstock_lookup.py`, `feedstock_context.py`, `feedstock_enrich.py`, `_path_guard.py`,
`test-skill.py` have no CLI wrapper — MCP-server-only or, for `test-skill.py`, no consumer at
all; see note below.)

**MCP tools (19):** `validate_recipe`, `check_dependencies`, `run_system_health_check`,
`scan_for_vulnerabilities`, `trigger_build`, `get_build_summary`, `lookup_feedstock`,
`enrich_from_feedstock`, `get_feedstock_context`, `edit_recipe`, `update_mapping_cache`,
`analyze_build_failure`, `optimize_recipe`, `update_recipe`, `prepare_submission_branch`,
`submit_pr`, `check_github_version`, `migrate_to_v1`, `download_pr_artifacts`.

**Pixi tasks:** `validate`, `lint-optimize`, `autotick`, `autotick-npm`, `check-deps`,
`license-check`, `update-mapping-cache`, `migrate`, `build-local(-all|-check|-setup-sdk)`,
`analyze-failure`, `submit-pr`, `prepare-pr`, `gen-yml-reference`, `scan-vulnerabilities`,
`pr-artifacts`, `version-check`, `health-check`, plus the bash-script build wrappers
`recipe-build`/`recipe-build-cross` (`native-build.sh`/`cross-build.sh` — outside the counted
`*.py` wrapper surface, still Slice-2 in role).

**Knowledge:** SKILL.md "Core Tools Reference §§ Validation & Quality / Build & Debug /
Security & Maintenance" (lines 1262–1290); "Build Failure Protocol" (line 978); "Migration
Protocol" (line 1071); Recipe Authoring Gotchas G1–G53, G55–G90, G92–G97, G99–G108 (i.e. every
gotcha *not* claimed by Slice 1 above — not individually re-partitioned in this pass; nearly
all concern recipe-authoring mechanics that live operationally in this slice, but a future
briefing story should confirm each on its own rather than trust this blanket statement).
`guides/migration.md`, `guides/testing-recipes.md`, `guides/ci-troubleshooting.md`,
`guides/cross-compilation.md`, `guides/feedstock-maintenance.md`,
`guides/feedstock-platform-expansion.md`, `guides/sdist-missing-license.md`.
`reference/pinning-reference.md`, `reference/selectors-reference.md`,
`reference/python-min-policy.md`, `reference/conda-forge-ecosystem.md`,
`reference/conda-forge-yml-reference(-full).md`, `reference/recipe-yaml-reference-full.md`,
`reference/abi3-matrix-collapse.md`.

**Notes / derived corrections:**
- `npm_updater.py` sits alongside `github_updater.py`/`recipe_updater.py` by naming symmetry
  (all three are "autotick" siblings), but it is classified here, not Slice 1, because its MCP
  tool (`update_recipe_from_npm` per the doc table) does not actually exist as an
  `@mcp.tool` registration — see Slice 1's boundary note — and the Spec's Always boundary
  locks only `generate_recipe_from_pypi`/`update_recipe_from_github` into Slice 1.
- `cve_manager.py` (`update_cve_database` MCP tool) is classified under **Slice 3**, not here,
  even though `scan_for_vulnerabilities` (this slice) consumes the CVE DB it builds — see
  Slice 3's cross-slice note.
- `test-skill.py` is a 10-line ad-hoc script (`test_api()` hitting
  `api.anaconda.org/package/conda-forge/pillow`) — **not** the skill's real test harness (that
  is `.claude/skills/conda-forge-expert/tests/run_skill_suite.py`, backing the `test-skill`
  pixi task, outside the counted scripts directory entirely — two different files that happen
  to share a similar name). No wrapper, no MCP tool, no import from anywhere else. Classified
  here only because it touches the same conda-forge package-metadata domain as
  `dependency-checker.py`; flagged as a likely dead-code / cleanup candidate for whichever
  future story compiles this slice, not as confirmed-useful.
- `gen_yml_reference.py` regenerates the `*-reference-full.md` docs consumed by both this
  slice and Slice 1 — kept here as the nearer conceptual fit (recipe-format reference
  material), not moved to Slice 5, since it is a standalone CLI (no inbound imports from any
  other script) rather than a genuinely shared library module.
- `trigger_build`/`get_build_summary` (MCP tools counted above) have no single backing
  canonical script the way most tools in this slice do — confirmed by reading
  `conda_forge_server.py` directly: `trigger_build`'s `mode='native'` path runs `rattler-build
  build` as an **inline subprocess call in `conda_forge_server.py` itself**, with no canonical
  script at all (the same "no backing script" pattern as Slice 3's `query_atlas`);
  `mode='docker'` delegates to `build-locally.py`, one of the two CFE-root artifacts this
  document's Coverage Reconciliation scope note excludes from the counted universe.
  `get_build_summary` just reads the summary file the above produces — also no script.
  `local_builder.py` (counted above, in this slice's 22 scripts) is a **separate** canonical
  script backing only the `build-local(-all|-check|-setup-sdk)` pixi tasks; it has no MCP tool
  of its own. Do not conflate the two when briefing this slice.

**Cross-slice dependencies:** imports `_cfy_template.py` (`submit_pr.py`), `_paths.py`
(`recipe_optimizer.py`, `feedstock_lookup.py`, `feedstock_context.py`), `_http.py`
(`mapping_manager.py`, `dependency-checker.py`, `recipe_updater.py`, `npm_updater.py`,
`pr_artifacts.py`, `github_version_checker.py`) — all Slice 5. `scan_for_vulnerabilities`
consumes the CVE database `cve_manager.py` (Slice 3) builds.

---

## Slice 3: Atlas Intelligence

**Scope:** the SQLite-backed cross-channel package map (`cf_atlas.db`), its 15 pipeline
phases (B→N), and every fleet-wide reporting/triage CLI built on top of it — including the
cyclonedx-universe-inventory tooling and the read-only gap-suggester scripts, all of which
read from or write to `cf_atlas.db`/`v_actionable_packages`.

**Canonical scripts (37):** `conda_forge_atlas.py`, `atlas_phase.py`, `detail_cf_atlas.py`,
`staleness_report.py`, `feedstock_health.py`, `behind_upstream.py`, `whodepends.py`,
`adoption_stage.py`, `find_alternative.py`, `release_cadence.py`, `version_downloads.py`,
`platform_breakdown.py`, `pyver_breakdown.py`, `channel_split.py`, `my_feedstocks.py`,
`pypi_intelligence.py`, `pypi_only_candidates.py`, `recommend_2027.py`, `library_futures.py`,
`inventory_channel.py`, `add_handoff.py`, `export_purls.py`, `mapping_gap.py`,
`universe_sbom.py`, `inventory_match.py`, `lts_registry_gap.py`, `cwe_seed_gap.py`,
`spdx_schema_gap.py`, `license_map_gap.py`, `cwe_catalog_fetcher.py`, `cisa_kev_fetcher.py`,
`epss_fetcher.py`, `cve_manager.py`, `cve_watcher.py`, `bootstrap_data.py`,
`_parquet_cache.py`, `_cf_graph_versions.py`.

**Wrappers (35):** same list minus `_parquet_cache.py`/`_cf_graph_versions.py` (private,
imported only by `conda_forge_atlas.py`, no wrapper).

**MCP tools (22):** `update_cve_database`, `staleness_report`, `platform_breakdown`,
`pyver_breakdown`, `channel_split`, `feedstock_health`, `whodepends`, `behind_upstream`,
`cve_watcher`, `version_downloads`, `release_cadence`, `find_alternative`, `adoption_stage`,
`pypi_only_candidates`, `export_purls`, `universe_sbom`, `inventory_match`, `recommend_2027`,
`pypi_intelligence`, `package_health` (confirmed: calls `detail_cf_atlas.py --json`),
`query_atlas` (confirmed: direct read-only `sqlite3` query against `cf_atlas.db`, implemented
inline in `conda_forge_server.py` — no canonical `scripts/*.py` backs it, still classified
here by role), `my_feedstocks`.

**Pixi tasks:** `bootstrap-data`, `build-cf-atlas`, `query-cf-atlas`, `stats-cf-atlas`,
`atlas-phase`, `detail-cf-atlas` (+ `--vdb`/`--vdb-all` variants under the `vuln-db` feature),
`staleness-report`, `whodepends`, `behind-upstream`, `channel-split`, `cve-watcher`,
`platform-breakdown`, `pyver-breakdown`, `find-alternative`, `adoption-stage`,
`pypi-only-candidates`, `export-purls`, `mapping-gap`, `universe-sbom`, `inventory-match`,
`library-futures`, `recommend-2027`, `add-handoff`, `pypi-intelligence`, `feedstock-health`,
`version-downloads`, `release-cadence`, `update-cve-db`, `fetch-cisa-kev`, `fetch-epss`,
`fetch-cwe-catalog`, `lts-registry-gap`, `cwe-seed-gap`, `spdx-schema-gap`,
`license-map-gap`, `my-feedstocks`, `inventory-channel` (also under `vuln-db` feature).

**Knowledge:** SKILL.md "Atlas Intelligence Layer" (line 814–950 incl. "Daily-use CLIs",
"MCP exposure", "When to invoke the atlas", "Persona catalog + phase overview"; explicitly
cites `reference/atlas-phases-overview.md`, `reference/atlas-phase-engineering.md`).
`guides/atlas-operations.md`.

**Notes / derived corrections:**
- `cve_manager.py` is placed here (not Slice 2) even though `scan_for_vulnerabilities`
  (Slice 2, per-recipe scanning) also consumes the CVE DB it maintains — SKILL.md's own text
  ("only Phase G's fresh vuln data needs the heavy `vuln-db` env") and its co-location with
  `cisa_kev_fetcher.py`/`epss_fetcher.py`/`cwe_catalog_fetcher.py` (unambiguous Phase-G data
  fetchers) makes atlas the better-fitting owner; the reverse dependency is noted, not hidden.
- The CLAUDE.md project doc's "17 CLIs" figure for the atlas is stale — SKILL.md's own
  "Daily-use CLIs" table plus the gap-suggester CLIs enumerate more than 17 today; not
  reconciled further here (out of this story's scope — flagged for the sync-runbook loop, not
  fixed by this story).

**Cross-slice dependencies:** imports `_http.py` (most fetchers/CLIs), `_sbom.py`
(`inventory_channel.py`, `spdx_schema_gap.py`, `library_futures.py`, `add_handoff.py`,
`recommend_2027.py`, `universe_sbom.py`, `license_map_gap.py`, `inventory_match.py`,
`conda_forge_atlas.py`), `_paths.py` (`bootstrap_data.py`) — all Slice 5. `scan_project.py`
and `env_inspect.py` (Slice 4) read `cf_atlas.db` read-only for enrichment (inbound
dependency from Slice 4, not outbound from here).

---

## Slice 4: Project Scanning & Security

**Scope:** scanning an arbitrary *consumer* project (not a conda-forge recipe or the
conda-forge fleet) — manifests, lock files, SBOMs, container images, live envs, GitOps
manifests, and pixi/conda environment introspection.

**Canonical scripts (2):** `scan_project.py` (3759 lines — the largest scanning surface in the
skill; ~30 input-format support matrix), `env_inspect.py`.

**Wrappers (2):** `scan_project.py` (`scan-project` under the `vuln-db` feature),
`env_inspect.py` (`env-inspect`).

**MCP tools (2):** `scan_project`, `env_inspect`.

**Pixi tasks:** `scan-project` (`vuln-db` feature), `env-inspect`.

**Knowledge:** `reference/dependency-input-formats.md` (explicitly cited from SKILL.md's
"Format coverage for `scan-project`", ~30-format support matrix).

**Cross-slice dependencies:** both scripts read `cf_atlas.db` read-only via `_sbom.py`/direct
`sqlite3` (Slice 5 / Slice 3 boundary) for conda-forge match enrichment; `scan_project.py`
additionally imports `detail_cf_atlas._extract_vuln_fields` (Slice 3) directly at line 2655.
Neither script is imported by anything outside this slice.

---

## Slice 5: Shared Infrastructure

**Scope:** private (underscore-prefixed) helper modules with no CLI wrapper or MCP tool of
their own, imported by two or more of Slices 1–4. Not a "seam" the Dream anticipated; added
because force-assigning genuinely cross-cutting code to one arbitrary domain slice would have
been a guess, not a derivation (see Confirmation vs. Correction section above).

**Canonical scripts (4):** the table below has 5 rows, not 4 -- the 5th (`github_version_checker.py`)
is **not** one of Slice 5's own canonical scripts, it is a cross-slice-shared-*import* row for
a script canonical elsewhere. Read on before the table.

`github_version_checker.py` is, and stays, Slice 2 canonical (own wrapper + MCP tool -- see
Slice 2's inventory above) but is imported directly by Slice 1's `github_updater.py`, and was
ported into Slice 1's compiled package as a sanctioned cross-slice runtime dependency (same
shape as `_cfy_template.py`). It is recorded here because this table is the campaign's
canonical place for cross-slice import edges, not because it changes Slice 5's own scope or
script count (still 4).

| Script | Imported by (confirmed via `grep -rl`) | Slices spanned |
|---|---|---|
| `_http.py` | `recipe-generator.py` (S1); `mapping_manager.py`, `dependency-checker.py`, `recipe_updater.py`, `npm_updater.py`, `pr_artifacts.py`, `github_version_checker.py` (S2); `conda_forge_atlas.py`, `detail_cf_atlas.py`, `cve_manager.py`, `cisa_kev_fetcher.py`, `cwe_catalog_fetcher.py`, `epss_fetcher.py`, `lts_registry_gap.py`, `spdx_schema_gap.py`, `inventory_match.py`, `inventory_channel.py`, `library_futures.py`, `_parquet_cache.py` (S3); `env_inspect.py` (S4) | 1, 2, 3, 4 |
| `_paths.py` | `recipe_optimizer.py`, `feedstock_lookup.py`, `feedstock_context.py` (S2); `bootstrap_data.py` (S3) | 2, 3 |
| `_cfy_template.py` | `recipe-generator.py` (S1); `submit_pr.py` (S2) | 1, 2 |
| `_sbom.py` | `inventory_channel.py`, `spdx_schema_gap.py`, `library_futures.py`, `add_handoff.py`, `recommend_2027.py`, `universe_sbom.py`, `license_map_gap.py`, `inventory_match.py`, `conda_forge_atlas.py` (S3); `env_inspect.py`, `scan_project.py` (S4) | 3, 4 |
| `github_version_checker.py` *(Slice 2 canonical, not Slice 5 -- see note above)* | `github_updater.py` (S1) | 1, 2 |

**Wrappers:** none (0) for the four Slice-5 canonical scripts above — none of them have a
same-named file under `.claude/scripts/conda-forge-expert/`; they are never invoked as a
standalone CLI. (`github_version_checker.py`'s row is the one exception in the table, by
design: it already has its own wrapper and MCP tool under Slice 2 -- see that slice's own
Wrappers/MCP-tools inventory above; it does not gain a second, Slice-5-owned wrapper.)

**MCP tools:** none (0) for the four Slice-5 canonical scripts above; `github_version_checker.py`'s
own `check_github_version` MCP tool is Slice 2's, unchanged (see note above).

**Narrow-use helpers deliberately NOT placed here:** `_path_guard.py` (imported only by
`recipe_editor.py` + `submit_pr.py`, both Slice 2 → assigned to Slice 2), `_parquet_cache.py`
and `_cf_graph_versions.py` (imported only by `conda_forge_atlas.py`, Slice 3 → assigned to
Slice 3). The rule applied throughout: a helper is "shared infrastructure" only when its
confirmed importers span **two or more** domain slices; a single-slice helper is assigned to
that slice, not force-generalized here.

---

## Mason Caller Inventory

`src/shared/packages/pyforge-mason/src/pyforge/mason/cfe.py`'s `_CFE_SCRIPTS` table (the sole
sanctioned Mason→CFE call surface, AD-3) maps 10 adapter keys to CFE scripts:

| Mason adapter key | CFE script | Slice |
|---|---|---|
| `generate_recipe` | `recipe-generator.py` | 1 |
| `update_recipe_from_github` | `github_updater.py` | 1 |
| `validate_recipe` | `validate_recipe.py` | 2 |
| `submit_pr` | `submit_pr.py` | 2 |
| `build_native` | `native-build.sh` | 2 (bash, outside the counted `*.py` wrapper surface) |
| `build_docker` | `build-locally.py` | 2 (CFE-root top level, outside `scripts/`/wrapper dirs — outside this story's counted coverage universe entirely) |
| `diagnose_failure` | `failure_analyzer.py` | 2 |
| `optimize_recipe` | `recipe_optimizer.py` | 2 |
| `scan_for_vulnerabilities` | `vulnerability_scanner.py` | 2 |
| `update_recipe` | `recipe_updater.py` | 2 |

**Derived finding:** Mason calls into Slice 1 (2 of 10 adapters) and Slice 2 (8 of 10
adapters) today, and has **zero callers into Slice 3 (Atlas Intelligence) or Slice 4 (Project
Scanning & Security)**. This directly supports the slice ordering above — Slices 1 and 2 are
where Mason already has skin in the game; Slices 3 and 4 are not yet wired to any Mason
use-case, which is exactly why they rank after Slices 1–2 rather than before them.
