# BMAD Projects in this Repository

This repository hosts multiple BMAD projects under one shared installation. Each
project has its own subdirectory under `_bmad-output/projects/<slug>/` containing
its planning artifacts, implementation artifacts, project context, and
project-scoped BMAD config overrides.

## Active project switching

Three mechanisms, in resolution-priority order (highest first):

1. **Per-call CLI flag:** `python3 _bmad/scripts/resolve_config.py --project <slug> ...`
2. **Environment variable:** `BMAD_ACTIVE_PROJECT=<slug>` (per-shell or per-subprocess scope)
3. **Marker file:** `_bmad/custom/.active-project` (gitignored, single-line slug)

Use the `scripts/bmad-switch` helper to manage the marker:

```bash
scripts/bmad-switch --list                  # list known projects
scripts/bmad-switch --current               # print active project
scripts/bmad-switch <slug>                  # set active project
scripts/bmad-switch --clear                 # remove marker (no active project)
```

When **no** active project resolves, the BMAD config resolver loads only the
four global layers (installer team/user + custom team/user). Skills will then
write to whatever `output_folder` is set in the global layers (default
`_bmad-output`); to keep a single project's outputs from polluting the
multi-project layout, always set an active project before invoking skills.

## Config layering

| Layer | File                                                                       | Scope                            |
|-------|----------------------------------------------------------------------------|----------------------------------|
| 1     | `_bmad/config.toml`                                                        | Installer team (regenerated)     |
| 2     | `_bmad/config.user.toml`                                                   | Installer user (regenerated)     |
| 3     | `_bmad/custom/config.toml`                                                 | **Global custom team, all projects** |
| 4     | `_bmad/custom/config.user.toml`                                            | Global custom user, all projects |
| 5     | `_bmad-output/projects/<slug>/.bmad-config.toml`                           | **Project team, this project only** |
| 6     | `_bmad-output/projects/<slug>/.bmad-config.user.toml`                      | Project user, this project only  |

Higher-numbered layers override lower-numbered layers. Layers 5 and 6 are only
loaded when an active project resolves.

## Projects

| Slug                   | Status | Description                                                                                                                                                                       |
|------------------------|--------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `local-recipes`        | active | Primary project — conda-forge recipe authoring monorepo (this repo's main purpose).                                                                                                |
| `presenton-pixi-image` | active | Air-gapped, conda-forge-native repackaging of the Presenton AI deck-generation app for OpenShift Container Platform deployment in regulated-enterprise environments.                |
| `deckcraft`            | active | Air-gapped, conda-forge-native AI pipeline for generating editable PowerPoint, Marp markdown, infographics, and images. Multi-surface (Claude Skill, MCP for Copilot/MS365, CLI). Complements `presenton-pixi-image` (built from primitives, not a repackage).                |

## Adding a new project

1. Create the directory tree:
   ```bash
   mkdir -p _bmad-output/projects/<slug>/{planning-artifacts,implementation-artifacts}
   ```
2. Create `_bmad-output/projects/<slug>/.bmad-config.toml` with at minimum:
   ```toml
   output_folder = "_bmad-output/projects/<slug>"

   [project]
   slug = "<slug>"
   description = "..."
   status = "active"
   ```
3. Add a row to the **Projects** table above.
4. Switch to the new project: `scripts/bmad-switch <slug>`.
5. Run BMAD skills as normal — they will write under the new project's directory.

## Reading another project's artifacts (without switching)

For read-only cross-project access (e.g., comparing PRDs), just open the file
directly at its path:

```
_bmad-output/projects/<slug>/planning-artifacts/<filename>
```

No resolver state change needed — only writes go through the active-project
machinery.

## Running a skill against a non-active project (without switching globally)

For one-off cross-project writes:

```bash
BMAD_ACTIVE_PROJECT=<slug> python3 _bmad/scripts/resolve_config.py ...
# or
python3 _bmad/scripts/resolve_config.py --project <slug> ...
```

The marker file is left untouched; only this invocation sees the override.
