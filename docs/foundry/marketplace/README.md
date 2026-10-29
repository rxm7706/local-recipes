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
`{host, repo}` and starts empty.

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

<!-- The folder rule's one home: the PR template, the how-to, the cards and the validator point here. -->
**The folder rule.** A skill folder holds `SKILL.md`, `steps.md`,
`listing.yaml` and text files (`.md`, `.txt`, `.yaml`, `.yml`, `.json`, in
any letter case) under `references/`, and nothing else: regular files only
(no symlink, no dot entry), no file over 1 MiB, the folder under 4 MiB. Each
layer refuses what it can see: `validate_listing` refuses every breach at
render, and the steward live lane runs it over this tree; the Pages mount
(`docs-site/src/lib/marketplace.ts`) ships only that set, fails the build on
a size cap, and `pages-check` reports a mounted file or folder over its cap;
the release zip step refuses a symlink, a cap breach or a non-text
`references/` file over the mount's output, as defence in depth.

The rolling `pages-site` release carries one `<scope>-<slug>.zip` per skill,
with `<scope>-<slug>.zip.sha256` beside it, while the marketplace flag is on
for that deploy. Each zip holds the `<scope>-<slug>/` folder with that set,
so `sha256sum -c <scope>-<slug>.zip.sha256 && unzip <scope>-<slug>.zip -d .claude/skills/`
checks and lands it in place. Every zip is built before the release is
touched; the previous deploy's per-skill assets of the `<scope>-<slug>.zip`
shape that are not in the new set are then deleted (a failed asset listing
fails the step), and the site zip and the new set go up in one upload, so a
renamed skill leaves no stale zip and no deploy leaves a new site beside
stale skill zips. `pages-site` is never a plugin name, so no skill zip can
carry the site asset's name.

`.claude-plugin/marketplace.json` (Claude Code) and `.agents/plugins/marketplace.json`
(Codex) are discovery pointers for each listing: Round 0 of
`MANUAL-CHECKLIST.md` has a row for each tool with a plugin install (Claude
Code, Codex) and records whether that install exposes the skill. Until it
does, the folder copy above is the install.

## Layout

```
index.yaml                         concatenation of the listing rows, schema pyforge.bmad-marketplace/v1, index_version 1
skills/<scope>/<slug>/listing.yaml one row, the P2 field set with no sample hosts
skills/<scope>/<slug>/SKILL.md     the skill folder a teammate copies
skills/<scope>/<slug>/steps.md     the human runbook; the paper card's sample commands are not this file
skills/<scope>/<slug>/references/  optional; the only subdirectory that ships
.claude-plugin/marketplace.json    the Claude marketplace file for a github or git source (plugin entries are relative paths), generated
.agents/plugins/marketplace.json   the Codex marketplace file (`codex plugin marketplace add <this directory>`), generated
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
this tree; § Contribute below says how to apply it.

The v1 catalog manifests stay at
`src/shared/packages/pyforge-steward/catalog/.claude-plugin/marketplace.json`
and `.agents/plugins/marketplace.json`; this tree's two manifests are
generated here, by `write_plugin_manifests`.

## Index schema

`index.yaml` declares `compatible_with: registry/estate.yaml`. An empty
`modules:` list is zero module listings. A module row maps through
`listing_from_estate_module` in `pyforge.steward.marketplace_pages`. bmp
`tier` maps onto the v1 names: `community` → `unverified`,
`estate-reviewed` → `community-reviewed`, `bmad-certified` →
`bmad-certified` (the PR template's §Listing carries the same mapping).

**Lanes.** `instructions-only`: the listing names no package; the diff is
markdown and the index row. `code-backed`: the listing names the package the
skill calls, each with `published: true` or `false`. A skill's lane is what
its packages say; a module's package is the module. The card names the
listing's lane and links here. The three pilots are `community` /
`unverified` (no review record) and `code-backed`.

The listing rules `validate_listing` enforces are the PR template's
§ Listing, one checkbox each (`.github/PULL_REQUEST_TEMPLATE/marketplace-skill.md`);
the folder rule is § Install above. In short: `scope`, `slug` and a module's
`name` are lower-case letters, digits and hyphens; a skill's `id` is
`<scope>/<slug>` and its `path` is `skills/<scope>/<slug>`, a folder that
exists with its `SKILL.md`; every skill folder is a row; ids, cards and
`<scope>-<slug>` plugin names are unique; a `related` entry of the form
`@<scope>/<slug>` names a listing.

## Contribute

Copy `templates/SKILL.md` and `templates/steps.md` into
`skills/<scope>/<slug>/`, write the `listing.yaml` row and append it to
`index.yaml`, regenerate the site and both manifests (below), and open a pull
request with the contribution template:

```bash
gh pr create --repo rxm7706/local-recipes --template marketplace-skill.md
```

(or `?template=marketplace-skill.md` on the web compare URL, or paste the
template's body by hand). Tick the lane in the template's first section.
`MANUAL-CHECKLIST.md` is the Round 0 desk test and the Wizard-of-Oz pilot a
contribution is read against; `bmp new` and `@bmp/skillify` are not built,
so a person helps shape the folder.

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
from pyforge.steward.marketplace_pages import write_plugin_manifests, write_site_from_index
root = Path('docs/foundry/marketplace')
write_site_from_index(root / 'index.yaml', root / 'site')
write_plugin_manifests(root / 'index.yaml')
"
```

`site/` is replaced by a fresh tree on every render, so a card whose listing
was dropped or renamed does not survive; `write_site` replaces a non-empty
directory only when every file and directory in it is one its own
`listings.json` (rows held to the slug grammar) accounts for, so a stray
file or directory beside the marker is refused, not deleted. The test
compares the committed tree to the render file for file.
`CatalogEngine.render` is a different command. Do not use it to refresh
`site/`.

A card renders `steps.md` (its own `#` title skipped, its steps as `<h3>`
under the card's one `Steps` heading), names both install directories and
every unpublished package, links the sibling cards under Related, and shows
the listing's `verified_at` date or "never verified". A relative link on a
skill's runbook, one whose target is `steps.md` or `references/x.md`, points
into the mounted folder beside the card, so it resolves on the Pages mount
and not in the checked-in `site/` tree, which has no folder beside the card
(Round 0 reads `site/index.html` and opens the folder by hand). The card's
links to this README, `MANUAL-CHECKLIST.md` and the tool matrix are
repository links; the mount rewrites them to the deploying host, as it
rewrites `marketplace.json`'s clone URL.

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
- Which internal GitHub or GHES mirror of local-recipes teammates use
  (`edit_store.mirrors`), and whether mirroring the full repository is
  allowed at work.
