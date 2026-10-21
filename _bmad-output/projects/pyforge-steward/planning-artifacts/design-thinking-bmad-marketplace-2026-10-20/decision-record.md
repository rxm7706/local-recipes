# Decision record — marketplace reset (2026-10-20 session, recorded 2026-10-21)

The applied direction in the restart brief is the decision. The archived
seed stays archived (`folded-into-station-dream`). The living aspiration is
the 2026-10-21 entry on `docs/dreams/pyforge-steward.md`.

## Product

It is a marketplace for BMAD skills and modules, for station skills built
with BMAD, and for agents built with BMAD. Skills are the first artifact.
Four jobs: find, install, create, publish/contribute.

The first user is a teammate of rxm7706 who may use Claude Code, Cursor,
Copilot in VS Code, Devin, Gemini, or none of those. Hosting is GitHub plus
GitHub Pages. Install comes from GitHub/Pages or from Artifactory
(conda/pip), which is the v1 ship backend.

A skill ships as a plain `SKILL.md` folder, copied into both
`.agents/skills/` and `.claude/skills/`. Per-tool marketplace manifests are
optional generated outputs. An agent ships skill-first. A per-tool adapter
is generated only for a format that has been confirmed, and only with a
`requires` check. No adapter format was confirmed in this change, so none
is generated.

The teammate CLI is proposed as `bmp`. It shares an engine with
`steward catalog`. It is not a new station and it is not a new steward
duty. Story 109.4 holds it. Two contribution lanes exist: instructions-only
and code-backed. Publish automation waits on a Round 0 desk test and a
Wizard-of-Oz pilot (Story 109.5). The manual form is
`catalog/marketplace/MANUAL-CHECKLIST.md`.

## Q1–Q7, reviewed

The 2026-09-15 rulings stay in the archived seed. This review says what the
reset keeps.

1. **Reset.** v1 is a catalog of modules and Frames plus a Claude/Codex
   marketplace manifest. The reset's first artifact is a skill folder.
   Frames stay CAP-123. They are not the first job.
2. **Browse grows.** The thin list stays. GitHub Pages adds an index and a
   card per listing. The card is not a click-to-install control.
3. **Keep git as the edit store, and keep conda/Artifactory as a ship
   backend.** Add GitHub/Pages as a second way to install a skill folder.
4. **Keep "our repo, start empty".** No community dump. A new GitHub
   repository still needs operator confirmation. `catalog.yaml`
   `dedicated_repo` stays null. The skeleton in this repo is what would be
   pushed.
5. **Keep steward review and the v1 trust-tier names** (`unverified`,
   `community-reviewed`, `bmad-certified`). Every listing names its source.
6. **Keep no billing.**
7. **Keep no Layer 3.**

## Reuse and stop

Keep: `catalog.yaml` backends and sources, the empty `registry/estate.yaml`
`modules` list, `CatalogEngine`, the trust-tier names, the ship backends,
the `pyforge-estate-catalog` recipe, and the thin browse indexes.

Stop treating `extraKnownMarketplaces` and `bmad-method install
--custom-source` as the way a skill is installed. Copy the skill folder.
That does not close `DW-FU-60-1-4`: the installer still finds 0 modules
because the v1 rows are GitHub pointers, and a skill folder is a different
path.

Do not change `CatalogEngine.render`. Do not rewrite the committed
`.claude-plugin` or `.agents` manifests. Do not replace the estate
procedures under `.claude/skills/mason-environment/`,
`.claude/skills/mason-package/`, or `.claude/skills/pyforge-warden/`.
The portable copies live under `catalog/marketplace/skills/`.

## Station

Steward remains the owner. v1's engine, `estate.yaml`, Epic 60, and the
conda/Artifactory path already live there. `bmp` is a face on that engine.
Mason and warden own the seed skill content, not the store. Scribe owns
memory, not a catalog. The rationale is also in the station Dream entry of
2026-10-21.
