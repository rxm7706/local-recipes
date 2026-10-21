## Listing

- [ ] `index.yaml` row: `id`, `kind`, `scope`, `slug`, `name`, `title`, `description`, `version`, `trust_tier`, `source`, `jobs`, `path`, `contribution_lane`
- [ ] `kind` is `skill`, `module`, or `agent`
- [ ] `trust_tier` is `unverified`, `community-reviewed`, or `bmad-certified`
- [ ] `source` names the producer (`estate-listings` until a second source is reviewed)
- [ ] For a skill, `path` is `skills/<scope>/<slug>` and that folder exists
- [ ] `contribution_lane` is `instructions-only` or `code-backed`

## Folder

- [ ] `SKILL.md` uses only commands that exist, or marks an unpublished `pyforge-*` package
- [ ] `steps.md` is readable without the station source open
- [ ] No `pixi run -e` and no path inside local-recipes
- [ ] Install targets named in the skill are `.agents/skills/` and `.claude/skills/`

## Generated site

- [ ] `site/` was regenerated with `pyforge.steward.marketplace_pages` on (dev) and matches `index.yaml`
- [ ] The card names every `requires.packages` entry whose `published` is false

## Lane

- [ ] Instructions-only: the diff is markdown and the index row
- [ ] Code-backed: the diff says which package the skill calls, and that package is either published or flagged unpublished

## Not in this pull request

- [ ] No new GitHub repository
- [ ] No change to `registry/estate.yaml` unless a module row is the listing
- [ ] No change to `CatalogEngine.render` or the committed `.claude-plugin` / `.agents` manifests
- [ ] No upload (`twine upload`, `pixi upload`, feedstock, or upstream PR)
