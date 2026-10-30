<!-- A marketplace skill contribution (docs/foundry/marketplace/; its README's § Contribute says how to apply this template). -->

## Lane

- [ ] `instructions-only`
- [ ] `code-backed`

The two lanes are defined in the README's § Index schema, **Lanes** (`docs/foundry/marketplace/README.md`).

## Listing

- [ ] `skills/<scope>/<slug>/listing.yaml` matches the `index.yaml` row
- [ ] Row fields: `id`, `kind`, `scope`, `slug`, `name`, `title`, `description`, `version`, `tier`, `trust_tier`, `source`, `jobs`, `path`, `lane`
- [ ] `kind` is `skill`, `module`, `agent`, or `bundle`
- [ ] `scope` and `slug` are lower-case letters, digits and hyphens, matched whole (no surrounding whitespace, no trailing newline; `id`, `path`, `kind`, `trust_tier`, `source` and `name` are compared whole too); `id` is `<scope>/<slug>`; `path` is `skills/<scope>/<slug>`, a folder inside this tree with no symlink at any level, with its `SKILL.md`; `<scope>-<slug>` is not `pages-site`
- [ ] `tier` maps onto `trust_tier`: `community` → `unverified`, `estate-reviewed` → `community-reviewed`, `bmad-certified` → `bmad-certified`
- [ ] `trust_tier` is `unverified`, `community-reviewed`, or `bmad-certified`
- [ ] `source` names the producer (`estate-listings` until a second source is reviewed)
- [ ] `lane` matches `contribution_lane` when both are set, and the packages under `requires` match the lane ticked above (each with a `name` and a bool `published`)
- [ ] `docs.steps` is a file inside the folder (`steps.md`); `docs.card` is `skills/<scope>/<slug>.html`; `verified_at` is a quoted `YYYY-MM-DD` or `null`
- [ ] A non-skill row's card name, its `slug` or its `name` when it has no `slug`, is lower-case letters, digits and hyphens
- [ ] Every folder under `skills/<scope>/` is a row of `index.yaml`
- [ ] The `id`, the card path and the `<scope>-<slug>` plugin name repeat no other row's
- [ ] `SKILL.md` opens with YAML frontmatter on line 1 whose `name` is exactly `<scope>-<slug>`
- [ ] `related`, when present, is a list of strings; an entry `@<scope>/<slug>` is spelled whole and names a skill row of the index (anything else is text on the card)

## Folder

- [ ] `SKILL.md` uses only commands that exist, or marks an unpublished `pyforge-*` package
- [ ] The only published commands the skill asks a teammate to run are named in `steps.md` step 0 with their install source and verified version; the station commands stay behind the unpublished packages
- [ ] `steps.md` is readable without the station source open: an engine is named by its module (`pyforge.<station>.engines.<name>`), never by a source path, and "this repo" does not appear
- [ ] No `pixi run -e` and no path inside local-recipes
- [ ] Install targets named in the skill are `.agents/skills/` and `.claude/skills/`
- [ ] The folder keeps to the folder rule in the README's § Install

## Generated site

- [ ] `site/`, `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json` were regenerated with `pyforge.steward.marketplace_pages` on (dev) and match `index.yaml` file for file
- [ ] The regenerated card shows what the README's § Regenerate the site says a card shows
- [ ] No sample checksum, example host, or paper-card command was copied into the listing

## Not in this pull request

- [ ] No new GitHub repository
- [ ] No change to `registry/estate.yaml` unless a module row is the listing
- [ ] No change to `CatalogEngine.render` or the v1 catalog manifests under `src/shared/packages/pyforge-steward/catalog/` (its `.claude-plugin/marketplace.json` and `.agents/plugins/marketplace.json`; this tree's two are regenerated above)
- [ ] No upload (`twine upload`, `pixi upload`, feedstock, or upstream PR)
