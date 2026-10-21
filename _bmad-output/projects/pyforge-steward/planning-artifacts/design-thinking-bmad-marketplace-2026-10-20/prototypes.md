# Paper prototypes — sample, not a live session

`p1-cli-transcript.md`, `p2-index-schema.yaml`, `p2-index-schema.md`,
`p3-skill-card.html`, and `p4-wizard-of-oz-pilot.md` were named as paper
prototypes and were not mounted. Nothing below is a transcript. Commands
in a paper prototype are sample data. The pilot skills use the commands in
[research-notes.md](research-notes.md).

## P1 — teammate CLI

Proposed name `bmp`, sharing `CatalogEngine` with `steward catalog`.
Story 109.4. Not implemented here. No sample transcript is invented.

## P2 — index schema (adopted)

The listing document this tree writes is
`src/shared/packages/pyforge-steward/catalog/marketplace/index.yaml`.

- `schema: pyforge.bmad-marketplace/v1`
- `compatible_with: registry/estate.yaml`
- A listing has `id`, `kind` (`skill`, `module`, `agent`), `scope`, `slug`,
  `name`, `title`, `description`, `version`, `trust_tier`, `source`,
  `jobs`, `path`, `contribution_lane`, `install.targets`, and
  `requires.packages` (with `published: false` when the package 404s).
- A skill `path` is `skills/<scope>/<slug>`.
- An `estate.yaml` document with `modules:` maps through
  `listing_from_estate_module`. Empty `modules` is an empty list.

## P3 — skill card

The card is generated HTML, not a hand-built mock.
`site/skills/<scope>/<slug>.html` is `render_skill_card`. It names the
install targets `.agents/skills` and `.claude/skills`, and lists packages
whose `published` is false. There is no install button.

## P4 — Wizard of Oz

The pilot procedure is `catalog/marketplace/MANUAL-CHECKLIST.md`. A person
answers find, install, and contribute until that checklist has been run.
Story 109.5. No fictional pilot log is included.
