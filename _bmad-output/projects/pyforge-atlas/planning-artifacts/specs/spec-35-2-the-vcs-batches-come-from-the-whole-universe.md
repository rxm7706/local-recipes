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
review_loop_iteration: 3
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
   - As legacy's actionable set: the enumeration is the active packages (the current repodata), and a package
     attributed to a feedstock the cf-graph marks archived is left out, with that feedstock (review round 1).
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
  - *Recomputed 2026-10-19 with archived feedstocks left out (review round 1); the first figures, with them, were
    26,983 GitHub upstreams and 29,395 feedstocks. These figures predate round 2's archived-anchor filter; legacy
    batched none of the packages that filter drops, so the legacy comparison holds.*
  - **Phase K:** 26,511 GitHub upstreams (22,102 distinct repos, ignoring case), 405 GitLab, 31 Codeberg. Of legacy's
    26,306 `upstream_versions` rows for those hosts, 26,245 are batched here (99.77%), and 26,196 of those name the
    same repo (99.81%).
  - **Phase N:** 28,684 feedstocks, exactly legacy's actionable 28,684.
  - **Phase L:** npm 211 (legacy 198, all covered), rubygems 165 (165), crates 10 (10), Maven 3 (2); cran, cpan,
    luarocks and nuget 0, as legacy.
  - Of legacy's 26,306 rows, 61 are not batched here: 25 packages have no repo URL in today's recipes (astroid,
    gidgethub and formulae now name only their PyPI page; libsqlite names sqlite.org), and legacy still holds the GitHub
    URLs an earlier cf-graph gave; the other 36 are `upstream_versions` rows outside legacy's own actionable view.
- **Live, recomputed 2026-10-21** (review round 2: archived anchors left out too) over a fresh public data root built
  that day by `pyforge atlas run` (34,720 enumerated packages, 359,036 cf-graph rows, 1,599 archived feedstocks):
  26,480 GitHub upstreams (22,093 repos ignoring case, 221 GraphQL batches of 100), 404 GitLab, 31 Codeberg; 28,734
  feedstocks; npm 211, rubygems 165, crates 10, Maven 3; cran, cpan, luarocks and nuget 0.

## Boundaries & Constraints

**Never:** a network call in the batch builder or a trigger node; the identity batch dropped with the flag off.

**Residual risk:**
- **The GitHub store asks for 22,100 repos with the flag on** (2026-10-21; 22,093 ignoring case, which Story 35.3's
  dedupe applies). It still sends only under the switch (Story 35.1), so an unattended run sends nothing; a
  credentialed run takes 221 GraphQL batches until Story 35.3 reshapes the query.
- **The host and registry stores fetch the universe unattended with the flag on.** The flag is on in dev and they need
  no switch (public hosts and registries answer anonymously), so a plain dev run asks GitLab for 404 projects (0
  before), Codeberg for 31 (0), npm for 211 names (8) and rubygems for 165 (0).
- **Until Story 35.3 lands, the GitHub store merges on `feedstock_name`** (the repo name): 262 names are shared across
  owners at universe scale (2026-10-21: repo names as written, owners compared ignoring case). Story 35.3 keys the
  store on `(kind, key)`.
- **With the flag on, identity-only targets drop:** 14 GitHub repos and the npm names `bmad-method`, `mailpit` and
  `@cyclonedx/cdxgen` that the identity batch named and the universe does not (by design, AC6).
- **The host stores' keys change** from identity's PEP 503 names to raw conda names, so after the flip old and new rows
  sit side by side until the old ones age out.

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

- 2026-10-21, review round 3 (FAIL), fixed:
  - B3: the new batch test had taken `test_the_flag_is_read_at_each_save`'s `@flag_states` decorator, so that test
    failed; each has its own again.
  - Should-fix: a test pins that a live attribution outranks an archived first anchor (the order swap changed 297
    packages on 2026-10-21's data), and the first-attribution test now asserts on the npm batch, which keep="last"
    changes.
  - Nits: tests for the first anchor row being the one read (a dependency row never is) and for a CRAN page among the
    about URLs; the spec says which count ignores case and that the earlier figures predate the anchor filter.
- 2026-10-21, review round 2 (FAIL), fixed:
  - B2: a `flag_states` test gives the GitHub store distinct identity and universe repos and pins which batch each
    state reads (the "flag off reads the universe" mutant now fails it).
  - SF7: a test pins the three trigger nodes' inputs, so dropping `core_feedstock_attribution` fails.
  - SF2 gap: a package with no attribution row takes its first anchor's feedstock, and is left out when that feedstock
    is archived (85 packages on 2026-10-19, e.g. `dagster_graphql`, `argparse`); the first attribution of a package
    decides, as in `package_recipe_fields`.
  - SF3: the residual figures recomputed on 2026-10-21's data; the 61 legacy-only rows explained; the unattended
    host and registry fetch with the flag on stated.
  - Nits: tests for a missing `feedstock_archived` value and for cran, cpan and luarocks URLs staying unbatched.
- 2026-10-19, review round 1 (FAIL), fixed:
  - B1: the registry store's flag-off path is tested in both states (`flag_states`).
  - Should-fix: archived feedstocks and their packages are left out, as legacy's actionable view does (the batches
    recomputed above); tests for a non-VCS URL falling through to the next, an archived feedstock, a feedstock asked
    only for an enumerated package; the residual risks the reviewer named are stated.
  - Nits: tests for a missing URL, a Maven about URL and the new request fields' serialization. Not changed: the
    registry batch keeps one name per (registry, package), as legacy has no package with two.
- 2026-10-18: written with the implementation (branch `atlas-35-2-universe-batches`, cut from `main` at `9b35deafc0`
  and stacked on Stories 35.1 and 34.7, which were in review).
