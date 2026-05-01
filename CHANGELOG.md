# Changelog

All notable changes to this repository are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this repository adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) where versioned releases apply.

Subsystems with their own internal versioning (individual conda recipes, the FastMCP server, BMAD installation, etc.) are noted with a parenthetical scope tag at the start of each entry.

## [Unreleased]

### Added — BMAD multi-project layout

- **(BMAD)** Per-project subdirectory structure under `_bmad-output/projects/<slug>/` so this single BMAD installation can drive multiple independent projects without artifact mixing.
- **(BMAD)** Six-layer config resolver — `_bmad/scripts/resolve_config.py` extended from four to six TOML merge layers. New layers 5 and 6 read from `_bmad-output/projects/<slug>/.bmad-config.toml` (team, committed) and `.bmad-config.user.toml` (per-developer, gitignored). Layers 5–6 only load when an active project resolves.
- **(BMAD)** Per-call `--project <slug>` CLI flag on `resolve_config.py` — overrides the active-project marker for a single invocation. Closes the "only one active project at a time" weakness for cross-project read/write scenarios. Slug format validated against `^[a-z0-9][a-z0-9_-]*$`.
- **(BMAD)** Active-project resolution priority chain: `--project` flag → `BMAD_ACTIVE_PROJECT` env var → `_bmad/custom/.active-project` marker file → none.
- **(BMAD)** `scripts/bmad-switch` helper — manages the active-project marker. Subcommands: `--list`, `--current`, `--clear`, or `<slug>` to set. Validates project directory existence before writing the marker.
- **(BMAD)** `_bmad-output/PROJECTS.md` — index of projects in this repository, including the project table, config layering reference, "adding a new project" guide, and read-vs-write cross-project usage patterns.
- **(BMAD)** Project entries:
  - `local-recipes` — primary; conda-forge recipe authoring (this repo's main purpose).
  - `presenton-pixi-image` — secondary; air-gapped Presenton AI deck-generation repackaging for OpenShift Container Platform deployment in regulated-enterprise environments. PRD step 3 of 13 (Success Criteria + Product Scope, 33 deltas applied across 4 elicitation/party-mode rounds) committed; step 4 (User Journey Mapping) pending.
- **(BMAD)** Per-project `.bmad-config.toml` files at `_bmad-output/projects/<slug>/.bmad-config.toml` for both projects, each setting `output_folder` to the project's subdirectory plus `[project]` metadata (slug, description, status).
- **(BMAD)** `CLAUDE.md` § "Multi-Project Pattern" documenting the layout, resolution priority, six-layer config table, and "adding a new project" pointer.

### Changed — BMAD artifact paths

- **(BMAD)** `_bmad-output/planning-artifacts/prd.md` → `_bmad-output/projects/presenton-pixi-image/planning-artifacts/prd.md`. The PRD content (33 deltas applied) is unchanged; only the path moved. Frontmatter `inputDocuments` references to the old `_bmad-output/project-context.md` will need to be updated when the presenton PRD work resumes (or a presenton-specific project context generated via `bmad-generate-project-context`).
- **(BMAD)** `_bmad-output/implementation-artifacts/{deferred-work.md,spec-cursor-sdk-local-recipe.md}` → `_bmad-output/projects/local-recipes/implementation-artifacts/`. Both files are conda-recipes-scoped, so they belong under the `local-recipes` project.
- **(BMAD)** `_bmad-output/project-context.md` → `_bmad-output/projects/local-recipes/project-context.md`. The context describes conda-recipes conventions and is project-scoped to `local-recipes`. Other projects (e.g., `presenton-pixi-image`) will need their own.
- **(BMAD)** Removed empty `_bmad-output/planning-artifacts/` and `_bmad-output/implementation-artifacts/` directories at the repo level (replaced by per-project subdirectories).
- **(BMAD)** `.gitignore` — replaced `_bmad-output/implementation-artifacts/` with `_bmad-output/projects/*/implementation-artifacts/` (per-project scope). Added `_bmad/custom/.active-project` (per-developer marker) and `_bmad-output/projects/*/.bmad-config.user.toml` (per-developer per-project overrides). Per-project `planning-artifacts/` remain committed as team artifacts.

### Documentation

- **(BMAD)** `docs/bmad-setup-plan.md` extended with Phase 8 (Multi-Project Layout) covering the migration, resolver extension, switcher, and operational workflow for running multiple projects from one BMAD installation. Phase 2 commands updated to reflect the new project-context.md path under `_bmad-output/projects/<slug>/`.
- **(BMAD)** `README.md` — added BMAD multi-project layout section linking to `_bmad-output/PROJECTS.md`, `docs/bmad-setup-plan.md`, and the `CLAUDE.md` reference. Project structure listing updated to include `_bmad/`, `_bmad-output/`, `scripts/bmad-switch`, `CHANGELOG.md`, `docs/bmad-setup-plan.md`, and `docs/specs/`.
- **(BMAD)** Memory entry saved (`feedback_bmad_multi_project.md` in `~/.claude/projects/.../memory/`) reminding future Claude sessions to confirm the active project before invoking write-skills.

### Removed

- **(repo hygiene)** Stray top-level `{output_folder}/` directory (with empty `planning-artifacts/` and `implementation-artifacts/` subdirs) — bug residue from an earlier session where an unsubstituted template literal was used as a path. Now removed; the multi-project resolver substitutes `{output_folder}` correctly so this directory will not be regenerated.

### Notes

- The `local-recipes` project is currently set as active (`scripts/bmad-switch local-recipes`). To work on `presenton-pixi-image`, run `scripts/bmad-switch presenton-pixi-image` and then say *"continue the PRD"* to resume from step 4.
- Reading another project's artifacts does not require switching — read from the file path directly.
- Mitigations 2 (per-skill `--project=<slug>` argument) and 3 (namespaced multi-config merge for simultaneous multi-project ops) are deferred. Build only if Mitigation 1 (per-call resolver flag) proves insufficient.
