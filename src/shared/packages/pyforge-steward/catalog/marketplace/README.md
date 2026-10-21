# BMAD marketplace skeleton

This tree is the reset marketplace (steward Epic 109, CAP-171). It stays in
this repository so it can be copied to an internal GitHub when the operator
confirms that repository. `catalog.yaml`'s `dedicated_repo` stays null until
that confirm. Nothing here creates a GitHub repository.

## Layout

```
index.yaml                         concatenation of the listing rows, schema pyforge.bmad-marketplace/v1, index_version 1
skills/<scope>/<slug>/listing.yaml one row, the P2 field set with no sample hosts
skills/<scope>/<slug>/SKILL.md     the skill folder a teammate copies
skills/<scope>/<slug>/steps.md     the human runbook; the paper card's sample commands are not this file
site/index.html                    static index, generated
site/listings.json                 the same listings, generated
site/skills/<scope>/<slug>.html    one skill card, generated
templates/SKILL.md                 the folder shape for a new skill
.github/PULL_REQUEST_TEMPLATE.md   the contribution PR shape
MANUAL-CHECKLIST.md                Round 0 desk test and Wizard-of-Oz pilot
```

`index.yaml` declares `compatible_with: registry/estate.yaml`. An empty
`modules:` list is zero module listings. A module row maps through
`listing_from_estate_module` in `pyforge.steward.marketplace_pages`. bmp
`tier` maps onto the v1 names: `community` → `unverified`,
`estate-reviewed` → `community-reviewed`, `bmad-certified` →
`bmad-certified`. The three pilots are `community` / `unverified` (no
review record) and `code-backed` (each requires a package). An
instructions-only skill has no package. A card renders `steps.md`.

## Install

A skill is the folder under `skills/<scope>/<slug>/`. Copy it into both
`.agents/skills/<scope>-<slug>/` and `.claude/skills/<scope>-<slug>/`.
The 2026-10-20 tool matrix documents Claude Code's project skill path as
`.claude/skills/` and Devin's as `.agents/skills/<name>/SKILL.md`. It marks
Claude Code reading `.agents/skills/` as uncertain and does not list
`.claude/skills/` for Devin. Cursor and GitHub Copilot in VS Code read both.
Google Gemini CLI and Codex read `.agents/skills/`. A teammate with no AI
tool uses the card and `steps.md`. No other skill-directory format is written.
GitHub release and Artifactory conda and pip are the sources once a
listing is published. These three are not published, so the card has no
URL and no checksum. `bmp install` is Story 109.4 and is not this tree.
Per-tool marketplace
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
