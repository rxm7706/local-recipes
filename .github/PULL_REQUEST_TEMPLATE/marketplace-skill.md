<!-- A marketplace skill contribution (docs/foundry/marketplace/; its README's § Contribute says how to apply this template). -->

## Lane

- [ ] `instructions-only`: the listing names no package; the diff is markdown and the index row
- [ ] `code-backed`: the listing names the package the skill calls, and that package is either published or flagged `published: false`

## Listing

- [ ] `skills/<scope>/<slug>/listing.yaml` matches the `index.yaml` row
- [ ] Row fields: `id`, `kind`, `scope`, `slug`, `name`, `title`, `description`, `version`, `tier`, `trust_tier`, `source`, `jobs`, `path`, `lane`
- [ ] `kind` is `skill`, `module`, `agent`, or `bundle`
- [ ] `scope` and `slug` are lower-case letters, digits and hyphens; `id` is `<scope>/<slug>`; `path` is `skills/<scope>/<slug>` and that folder exists with its `SKILL.md`
- [ ] `tier` maps onto `trust_tier`: `community` → `unverified`, `estate-reviewed` → `community-reviewed`, `bmad-certified` → `bmad-certified`
- [ ] `trust_tier` is `unverified`, `community-reviewed`, or `bmad-certified`
- [ ] `source` names the producer (`estate-listings` until a second source is reviewed)
- [ ] `lane` matches `contribution_lane` when both are set, and the packages under `requires` match the lane ticked above (each with a `name` and a bool `published`)
- [ ] `docs.steps` is a file inside the folder (`steps.md`); `docs.card` is `skills/<scope>/<slug>.html`; `verified_at` is a quoted `YYYY-MM-DD` or `null`

## Folder

- [ ] `SKILL.md` uses only commands that exist, or marks an unpublished `pyforge-*` package
- [ ] The only published commands the skill asks a teammate to run are named in `steps.md` step 0 with their install source and verified version; the station commands stay behind the unpublished packages
- [ ] `steps.md` is readable without the station source open: an engine is named by its module (`pyforge.<station>.engines.<name>`), never by a source path, and "this repo" does not appear
- [ ] No `pixi run -e` and no path inside local-recipes
- [ ] Install targets named in the skill are `.agents/skills/` and `.claude/skills/`
- [ ] The folder keeps to the folder rule in the README's § Install (`validate_listing` refuses each breach; the mount and the release zip ship exactly that set)

## Generated site

- [ ] `site/`, `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json` were regenerated with `pyforge.steward.marketplace_pages` on (dev) and match `index.yaml` file for file
- [ ] The card renders `steps.md`, names every requires package whose `published` is false, and shows the verified date or "never verified"
- [ ] No sample checksum, example host, or paper-card command was copied into the listing

## Not in this pull request

- [ ] No new GitHub repository
- [ ] No change to `registry/estate.yaml` unless a module row is the listing
- [ ] No change to `CatalogEngine.render` or the v1 catalog manifests under `src/shared/packages/pyforge-steward/catalog/` (its `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`; this tree's two are regenerated above)
- [ ] No upload (`twine upload`, `pixi upload`, feedstock, or upstream PR)
