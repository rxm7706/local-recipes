---
title: "35.2: The VCS batches come from the whole universe"
type: 'feature'
created: '2026-10-18'
status: 'in-review'
baseline_revision: '9b35deafc0'
flag:
  key: pyforge.atlas.live_vcs_universe            # minted by Story 35.1, shared by Epic 35's feature stories
  provider: openfeature-file                      # the one tree, src/platform/config/flags.json (canopy:AD-11)
  default: {production: off, staging: off, dev: on}   # per-env values through src/platform/config/flag-overlays.json
  scope: global                                   # v1 is global only
  fallback: 'every VCS and registry store reads the identity batch (identity_packages_primary), as before this story'
  cleanup: 90 days after ON in every environment (spec-feature-flag-governance Q4)
review_loop_iteration: 0
followup_review_recommended: false
context:
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/SPEC.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-pyforge-atlas/live-sources.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-35-1-one-opt-in-switch-and-github-authenticates.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/specs/spec-34-7-the-vulnerability-stores-refresh-themselves.md
  - _bmad-output/projects/pyforge-atlas/planning-artifacts/epics.md
  - docs/reference/story-spec-flag-block.md
  - src/shared/packages/pyforge-atlas/src/pyforge/atlas/pipelines/vcs_health/vcs_refresh_identifiers.py
  - .claude/skills/conda-forge-expert/scripts/conda_forge_atlas.py
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** every VCS and registry batch comes from `identity_packages_primary`, the OpenTeams subset
(`batches_from_identity`), so the stores cover 727 GitHub repos where legacy Phase K covers 26,272 packages.

Legacy selects from `v_actionable_packages` and the recipe's about URLs (Phase E):
- **Phase K** (CFA:5161-5181, 5251): the first of the repo, dev and home URLs that names a GitHub, Codeberg or GitLab
  repo (`_extract_vcs_repo`, CFA:4580).
- **Phase L** (CFA:5899-5925): npm and Maven names from the recipe's source URL (Phase E, CFA:2049, 2450-2467), and
  crates, rubygems, nuget and Maven names from the about URLs (`_detect_registry_from_urls`, CFA:5755). Legacy never
  writes cran, cpan or luarocks names.
- **Phase N** (CFA:6592-6609): every actionable package's feedstock.

**Approach:**
1. **`batches_from_universe`** (`vcs_refresh_identifiers.py`) builds the batches from every enumerated conda package
   (Phase B). Each package's recipe fields come from the feedstock it is attributed to (Phase B.5), else its first
   anchor (`core_sources.package_recipe_fields`, Story 34.7). It returns:
   - `upstream_repos`: `(conda_name, owner, repo)` per GitHub upstream;
   - `gitlab` / `codeberg`: `(conda_name, project)` pairs;
   - `registries`: `(conda_name, name)` pairs per registry;
   - `feedstocks`: the feedstock of every enumerated package (Phase N, for Story 35.3).
   The regexes are legacy's, so a GitHub repo name stops at a dot (`solo-py.git` reads `solo-py`).
   - Deviation: legacy selects actionable packages (active, feedstock not archived); here every enumerated package is a
     candidate, a superset (archived feedstocks still publish packages).
2. **The triggers carry both batches.** `refresh_vcs_github_store`, `refresh_vcs_host_stores` and
   `refresh_vcs_registry_stores` take `core_packages_enumerated`, `core_cf_graph_raw` and `core_feedstock_attribution`
   beside `identity_packages_primary`; `RefreshRequest` gains `upstream_repos`, `universe_pairs` and `feedstocks`.
   Nodes stay pure.
3. **The stores read the flag.** With `pyforge.atlas.live_vcs_universe` on, `GitHubRequestDataset` asks for the
   universe's distinct `(owner, repo)`, and the host and registry stores load `universe_pairs`. Off, each reads the
   identity batch, as before. The flag is read at save, as Story 35.1's switch is.

**Scope.** The GitHub query itself (releases, tags, feedstock health) is Story 35.3; the hosts' and registries' fetches
are Story 35.4. Neither changes here.

Ledger key: `35-2-the-vcs-batches-come-from-the-whole-universe`.
Type / Effort / Deps: feature / M / Story 34.3 (node_attrs), Story 34.7 (the about URLs), Story 35.1 (the flag).

### Living CAP citations

- **`spec-pyforge-atlas` CAP-65** (FR-73): VCS and registry fetches cover the full universe.
- **AD-3** (cross-pipeline inputs by catalog name), **AD-11** (no test reaches the network).
- **Ruling.** 2026-10-18, "Full universe (Recommended)".

## Acceptance Criteria

- **AC1 — Phase K.** For each enumerated package, the first of its repo, dev and home URLs that names a GitHub,
  Codeberg or GitLab repo, checked in that order per URL, gives its upstream; GitLab keeps the whole project path.
- **AC2 — Phase L.** npm and Maven from the source URL, then crates, rubygems, nuget and Maven from the about URLs;
  cran, cpan and luarocks stay empty, as legacy.
- **AC3 — Phase N.** The feedstock of every enumerated package.
- **AC4 — Attribution.** A package's fields come from its attributed feedstock, else its first anchor; a package
  outside the enumeration is never batched.
- **AC5 — Flag.** On, every store reads the universe's batch; off, the identity batch, unchanged; tested in both states.
- **AC6 — The population test.** With identity naming a repo the universe does not, the flag-on GitHub store never asks
  for it.
- **AC7 — Live.** See Verification. Tolerance against legacy the same day: at least 99% of legacy Phase K's packages
  batched, with the same repo for at least 99% of those; every legacy Phase N feedstock and Phase L name batched.
- **AC8 — Gates.** `pyforge-atlas-test`, `kedro-catalog-check`, the coverage gate, `lint-types` (and mypy in
  `pyforge-foundry-full`), `flag-gate-check`; governing Specs reconciled and stamped scoped.

## Verification

- Unit, from the repo root: `src/shared/packages/pyforge-atlas/tests/unit/pipelines/vcs_health/test_universe_batches.py`.
- **Live, recorded 2026-10-18:** `batches_from_universe` over a 2026-10-18 data root (34,666 enumerated packages, the
  cf-graph frame of that day with Story 34.7's about URLs), against legacy `cf_atlas.db` (`v_actionable_packages`,
  33,841 packages):
  - **Phase K:** 26,983 GitHub upstreams (22,445 distinct repos), 411 GitLab, 31 Codeberg. Legacy derives 26,272
    packages (GitHub 25,846, GitLab 400, Codeberg 26): 26,247 are batched here (99.90%), and 26,193 of those name the
    same repo (99.79%). 1,178 packages are batched here only.
  - **Phase N:** 29,395 feedstocks; all 28,684 of legacy's are among them.
  - **Phase L:** npm 211 (legacy 198, all covered), rubygems 165 (165), crates 10 (10), Maven 3 (2); cran, cpan,
    luarocks and nuget 0, as legacy.
  - The 25 legacy-only packages have no repo URL in today's recipes (astroid, gidgethub and formulae now name only
    their PyPI page; libsqlite names sqlite.org); legacy still holds the GitHub URLs an earlier cf-graph gave.

## Boundaries & Constraints

**Never:** a network call in the batch builder or a trigger node; the identity batch dropped with the flag off.

**Residual risk:**
- **The GitHub store asks for 22,445 repos with the flag on.** It still sends only under the switch (Story 35.1), so
  an unattended run sends nothing; a credentialed run takes about 225 GraphQL batches until Story 35.3 reshapes the
  query.
- **Archived feedstocks are batched** (the deviation in Approach 1): 711 feedstocks more than legacy's Phase N.

## I/O & Edge-Case Matrix

| Situation | Before | After (flag on) |
|---|---|---|
| A package outside the OpenTeams subset with a GitHub repo URL | never fetched | batched |
| `airflow-with-amazon`, attributed to the airflow feedstock but not one of its anchors | — | the feedstock's repo |
| A GitLab repo under subgroups | — | the whole project path |
| A recipe sourced from npm or Maven Central | — | its registry name |
| Flag off | identity batch | identity batch (unchanged) |

</intent-contract>

## Binding

- Parent Spec capability: `spec-pyforge-atlas` CAP-65 (FR-73), a feature.
- Dream: `docs/dreams/pyforge-atlas.md` § *Realization log*, 2026-10-18 (atlas fills its own data).
- Epic 35 / Story 35.2 in `planning-artifacts/epics.md`.

## Spec Change Log

- 2026-10-18: written with the implementation (branch `atlas-35-2-universe-batches`, cut from `main` at `9b35deafc0`
  and stacked on Stories 35.1 and 34.7, which were in review).
