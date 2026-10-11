## Title

conda-recipe-manager IndexError on valid indented comments (crm 0.10.6, surfaced by conda-smithy lint)

## Body

conda-recipe-manager **0.10.6** crashes in `_construct_parse_tree` with `IndexError` when a recipe has a comment indented deeper than its sibling keys — conda-smithy lint reports ParsingException while rattler-build may still build. Example: `recipes/mem0ai/recipe.yaml` comment deeper than keys.

## Reproduce or evidence

- `.claude/skills/conda-forge-expert/SKILL.md:3871-3881` — G93 and v8.99.1 addendum
- `.claude/skills/conda-forge-expert/CHANGELOG.md` v8.99.1
- mason Story 25.2 — refresh-wave / parse crash class

## Local workaround

Re-indent comments per G93 (column-0 only inside blocks, or move to tail comment block); avoid crm parse on affected files until fixed upstream.

## What resolution unblocks here

Retire when crm parser accepts the indentation pattern or estate upgrades to a release containing the fix.
