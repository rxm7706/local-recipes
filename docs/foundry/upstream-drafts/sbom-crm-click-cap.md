## Title

Lift conda-recipe-manager click upper bound so click 8.5.x resolves with mcp (crm 0.10.6)

## Body

conda-recipe-manager **0.10.6** (seen in this estate's lock) caps `click` at `<=8.4.1` in both the upstream `conda/conda-recipe-manager` project and `conda-forge/conda-recipe-manager-feedstock`, while PyForge's mcp stack needs `click >=8.4.2`. Latest click on conda-forge is **8.5.0** (`conda-forge/click-feedstock`). Feedstock PR **#44** ("Modify click dependency to match source") was closed **unmerged** on 2026-09-01; PR **#46** (merged 2026-09-03) widened the range but still caps `click >=8.2.1,<=8.4.1` in `recipe/meta.yaml:29` (v0 recipe, feedstock 3c6421e854). No open issue currently tracks lifting the upper bound for 8.5.x.

## Reproduce or evidence

- `docs/foundry/sbom-gaps.md:12` — `feature:crm` upstream
- `pixi.toml:1114-1119` — SBOM gap comment (crm click vs mcp)
- Feedstock: `conda-forge/conda-recipe-manager-feedstock` PR #44 closed unmerged; PR #46 merged with `click <=8.4.1`
- Latest click: `conda-forge/click-feedstock` `recipe/recipe.yaml` — 8.5.0
- `pixi.lock` — click 8.4.1 in `grayskull` / `local-recipes` (crm 0.10.6); 8.5.0 elsewhere
- Stale in-repo comments at `pixi.toml:102`, `:2120`, `:2152`, `:2203`, `:2220-2223`, `:2446` still cite `click==8.2.1` and #44 as "the unpin PR"

## Local workaround

Do not compose `crm` / feedrattler into `pyforge-foundry-full`; grayskull resolves crm to 0.5.0 without the click cap. Documented in `docs/foundry/sbom-gaps.md` and `docs/foundry/upstream-todos.yaml`.

## What resolution unblocks here

Re-disposition or promote `feature:crm` after upstream allows `click` 8.5.x (unpinned or `<9`) so mcp and crm co-resolve in the laptop SBOM.
