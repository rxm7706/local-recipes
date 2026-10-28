# BMAD marketplace

Skills, modules, and agents. Find, install, create, and publish. This tree is
the reset marketplace (steward Epic 109, CAP-171); the product brief is
`_bmad-output/projects/pyforge-steward/planning-artifacts/briefs/brief-bmad-marketplace-reset-2026-10-21/brief.md`.

It lives at `docs/foundry/marketplace/` because that directory is the foundry
target for published indexes (`frames/` and `browse.yaml` are its neighbours).
The portable skill folders are listings in that index, not station skills
under `skills/{stations,personas,domain}/`.

Decision 2026-10-21: this monorepo hosts and publishes the marketplace. There
is no separate marketplace repository. Teammates use an internal mirror of
local-recipes. `catalog.yaml`'s `edit_store.mirrors` is a list of
`{host, repo}` and starts empty. The open question is which internal GitHub
or GHES mirror of local-recipes, and whether mirroring the full repository is
allowed at work.

Foundry rebuilds this tree at cutover. Nothing moves, and nothing changes at
the `cutover_root` flip.

## Install

A skill is the folder under `skills/<scope>/<slug>/`. Copy it into both
`.agents/skills/<scope>-<slug>/` and `.claude/skills/<scope>-<slug>/`.

| Tool | Reads the skill from |
|---|---|
| Claude Code | `.claude/skills/` (documented); `.agents/skills/` uncertain |
| Devin (Cognition AI) | `.agents/skills/` (documented); `.claude/skills/` not listed |
| Cursor | both |
| GitHub Copilot in VS Code | both |
| Google Gemini CLI | `.agents/skills/` |
| Codex | `.agents/skills/` |
| No AI tool | the card at `/marketplace/` and `steps.md` |

The table is the 2026-10-20 tool matrix
(`planning-artifacts/design-thinking-bmad-marketplace-2026-10-20/tool-support-matrix.md`).
A teammate with no AI tool uses the card and `steps.md`.

The rolling `pages-site` release carries one `<scope>-<slug>.zip` per skill,
with `<scope>-<slug>.zip.sha256` beside it, while the marketplace flag is on
for that deploy. Each zip holds the `<scope>-<slug>/` folder, so
`unzip <scope>-<slug>.zip -d .claude/skills/` lands it in place; it carries
`SKILL.md`, `steps.md`, `listing.yaml` and `references/` and nothing else.

`.claude-plugin/marketplace.json` is a discovery pointer for each listing:
Round 0 of `MANUAL-CHECKLIST.md` records whether `/plugin install` exposes
the skill. Until it does, the folder copy above is the install.

## Layout

```
index.yaml                         concatenation of the listing rows, schema pyforge.bmad-marketplace/v1, index_version 1
skills/<scope>/<slug>/listing.yaml one row, the P2 field set with no sample hosts
skills/<scope>/<slug>/SKILL.md     the skill folder a teammate copies
skills/<scope>/<slug>/steps.md     the human runbook; the paper card's sample commands are not this file
skills/<scope>/<slug>/references/  optional; the only subdirectory that ships
.claude-plugin/marketplace.json    the Claude marketplace file for a github or git source (plugin entries are relative paths), generated
site/index.html                    static index, generated
site/listings.json                 the same listings, generated
site/marketplace.json              the Pages URL form of the marketplace file (plugin entries are git-subdir), generated
site/skills/<scope>/<slug>.html    one skill card, generated
templates/SKILL.md                 the folder shape for a new skill
templates/steps.md                 the runbook shape for a new skill
MANUAL-CHECKLIST.md                Round 0 desk test and the Wizard-of-Oz pilot
```

The contribution PR template is `.github/PULL_REQUEST_TEMPLATE/marketplace-skill.md`
at the repository root, because GitHub reads templates from there and not from
this tree; open the pull request with `?template=marketplace-skill.md` on the
compare URL, or paste its body by hand.

The v1 catalog manifests stay at
`src/shared/packages/pyforge-steward/catalog/.claude-plugin/marketplace.json`
and `.agents/plugins/marketplace.json`. `CatalogEngine.render` does not write
this tree. Per-tool skill-directory formats are not generated.

## Index schema

`index.yaml` declares `compatible_with: registry/estate.yaml`. An empty
`modules:` list is zero module listings. A module row maps through
`listing_from_estate_module` in `pyforge.steward.marketplace_pages`. bmp
`tier` maps onto the v1 names: `community` → `unverified`,
`estate-reviewed` → `community-reviewed`, `bmad-certified` →
`bmad-certified` (the PR template's §Listing carries the same mapping). The
three pilots are `community` / `unverified` (no review record) and
`code-backed` (each requires a package). An instructions-only skill has no
package. A card renders `steps.md`, names both install directories and every
unpublished package, and shows the listing's `verified_at` date or "never
verified".

The listing rules `validate_listing` enforces: `scope`, `slug` and a module's
`name` are lower-case letters, digits and hyphens; a skill's `id` is
`<scope>/<slug>` and its `path` is `skills/<scope>/<slug>`, a folder that
exists with its `SKILL.md`; every skill folder is a row; ids, cards and
`<scope>-<slug>` plugin names are unique; each package under `requires` has a
`name` and a bool `published`, and the packages match the lane; install
targets are `.agents/skills`, `.claude/skills` or one folder under either;
`docs.steps` stays inside the folder; `docs.card` is `skills/<scope>/<slug>.html`;
`verified_at` is a quoted `YYYY-MM-DD` or `null`.

## Contribute

Copy `templates/SKILL.md` and `templates/steps.md` into
`skills/<scope>/<slug>/`, write the `listing.yaml` row and append it to
`index.yaml`, regenerate the site (below), and open a pull request with
`?template=marketplace-skill.md`. The template's first section is the lane:
`instructions-only` (markdown and the index row, no package) or
`code-backed` (the listing names the package the skill calls, published or
flagged unpublished). `MANUAL-CHECKLIST.md` is the Round 0 desk test and the
Wizard-of-Oz pilot a contribution is read against; `bmp new` and
`@bmp/skillify` are not built, so a person helps shape the folder.

## Regenerate the site

Regeneration reads `pyforge.steward.marketplace_pages`. Dev is on. Staging
and production are off. A Pages deploy resolves `dev` (`pages.yml` sets no
`PYFORGE_ENVIRONMENT`, and `python -m pyforge.steward.marketplace_pages
--flag-env` hands the build `PYFORGE_MARKETPLACE_PAGES`). While the flag is
off, `write_site` writes nothing, the committed `site/` stays in git, and the
Pages build mounts no `/marketplace/`: the URL is absent, not stale. On, the
build mounts `site/` plus the shipped files of each skill folder at
`/marketplace/`, and `pages-check` holds the mount to its manifest.

From the repository root (the flag tree is `src/platform/config/flags.json`;
run elsewhere, `write_site` refuses naming the missing tree), with
`PYFORGE_ENVIRONMENT` unset or `dev`:

```bash
pixi run --frozen -e pyforge-steward python -c "
from pathlib import Path
from pyforge.steward.marketplace_pages import write_plugin_manifest, write_site_from_index
root = Path('docs/foundry/marketplace')
write_site_from_index(root / 'index.yaml', root / 'site')
write_plugin_manifest(root / 'index.yaml', root / '.claude-plugin' / 'marketplace.json')
"
```

`site/` is replaced by a fresh tree on every render, so a card whose listing
was dropped or renamed does not survive; the test compares the committed tree
to the render file for file. `CatalogEngine.render` is a different command.
Do not use it to refresh `site/`.

## Not built yet

- `bmp install` is Story 109.4 and is not this tree; the pages are a reading
  surface, not an install button.
- Per-tool skill-directory formats and adapters are not generated.
- GitHub release and Artifactory conda and pip are the sources once a listing
  is published. These three are not published, so the card has no download
  URL of its own; the rolling `pages-site` zips above are the only artifact.
- `pyforge-mason`, `pyforge-warden`, and `pyforge-core` were not on PyPI,
  conda-forge, or SelfExplainML on 2026-10-21. Each pilot skill says so in
  `steps.md`.
- Which internal mirror of local-recipes teammates use (`edit_store.mirrors`).
