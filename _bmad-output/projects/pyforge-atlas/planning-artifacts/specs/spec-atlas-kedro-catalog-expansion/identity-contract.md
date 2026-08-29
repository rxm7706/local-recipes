# Identity contract — Phase D in `upstream_discovery`

Companion to `SPEC.md`. Supersedes Epic 17's "purl-associator stays in quartet"
constraint (dated memlog entry required in inventory spec on Story 21.7).

## Source datasets

| Dataset | Endpoint | Credential |
|---------|----------|------------|
| `purl_associator_mappings_raw` | `https://prefix-dev.github.io/purl-associator/mappings-index.json` (+ shards) | none |
| `openteams_project_1_board_raw` | GitHub GraphQL project V2 #1, org `OpenTeams-WFT-CDO` | `gh` / token |
| `discovery_staged_recipes_prs_raw` | `conda-forge/staged-recipes` PR API | `gh` |
| Local recipes overlay | filesystem `recipes/` | none (repo-local) |

Associator canonical payload: [prefix-dev/purl-associator](https://github.com/prefix-dev/purl-associator)
Pages deploy (`web/public/mappings.json` / index + shards). Index required at
bootstrap; shards fetched on demand for `alternative_purls` and `cpes`.

## Derived outputs

| Output | Description |
|--------|-------------|
| `identity_packages_primary` | One row per inventory-universe package + board-only extras |
| `identity_export_parquet` | GIST_SCHEMA-shaped export (ranking columns empty until publish merge) |

## Join semantics (parity with `..._openteams_identity.py`)

1. Universe = `CDO-ENT-JFROG` ∪ `CDO-ENT-CONDA` from catalog-derived inventory Parquet.
2. For each inventory row: `lookup_assoc(name, packages)` with PEP 503 keys and
   `-`/`.`/`_` alias fallbacks.
3. Hit → `from_assoc` (`identity_source=purl-associator`).
4. Miss → `from_inventory` (`PyPI_PURL` + `git_purl(Source_Repository_URL)`).
5. Board packaging issues not in inventory → `from_board_only`.
6. Overlays: `attach_packaging_urls` (feedstock, metadata, staged PR, local URL).
7. `overlay_live_local` for `Local_Build_Status` from `recipe.yaml` CFE stamp.

## Export columns (identity tab minimum)

`Core_Python_Package_Name`, `OpenTeams_Title`, `identity_source`,
`associator_key`, `associator_status`, `primary_purl`, `primary_type`,
`alternative_purls`, `cpes`, `conda_purl`, `source_repository_url`,
`OpenTeams_Issue_URL`, `Conda-Forge_FeedStock_URL`, `Conda-Forge_Metadata_URL`,
`Staged_Recipes_PR_URL`, `Local_Recipes_URL`, `Local_Build_Status`,
`Verification_Timestamp_UTC`.

Ranking columns (`P`, `Rank`, `Score`, `Work`, JFROG fields) merged at gist
publish from `priority.py` through Epic 21; **Epic 23.5** `identity_complete_export.parquet`
includes them — gist actuator reads Parquet only.

## Gist publish (export target)

- Atlas writes `identity_export_parquet` (Epic 21) → `identity_complete_export.parquet` (Epic 23.5).
- Inventory `--gist-only` reads complete export (post-23.6), edits pinned gist in place
  (`OPENTEAMS_IDENTITY_GIST_ID` never in git).
- Files: `mgmt-wf-python-modernization-identity.md`,
  `mgmt-wf-python-modernization-dashboards.md`.

## Parity test corpus

Fixture set must cover: associator hit, inventory-derived fallback, board-only
extra, unmapped none, conda_purl only when `CondaForge_Verified`, overlay
URLs from feedstock map + staged PR + local recipes.
