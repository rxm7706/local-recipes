## Title

conda-recipe-manager v0→v1 conversion leaks SentinelType repr as YAML mapping key (exit 100)

## Body

When converting v0 `meta.yaml` to v1 `recipe.yaml`, conda-recipe-manager **0.10.6** can emit a mapping key like `<conda_recipe_manager.types.SentinelType object at 0x…>` instead of a real field name. The CLI exits **100** (not a normal validation error). conda-smithy then fails lint on the broken recipe.

## Reproduce or evidence

- `.claude/skills/conda-forge-expert/SKILL.md:4384` — G121
- `.claude/skills/conda-forge-expert/CHANGELOG.md` v8.98.0
- mason Stories 22.1 and 22.3 — twelve `recipe.yaml` files carried SentinelType keys; crm 0.10.6 exits 100

## Local workaround

Repair affected recipes by hand or avoid paths that trigger conversion until upstream fixes; track in CFE gotcha G121.

## What resolution unblocks here

Close or retire this registry item when upstream crm no longer leaks SentinelType keys (or estate pins a fixed release).
