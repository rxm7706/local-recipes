# BMAD marketplace skeleton

This tree is the reset marketplace (steward Epic 109, CAP-171). It lives at
`docs/foundry/marketplace/` because that directory is the foundry target for
published indexes (`frames/` and `browse.yaml` are its neighbours). The
portable skill folders are listings in that index, not station skills under
`skills/{stations,personas,domain}/`. Decision 2026-10-21: this monorepo
hosts and publishes the marketplace. There is no separate marketplace
repository. Teammates use an internal mirror of local-recipes.
`catalog.yaml`'s `edit_store.mirrors` is a list of `{host, repo}` and starts
empty. The open question is which internal GitHub or GHES mirror of
local-recipes, and whether mirroring the full repository is allowed at work.
Foundry rebuilds this tree at cutover. Nothing moves, and nothing changes
at the `cutover_root` flip.

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
Per-tool skill-directory formats are not generated. This tree's
`.claude-plugin/marketplace.json` is the Claude marketplace file (`github`
and `git` sources; plugin entries are relative paths). `site/marketplace.json`
is the Pages URL form (plugin entries are `git-subdir`, because a `url`
marketplace source downloads only that file). The v1 catalog manifests stay
at `src/shared/packages/pyforge-steward/catalog/.claude-plugin/marketplace.json`
and `.agents/plugins/marketplace.json`. `CatalogEngine.render` does not write
this tree. Pages mounts `site/` at `/marketplace/` while
`pyforge.steward.marketplace_pages` is on.

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
from pyforge.steward.marketplace_pages import write_plugin_manifest, write_site_from_index
root = Path('docs/foundry/marketplace')
write_site_from_index(root / 'index.yaml', root / 'site')
write_plugin_manifest(root / 'index.yaml', root / '.claude-plugin' / 'marketplace.json')
"
```

`CatalogEngine.render` is a different command. Do not use it to refresh
`site/`.
