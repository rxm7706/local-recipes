---
name: pyforge-mason
description: >
  Mason station CLI grammar for the recipe, package and environment crafts
  plus doctor, reached as pyforge mason or POST /stations/mason/mcp. Use when
  running pyforge mason recipe, package, environment or doctor commands,
  scripting Mason exit codes or --format json output, or working in
  src/shared/packages/pyforge-mason/. Do not import pyforge.mason internals;
  the CLI is the public contract. Do not use for recipe knowledge such as
  pins, selectors or build fixes; conda-forge-expert owns recipe semantics
  and Mason's recipe verbs only wrap it.
---

# pyforge-mason

## Overview

Compiles `src/shared/packages/pyforge-mason/` (PyPI `pyforge-mason` 0.1.0) as an
agentskills.io content skill for the **mason** station. Source: local path
`src/shared/packages/pyforge-mason` @ commit `c9e07879` (`source_ref: local`).
Forge tier: **Quick** (SKF `skf-extract-public-api` + source reading; T1-low).
3 exports documented (`build_parser`, `main`, `__version__`). The package
`__init__.py` exports only `__version__` [SRC:src/pyforge/mason/__init__.py:L13];
other components reach Mason through its CLI, never by importing
`pyforge.mason` internals [SRC:README.md:L22-L25].

Mason is the Artisan Builder's station with three verb-bearing nouns —
`recipe`, `package`, `environment` — and a top-level `doctor` leaf
[SRC:src/pyforge/mason/cli.py:L8-L18].

**Recipe work belongs to conda-forge-expert.** The `recipe` noun wraps the
conda-forge-expert craft by subprocess; that skill stays canonical for recipe
semantics and is never forked [SRC:src/pyforge/mason/cli.py:L8-L12]
[SRC:README.md:L18-L20]. For every recipe question — what to write, which
pin, why a build failed — read
[conda-forge-expert](../../../conda-forge-expert/SKILL.md)
(`.claude/skills/conda-forge-expert/SKILL.md`) [SRC:README.md:L22-L23]. This
skill documents Mason's grammar only.

## Description

Mason — "forge the blocks, bind the environment, ship the structure"
[SRC:src/pyforge/mason/cli.py:L530-L533]. Its three nouns: `recipe` authors,
validates and builds conda recipes by wrapping conda-forge-expert; `package`
builds and ships distributions to PyPI and conda-forge; `environment` resolves
conflicting worlds into one lockfile [SRC:src/pyforge/mason/cli.py:L108-L112]
[SRC:README.md:L5].

## Quick Start

Use the `pyforge mason …` grammar or `POST /stations/mason/mcp`
[SRC:README.md:L22-L25]. The argparse program name is `mason`, so help and
usage text print `mason …` [SRC:src/pyforge/mason/cli.py:L530-L535]; the
`pyforge mason` form is the one public grammar. Run from the repository root:
CFE auto-discovery and manifest discovery start at the current directory
[SRC:src/pyforge/mason/cli.py:L1119-L1124] [SRC:src/pyforge/mason/cli.py:L1510-L1513].

```bash
pyforge mason doctor --format json
pyforge mason recipe validate RECIPE_PATH
pyforge mason package build PROJECT_PATH --target library
pyforge mason environment check [MANIFEST_PATH ...] --lockfile PATH
```

**doctor** [SRC:src/pyforge/mason/cli.py:L1106-L1126] — diagnoses the
installed Mason: version, CFE resolution, engine presence
[SRC:src/pyforge/mason/cli.py:L113]. It never raises and always exits
`EXIT_OK`; a missing CFE or engine is data in the degradation report, not a
command failure.

**recipe** — eight verbs that delegate to conda-forge-expert:
`new`, `validate`, `build`, `diagnose`, `optimize`, `scan`, `submit`,
`update` [SRC:src/pyforge/mason/cli.py:L583-L794].

**package** — `build` and `ship`, built natively and CFE-independent for
`build` [SRC:src/pyforge/mason/cli.py:L807-L852].

**environment** — `lock` and `check` via conda-lock, CFE-independent
[SRC:src/pyforge/mason/cli.py:L870-L947].

<!-- [MANUAL:additional-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:additional-notes] -->

## Common Workflows

**Health check before any CFE-dependent verb:**
`pyforge mason doctor` → read CFE resolution in the report → then a `recipe` verb
[SRC:src/pyforge/mason/cli.py:L1112-L1117].

**Recipe gate in CI:** `pyforge mason recipe validate RECIPE_PATH` — the only
`recipe` verb whose wrapped validator outcome becomes the exit code
(`EXIT_OK` on pass, else `EXIT_FAILED`) [SRC:src/pyforge/mason/cli.py:L1226-L1251].

**Rehearse, then ship:** `pyforge mason package build PROJECT_PATH` →
`pyforge mason package ship --to pypi-test,pypi` (dry run) → add `--yes` to ship
for real [SRC:src/pyforge/mason/cli.py:L140-L144] [SRC:src/pyforge/mason/cli.py:L493-L498].

**Lock, then gate staleness:** `pyforge mason environment lock -o LOCKFILE` →
`pyforge mason environment check --lockfile LOCKFILE` with the same
`--platform` list [SRC:src/pyforge/mason/cli.py:L935-L943].

**Submit a recipe:** `pyforge mason recipe submit RECIPE_DIR` (dry run) → add
`--yes` to push and open the PR, or `--prepare-only` to stop after the branch
push [SRC:src/pyforge/mason/cli.py:L127-L130] [SRC:src/pyforge/mason/cli.py:L732-L742].

## Key API Summary

| Command | Purpose | Key params |
|---|---|---|
| `doctor` | Version, CFE resolution, engine presence; always exit 0 | global flags only |
| `recipe new` | Generate a recipe via CFE | one of `--from-pypi/--from-github/--from-cran/--from-npm`, `--output/-o` |
| `recipe validate` | CFE validator; outcome is the exit code | `recipe_path` |
| `recipe build` | Native build; Docker for CI parity | `RECIPE_PATH`, `--docker` + `--config` |
| `recipe diagnose` | CFE failure analyzer on a log | `log_path` (not `-`) |
| `recipe optimize` | CFE recipe optimizer lint | `recipe_path` |
| `recipe scan` | CFE vulnerability scan of exact pins | `recipe_path` |
| `recipe submit` | CFE two-phase staged-recipes submission | `recipe_path` (directory), `--yes`, `--prepare-only` |
| `recipe update` | CFE autotick version bump | `recipe_path`, `--dry-run`, `--github`, `--repo`, `--pre` |
| `package build` | wheel + sdist (PEP 517) and `.conda` (pixi build) | `PROJECT_PATH`, `--target library` |
| `package ship` | Ship to targets; dry run by default | `--to TARGETS`, `--yes`, `--recipe-path` |
| `environment lock` | Manifests to one lockfile via conda-lock | `MANIFEST_PATH...`, `--output/-o`, `--platform` |
| `environment check` | Lockfile staleness gate | `MANIFEST_PATH...`, `--lockfile/-l`, `--platform` |
| `main` | Entry point; sole owner of the exit code | `argv` |
| `build_parser` | Builds the `mason` noun → verb parser | — |

Sources: help strings [SRC:src/pyforge/mason/cli.py:L108-L154]; registrations
[SRC:src/pyforge/mason/cli.py:L523-L949]; `main`
[SRC:src/pyforge/mason/cli.py:L1080].

<!-- [MANUAL:api-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:api-notes] -->

## Key Exports

`__all__` is `["__version__"]` [SRC:src/pyforge/mason/__init__.py:L13]. The
SKF public-API extract of `cli.py` adds `build_parser`
[SRC:src/pyforge/mason/cli.py:L523] and `main`
[SRC:src/pyforge/mason/cli.py:L1080]. These three are the whole importable
surface; everything else under `pyforge.mason` is internal.

## Usage

Invoke Mason as `pyforge mason …` or through `POST /stations/mason/mcp`; never
import `pyforge.mason` internals [SRC:README.md:L22-L25]. Global flags parse
before or after the noun, so `pyforge mason --format json recipe …` and
`pyforge mason recipe … --format json` are equivalent
[SRC:src/pyforge/mason/cli.py:L524-L528]. For recipe content — what a recipe
should contain and why a build fails — consult
[conda-forge-expert](../../../conda-forge-expert/SKILL.md) first; Mason's
`recipe` verbs only run that skill's tools [SRC:README.md:L18-L23].

## Key Types

**Global flags** — AD-13's closed set of six, accepted before or after the noun
and verb; each resolves flag → environment → default
[SRC:src/pyforge/mason/cli.py:L376-L434] [SRC:src/pyforge/mason/cli.py:L156-L164]:

| Flag | Environment | Default |
|---|---|---|
| `--cfe-root PATH` | `MASON_CFE_ROOT` | auto-discovery |
| `--cfe-python PATH` | `MASON_CFE_PYTHON` | running interpreter |
| `--cfe-timeout SECONDS` | `MASON_CFE_TIMEOUT` | none (finite, positive) |
| `--format {text,json}` | `MASON_FORMAT` | `text` |
| `--verbose` | `MASON_VERBOSE` | off |
| `--quiet` | `MASON_QUIET` | off; wins over `--verbose` |

**Exit codes** — `main()` alone returns them; a verb never calls `sys.exit()`
[SRC:src/pyforge/mason/cli.py:L103-L106]. Names: `EXIT_OK`, `EXIT_FAILED`,
`EXIT_USAGE`, `EXIT_CFE_UNAVAILABLE`, `EXIT_INTERRUPTED`, defined in
`exit_codes.py` [SRC:src/pyforge/mason/cli.py:L94-L100]. An unresolved CFE root
maps to `EXIT_CFE_UNAVAILABLE` (3), distinct from `EXIT_FAILED`
[SRC:src/pyforge/mason/cli.py:L1603-L1612]; any other `MasonError` maps to
`EXIT_FAILED` [SRC:src/pyforge/mason/cli.py:L1613-L1618]; argparse usage errors
pass through as 2 [SRC:src/pyforge/mason/cli.py:L103-L106]
[SRC:src/pyforge/mason/cli.py:L1596-L1602].

**JSON output** — with `--format json`, a failure prints `identifier: message`
on stderr and also writes an error envelope to stdout whose errors list holds
`{identifier, message}` [SRC:src/pyforge/mason/cli.py:L1054-L1077].

## Architecture at a Glance

- **recipe** — wraps conda-forge-expert by subprocess; never forked
  [SRC:src/pyforge/mason/cli.py:L8-L12].
- **package** — built natively; no wheel-build/upload path exists to wrap
  [SRC:src/pyforge/mason/cli.py:L13].
- **environment** — built natively; no lock orchestration exists to wrap
  [SRC:src/pyforge/mason/cli.py:L14].
- **doctor** — top-level leaf with no verb level [SRC:src/pyforge/mason/cli.py:L16-L18].
- **CLI** — argparse, not click/typer (FR-41 forbids a CLI-framework dependency)
  [SRC:src/pyforge/mason/cli.py:L77-L78].

## CLI

```text
pyforge mason [global flags] doctor
pyforge mason recipe new (--from-pypi PKG | --from-github OWNER/REPO | --from-cran PKG | --from-npm PKG) --output PATH
pyforge mason recipe validate RECIPE_PATH
pyforge mason recipe build RECIPE_PATH [--docker --config CONFIG]
pyforge mason recipe diagnose LOG_PATH
pyforge mason recipe optimize RECIPE_PATH
pyforge mason recipe scan RECIPE_PATH
pyforge mason recipe submit RECIPE_DIR [--yes] [--prepare-only]
pyforge mason recipe update RECIPE_PATH [--dry-run] [--github] [--repo OWNER/REPO] [--pre]
pyforge mason package build PROJECT_PATH [--target library]
pyforge mason package ship --to TARGETS [--yes] [--target library] [--recipe-path PATH]
pyforge mason package --ship TARGETS [--yes] [--target library] [--recipe-path PATH]
pyforge mason environment lock [MANIFEST_PATH ...] --output PATH [--platform PLATFORMS]
pyforge mason environment check [MANIFEST_PATH ...] --lockfile PATH [--platform PLATFORMS]
```

MCP: `POST /stations/mason/mcp` [SRC:README.md:L24-L25].

## Full API Reference

### Dispatch rules

- A bare `pyforge mason` prints help and exits `EXIT_OK`
  [SRC:src/pyforge/mason/cli.py:L1100-L1104].
- A noun with no verb prints that noun's help on stderr and exits `EXIT_USAGE`
  [SRC:src/pyforge/mason/cli.py:L1177-L1184]. The one exception is
  `package --ship TARGETS`, the bare-noun alias of `package ship --to`
  [SRC:src/pyforge/mason/cli.py:L839-L848].
- `--ship` together with an explicit `package` verb is a usage error
  [SRC:src/pyforge/mason/cli.py:L1128-L1149].
- A delegated tool's non-zero return code is data on the result, not a raised
  error; the envelope `status` stays `ok` [SRC:src/pyforge/mason/cli.py:L1291-L1296].
  Exceptions that project onto the exit code: `recipe validate`
  [SRC:src/pyforge/mason/cli.py:L1251], `environment lock`
  [SRC:src/pyforge/mason/cli.py:L1532], `environment check`
  [SRC:src/pyforge/mason/cli.py:L1580] and `package ship`
  [SRC:src/pyforge/mason/cli.py:L1051].

### recipe

| Verb | Arguments | Constraints |
|---|---|---|
| `new` | `--from-pypi PACKAGE` / `--from-github OWNER/REPO` / `--from-cran PACKAGE` / `--from-npm PACKAGE` (exactly one, required); `--output/-o PATH` (required) | [SRC:src/pyforge/mason/cli.py:L589-L621] |
| `validate` | `recipe_path` — recipe file or its directory | exit code follows the validator [SRC:src/pyforge/mason/cli.py:L641-L644] |
| `build` | `RECIPE_PATH`; `--docker`; `--config CONFIG` | `--docker` and `--config` require each other; a blank `--config` counts as absent [SRC:src/pyforge/mason/cli.py:L1262-L1275] |
| `diagnose` | `log_path` | `-` (stdin) is refused with `EXIT_USAGE` [SRC:src/pyforge/mason/cli.py:L1319-L1324] |
| `optimize` | `recipe_path` | passed through to CFE unchecked [SRC:src/pyforge/mason/cli.py:L686-L700] |
| `scan` | `recipe_path` | scans exact pins only; calls `api.osv.dev` by default [SRC:src/pyforge/mason/cli.py:L122-L126] |
| `submit` | `recipe_path` (the recipe directory, not a file); `--yes`; `--prepare-only` | dry run unless `--yes` [SRC:src/pyforge/mason/cli.py:L726-L742] |
| `update` | `recipe_path`; `--dry-run`; `--github`; `--repo OWNER/REPO`; `--pre` | `--repo`/`--pre` are ignored with a warning unless `--github` [SRC:src/pyforge/mason/cli.py:L1444-L1445] |

`update`'s `recipe_path` must be a v1 `recipe.yaml`; with `--github` a
directory is also accepted [SRC:src/pyforge/mason/cli.py:L759-L764].

### package

| Verb | Arguments | Constraints |
|---|---|---|
| `build` | `PROJECT_PATH`; `--target {library}` (default `library`) | never reads CFE flags [SRC:src/pyforge/mason/cli.py:L1469-L1485] |
| `ship` | `--to TARGETS` (required); `--yes`; `--target library`; `--recipe-path RECIPE_PATH` | targets: `pypi`, `pypi-test`, `conda-forge`, `channel:NAME`, comma-separated [SRC:src/pyforge/mason/cli.py:L507-L513] |

`pypi-test` named alongside `pypi` always runs first and gates it
[SRC:src/pyforge/mason/cli.py:L140-L144]. `--recipe-path` matters only for the
`conda-forge` target [SRC:src/pyforge/mason/cli.py:L499-L506]. `ship` exits
`EXIT_FAILED` when any target result is `FAILED`, else `EXIT_OK`; an unresolved
CFE root becomes a `FAILED` target, not exit 3
[SRC:src/pyforge/mason/cli.py:L1010-L1026].

### environment

| Verb | Arguments | Constraints |
|---|---|---|
| `lock` | `MANIFEST_PATH...` (optional); `--output/-o PATH` (required); `--platform PLATFORMS` | exit `EXIT_FAILED` when conda-lock fails [SRC:src/pyforge/mason/cli.py:L876-L896] |
| `check` | `MANIFEST_PATH...` (optional); `--lockfile/-l PATH` (required, never written); `--platform PLATFORMS` | exit `EXIT_FAILED` when stale or when the check fails [SRC:src/pyforge/mason/cli.py:L921-L943] |

Manifests: `pyproject.toml`, `environment.yml`, `requirements*.txt`,
`pixi.toml`; omit them to auto-discover in the current directory, and the
discovered list prints to stderr [SRC:src/pyforge/mason/cli.py:L880-L881]
[SRC:src/pyforge/mason/cli.py:L1510-L1513]. Pass `check` the same
`--platform` list the lockfile was locked with; conda-lock's own default
reports a narrower lockfile as stale [SRC:src/pyforge/mason/cli.py:L939-L943].

### Python entry points

- `main(argv: Sequence[str] | None = None) -> int` — parses, configures
  logging, dispatches, maps outcomes to exit codes; catches
  `KeyboardInterrupt`, `SystemExit`, `CfeUnresolvedError`, `MasonError` and any
  other exception [SRC:src/pyforge/mason/cli.py:L1080-L1623]. It replaces root
  logging handlers (`force=True`), so it is not safe to call in-process from a
  host that owns the root logger [SRC:src/pyforge/mason/cli.py:L350-L360].
- `build_parser() -> argparse.ArgumentParser` — the full noun → verb tree
  [SRC:src/pyforge/mason/cli.py:L523-L949].
- `__version__: str` — installed distribution version, or `0.1.0+source` from a
  source tree [SRC:src/pyforge/mason/__init__.py:L16-L25].
