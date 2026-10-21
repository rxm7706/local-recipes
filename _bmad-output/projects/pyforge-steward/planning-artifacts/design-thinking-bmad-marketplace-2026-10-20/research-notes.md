# Research notes — 2026-10-21

`station-inventory.md` and `tool-support-matrix.md` were named as session
research and were not mounted. This note is the check this change ran. It
is not those files.

## Station fit

| Station | Why it is or is not the owner |
|---|---|
| steward | Owns `catalog/`, `CatalogEngine`, Epic 60, `registry/estate.yaml`, and the conda/Artifactory ship path. The reset keeps that engine. |
| mason | Owns environment lock and package build, which two seed skills describe. It does not own a catalog or Pages. |
| warden | Owns `warden scan`, which the third seed skill describes. It does not own a store. |
| scribe | Owns team memory and recall. A marketplace is not a memory log. |
| herald | Owns decks and the docs site duct. The marketplace Pages are a separate static tree under the catalog, not `docs-site/`. |

## Commands that exist (2026-10-21, this repo's pixi environments)

These are not assumed to be on a teammate's `PATH`. The pilot skills say
which package must be installed first.

| Command | Seen |
|---|---|
| `conda-lock` | 4.0.2 |
| `mason environment --help` | `lock`, `check` |
| `pyproject-build` / `build` | `build` 1.6.1 |
| `twine` | 7.0.0 |
| `pixi` | 0.81.0 |
| `warden scan --help` | `scan`, including `--doctor` |
| `deptry` | 0.25.1 |
| `osv-scanner` | 2.4.0 |

`pyforge mason environment lock` assembles `conda-lock lock -f <manifest>
--lockfile <out>` (`pyforge.mason.engines.condalock`). Check runs
`conda-lock lock --check-input-hash` on a temporary copy. `pyforge mason
package build` assembles `pyproject-build --no-isolation`. The conda
artifact argv is `pixi build --output-dir <dir>`. Upload argv
(`twine upload`, `pixi upload prefix --channel`) runs only after mason
`--yes`. The pilot does not tell a teammate to upload.

`warden scan` is the verdict. `deptry` and `osv-scanner scan --offline` are
engines the CLI calls. Their stdout is not a second verdict.

## Unpublished packages (HTTP 404 on 2026-10-21)

PyPI, conda-forge, and the SelfExplainML channel returned 404 for
`pyforge-mason`, `pyforge-warden`, `pyforge-core`, `pyforge-steward`, and
`pyforge-estate-catalog`. There is a recipe at `recipes/pyforge-estate-catalog/`.
There is no `recipes/pyforge-mason` or `recipes/pyforge-warden`.

## Tools the first user may have

The brief names Claude Code, Cursor, Copilot in VS Code, Devin, Gemini, and
none. The install that does not depend on a tool's marketplace format is
the folder copy into `.agents/skills/` and `.claude/skills/`. A matrix of
each tool's marketplace file was not mounted, so this change does not
generate those files.
