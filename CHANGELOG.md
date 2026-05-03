# Changelog

All notable changes to this repository are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this repository adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) where versioned releases apply.

Subsystems with their own internal versioning (individual conda recipes, the FastMCP server, BMAD installation, etc.) are noted with a parenthetical scope tag at the start of each entry.

## [Unreleased]

### Added — conda-forge-expert v6.1.0 (skill: conda-forge-expert)

- **(skill: conda-forge-expert)** `detail_cf_atlas.py --version VER` flag scopes the `--vdb` "affecting current" CVE check to an arbitrary release instead of the atlas-derived `latest_conda_version`. Useful when the atlas-latest diverges from the version actually deployed downstream (e.g., `django` atlas-latest is 6.0.4 but the channel `noarch` build is 5.2.12, and an internal app may pin to a third version). When set, version-pinned purls (`pkg:pypi/...@VER`, `pkg:conda/...@VER`, `pkg:npm/...@VER`) carry the override; un-pinned purls and the historical-vuln baseline are unchanged. The risk-line label flips to `queried_version <ver>` so the report makes clear what was scanned. Atlas-derived sections (header, build matrix, channel storefronts) keep showing `latest_conda_version`. Backward-compatible: omitting the flag preserves existing behavior.
- **(skill: conda-forge-expert)** `detail_cf_atlas.py` air-gap-friendly build-matrix fallback. When `api.anaconda.org` is unreachable (commonly blocked at corporate egress), the script now falls back to per-subdir `current_repodata.json` from a conda channel mirror via `_http.resolve_conda_forge_urls()` (CONDA_FORGE_BASE_URL → pixi mirrors → pixi default-channels → repo.prefix.dev/conda-forge → conda.anaconda.org/conda-forge). The build-matrix header label is dynamic so users see which source produced the data ("from anaconda.org" vs "from https://repo.prefix.dev/conda-forge" vs the JFrog mirror they pointed at). Reshapes records to match the files API output so `render()` is source-agnostic. JFrog auth headers are injected automatically by `_http_make_request` when the env vars are set. Drops `upload_time` (repodata's `timestamp` is build time, not upload time) — render prints that field as empty cleanly.
- **(skill: conda-forge-expert)** New pixi task `[feature.vuln-db.tasks.detail-cf-atlas-vdb]` presets `--vdb --vdb-all` so callers only need `<name>` and optionally `--version VER`. Existing `detail-cf-atlas` task descriptions in both envs updated to mention `--version`.
- **(skill: conda-forge-expert)** New offline test file `tests/unit/test_detail_cf_atlas.py` (8 tests) covering the repodata fallback shape parity, subdir filter, candidate-chain walk on 502, no-match error, missing `_http` helper, and the `--version` purl-substitution paths (override + default). Suite total goes 205 → 213 passing.
- **(skill: conda-forge-expert)** Docs sync: top-level `README.md` quick-reference table, `quickref/commands-cheatsheet.md`, `docs/enterprise-deployment.md`, and the skill `CHANGELOG.md` v6.1.0 entry.

### Changed — conda-forge-expert (skill: conda-forge-expert)

- **(skill: conda-forge-expert)** `detail_cf_atlas.py` cleanup: removed dead `CONDA_FORGE_BASE` module-level constant (defined but never used; the docstring's "Honors CONDA_FORGE_BASE_URL" claim was misleading — it now is true via `_http.resolve_conda_forge_urls()` in the new fallback). Replaced the `_HTTP_AVAILABLE` boolean guard with `_http_make_request is not None` checks so pyright narrows the type correctly (eliminates pre-existing `possibly-unbound` warning).

### Added — conda-forge-expert v6.0.0 (skill: conda-forge-expert)

- **(skill: conda-forge-expert)** Three-tier directory layout. `.claude/skills/conda-forge-expert/scripts/` remains the canonical source. New `.claude/scripts/conda-forge-expert/` is the public CLI entrypoint layer (22 thin subprocess wrappers — what `pixi run` calls). `.claude/data/conda-forge-expert/` (mutable runtime state) moved from the old `.claude/skills/data/`. README at the new entrypoint path documents the wrapper pattern.
- **(skill: conda-forge-expert)** New `_http.py` enterprise HTTP helper (truststore SSL injection + JFrog/GitHub/.netrc auth chain). Consumed by `conda_forge_atlas.py`, `detail_cf_atlas.py`, `github_version_checker.py`, `inventory_channel.py`. Same checkout works externally and internally — enterprise routing is **runtime-driven** via env vars; no enterprise URLs in committed `pixi.toml`.
- **(skill: conda-forge-expert)** `mapping_manager.py` curl SSL fallback. When `conda-forge-metadata` raises a TLS trust failure, re-fetches the PyPI→conda mapping via system `curl` from `regro/cf-graph-countyfair`. Fixes networks where Python's TLS trust is broken but OS trust isn't.
- **(skill: conda-forge-expert)** SKILL.md and `config/skill-config.yaml` bumped 5.10.0 → 6.0.0.

### Changed — pixi.toml (skill: conda-forge-expert)

- **(skill: conda-forge-expert)** All 22 task `cmd` lines re-targeted from `.claude/skills/conda-forge-expert/scripts/` → `.claude/scripts/conda-forge-expert/` (entrypoint layer). Pytest paths intentionally still reference the skill-internal `tests/` dir.
- **(skill: conda-forge-expert)** `[feature.vuln-db.activation.env]` exports `VDB_HOME` / `VDB_CACHE` under the new `.claude/data/conda-forge-expert/` path.

### Fixed — pre-commit regressions

- **(skill: conda-forge-expert)** `conda_forge_atlas.py` `CONDA_FORGE_SUBDIRS` / `CONDA_FORGE_CHANNEL` constants were inadvertently deleted during an LLM-edit and replaced with a literal `# ...existing code...` placeholder; restored before any user impact.
- **(skill: conda-forge-expert)** `pixi.toml` had a hardcoded JFrog `index-url` and Debian-specific SSL cert paths that broke external `pixi install`; reverted in favor of runtime detection via `_http.py`.
- **(skill: conda-forge-expert)** `tests/meta/test_skill_md_consistency.py` and `tests/meta/test_all_scripts_runnable.py` updated to recognize both canonical and entrypoint paths and to skip underscore-prefixed internal helpers; four scripts from v5.11/v5.12 (`conda_forge_atlas`, `detail_cf_atlas`, `scan_project`, `inventory_channel`) added to the runnable-list registry.
- **(repo hygiene)** `.gitignore` now covers `.claude/data/` (skill runtime state) and `.claude/scheduled_tasks.lock` (Claude Code session-lock artifact).

### Documentation — conda-forge-expert v6.0.0

- **(skill: conda-forge-expert)** `CLAUDE.md` — added "conda-forge-expert v6.0.0 layout (3-tier)" subsection mapping each tier to its purpose; documented the runtime-driven enterprise routing model.
- **(skill: conda-forge-expert)** `README.md` — Pixi tasks section gained the missing v5.11/v5.12 task families (atlas suite, vuln-db env tasks, build-local* family, autotick-npm) and an enterprise-routing note.
- **(skill: conda-forge-expert)** `_bmad-output/projects/local-recipes/project-context.md` — repository conventions section reflects the canonical-vs-entrypoint split and the new data path.

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
