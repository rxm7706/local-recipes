# BMAD marketplace skeleton

This tree is the reset marketplace (steward Epic 109, CAP-171). It stays in
this repository so it can be copied to an internal GitHub when the operator
confirms that repository. `catalog.yaml`'s `dedicated_repo` stays null until
that confirm. Nothing here creates a GitHub repository.

## Layout

```
index.yaml                         listings, schema pyforge.bmad-marketplace/v1
skills/<scope>/<slug>/SKILL.md     the skill folder a teammate copies
skills/<scope>/<slug>/steps.md     the human steps for that skill
site/index.html                    static index, generated
site/listings.json                 the same listings, generated
site/skills/<scope>/<slug>.html    one skill card, generated
templates/SKILL.md                 the folder shape for a new skill
.github/PULL_REQUEST_TEMPLATE.md   the contribution PR shape
MANUAL-CHECKLIST.md                Round 0 desk test and Wizard-of-Oz pilot
```

`index.yaml` declares `compatible_with: registry/estate.yaml`. An empty
`modules:` list is zero module listings. A module row maps through
`listing_from_estate_module` in `pyforge.steward.marketplace_pages`. Trust
tier names are the v1 names (`unverified`, `community-reviewed`,
`bmad-certified`).

## Install

A skill is the folder under `skills/<scope>/<slug>/`. Copy it into both
`.agents/skills/<name>/` and `.claude/skills/<name>/`. Per-tool marketplace
manifests are not required. The v1 `.claude-plugin/marketplace.json` and
`.agents/plugins/marketplace.json` beside this tree are the catalog engine's
outputs. This skeleton does not rewrite them.

`pyforge-mason`, `pyforge-warden`, and `pyforge-core` were not on PyPI,
conda-forge, or SelfExplainML on 2026-10-21. Each pilot skill says so in
`steps.md`.

## Regenerate the site

Regeneration reads `pyforge.steward.marketplace_pages`. Dev is on. Staging
and production are off. While the flag is off, `write_site` writes nothing
and the committed HTML stays.

From the repository root, with `PYFORGE_ENVIRONMENT` unset or `dev`:

```bash
pixi run --frozen -e pyforge-steward python -c "
from pathlib import Path
from pyforge.steward.marketplace_pages import write_site_from_index
root = Path('src/shared/packages/pyforge-steward/catalog/marketplace')
write_site_from_index(root / 'index.yaml', root / 'site')
"
```

`CatalogEngine.render` is a different command. Do not use it to refresh
`site/`.
