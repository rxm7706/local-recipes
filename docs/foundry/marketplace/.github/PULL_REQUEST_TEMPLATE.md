## Listing

- [ ] `skills/<scope>/<slug>/listing.yaml` matches the `index.yaml` row
- [ ] Row fields: `id`, `kind`, `scope`, `slug`, `name`, `title`, `description`, `version`, `tier`, `trust_tier`, `source`, `jobs`, `path`, `lane`
- [ ] `kind` is `skill`, `module`, `agent`, or `bundle`
- [ ] `tier` maps onto `trust_tier`: `community` → `unverified`, `estate-reviewed` → `community-reviewed`, `bmad-certified` → `bmad-certified`
- [ ] `trust_tier` is `unverified`, `community-reviewed`, or `bmad-certified`
- [ ] `source` names the producer (`estate-listings` until a second source is reviewed)
- [ ] For a skill, `path` is `skills/<scope>/<slug>` and that folder exists
- [ ] `lane` is `instructions-only` (no package) or `code-backed` (names a package), and it matches `contribution_lane` when both are set

## Folder

- [ ] `SKILL.md` uses only commands that exist, or marks an unpublished `pyforge-*` package
- [ ] `steps.md` is readable without the station source open
- [ ] No `pixi run -e` and no path inside local-recipes
- [ ] Install targets named in the skill are `.agents/skills/` and `.claude/skills/`

## Generated site

- [ ] `site/` was regenerated with `pyforge.steward.marketplace_pages` on (dev) and matches `index.yaml`
- [ ] The card renders `steps.md` and names every requires package whose `published` is false
- [ ] No sample checksum, example host, or paper-card command was copied into the listing

## Lane

- [ ] Instructions-only: the diff is markdown and the index row
- [ ] Code-backed: the diff says which package the skill calls, and that package is either published or flagged unpublished

## Not in this pull request

- [ ] No new GitHub repository
- [ ] No change to `registry/estate.yaml` unless a module row is the listing
- [ ] No change to `CatalogEngine.render` or the committed `.claude-plugin` / `.agents` manifests
- [ ] No upload (`twine upload`, `pixi upload`, feedstock, or upstream PR)
