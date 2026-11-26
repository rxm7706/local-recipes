---
name: pyforge-mason
description: >
  Mason station CLI grammar for the recipe, package and environment crafts
  plus self-check, reached as pyforge mason or POST /stations/mason/mcp. Use when
  running pyforge mason recipe, package, environment or self-check commands,
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
`src/shared/packages/pyforge-mason` @ commit `4c72fc94de`, read as it stands
(`source_ref: local`). Forge tier: **Forge** (the SKF
ast-grep public-API extract + source reading; `__version__` read by eye, T1-low).
First compiled from `c9e07879` (Story 19.1); recompiled in place at 0.1.0 on
2026-11-12 (steward Story 29.5, the fixes the EGM audit of 2026-11-05 accepted:
MAS-R-F2, MAS-R-F3, MAS-R-F5, MAS-R-F6) from the scope widened with
`exit_codes.py`, `render.py`, `models.py` and `resolve.py`, the README mason
Story 37.3 corrected, the station contract `contract.md` as a doc source, and the
real `mason --help`, the way Story 29.1 and atlas Stories 33.1 and 33.2 did.
Updated to 0.1.1 on 2026-11-25 by `skf-update-skill` (mason Story 42.1, operator
ruling 2026-11-25 "Exit 1 on failure"): a failed wrapped tool makes Mason exit 1.
Updated to 0.1.2 on 2026-11-26 by `skf-update-skill`: the self-diagnosis command is
`self-check`, and its old spelling, the doctor station's name, is no longer accepted;
the citations follow the moved lines.
3 exports documented (`build_parser`, `main`, `__version__`). The package
`__init__.py` exports only `__version__` [SRC:src/pyforge/mason/__init__.py:L13];
other components reach Mason through its CLI, never by importing
`pyforge.mason` internals [SRC:README.md:L22-L25].

Mason is the Artisan Builder's station with three verb-bearing nouns —
`recipe`, `package`, `environment` — and a top-level `self-check` leaf
[SRC:src/pyforge/mason/cli.py:L113-L120].

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
[SRC:src/pyforge/mason/cli.py:L575-L578]. Its three nouns: `recipe` authors,
validates and builds conda recipes by wrapping conda-forge-expert; `package`
builds and ships distributions to PyPI and conda-forge; `environment` resolves
conflicting worlds into one lockfile [SRC:src/pyforge/mason/cli.py:L113-L117]
[SRC:README.md:L5].

**The public contract** is
`_bmad-output/projects/pyforge-mason/planning-artifacts/specs/spec-pyforge-mason/contract.md`
(spec-pyforge-mason:CAP-5): every parser path, option and positional, every
environment variable, the exit codes, the error identifiers, the MCP tool and
portal-job names and the feature-flag keys (none: Mason reads no flag), plus the
JSON envelope, the ship states and the self-check report as prose [SRC:README.md:L35-L36].
The MCP names and exit codes in this skill are rows of that file; where they
differ, the contract and the code win.

## Quick Start

Use the `pyforge mason …` grammar: it is the one public grammar and reaches every
verb [SRC:README.md:L22-L25]. The argparse program name is `mason`, so help and
usage text print `mason …` [SRC:src/pyforge/mason/cli.py:L575-L580]. Run from the
repository root: CFE auto-discovery and manifest discovery start at the current
directory [SRC:src/pyforge/mason/cli.py:L1184-L1189] [SRC:src/pyforge/mason/cli.py:L1594-L1597].
`POST /stations/mason/mcp` is not a second route to the grammar: it runs one
supervised `recipe build` and nothing else (§ *Station MCP runner*).

```bash
pyforge mason self-check --format json
pyforge mason recipe validate RECIPE_PATH
pyforge mason package build PROJECT_PATH --target library
pyforge mason environment check [MANIFEST_PATH ...] --lockfile PATH
```

**self-check** [SRC:src/pyforge/mason/cli.py:L1171-L1191] — diagnoses the
installed Mason: version, CFE resolution, engine presence
[SRC:src/pyforge/mason/cli.py:L118]. It never raises and always exits
`EXIT_OK`; a missing CFE or engine is data in the degradation report, not a
command failure.

**recipe** — eight verbs that delegate to conda-forge-expert:
`new`, `validate`, `build`, `diagnose`, `optimize`, `scan`, `submit`,
`update` [SRC:src/pyforge/mason/cli.py:L628-L839]. `recipe update` writes the
version bump by default; `--dry-run` shows the plan and writes nothing
[SRC:src/pyforge/mason/cli.py:L810-L814]. `recipe build factory/recipes/<r>` builds
on the python-foundry factory island (§ *Layout*).

**package** — `build` and `ship`, built natively and CFE-independent for
`build` [SRC:src/pyforge/mason/cli.py:L852-L897].

**environment** — `lock` and `check` via conda-lock, CFE-independent
[SRC:src/pyforge/mason/cli.py:L916-L995].

<!-- [MANUAL:additional-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
**Outward work.** `--yes` on `package ship` and `recipe submit` publishes
outside this repository (PyPI, a conda channel, a staged-recipes PR). Run the
dry run; run `--yes` only on the operator's explicit ask. The rule is
`AGENTS.md` § Policy and the `outward-package-submission` entry of
`docs/governance/guild-roster.json` `session_denials`. The session hook
enforces it on Claude Code and Cursor only; on any other harness this note is
the guard.

**`--json` and `--version`.** `--json` is another spelling of `--format json`, taken wherever `--format` is (the
global flags and every noun and verb), not a seventh global flag: `pyforge.core.cli_output.align_json_options` adds it
when the parser is built, so source extraction does not see it (steward Story 144.1). `mason --version` prints the
version and exits 0.
<!-- [/MANUAL:additional-notes] -->

## Station MCP runner

What `POST /stations/mason/mcp` runs, as the code stands (`contract.md` § *MCP tool
and portal-job names* and § *The MCP face*; the host code is django-mason's
`mcp_asgi.py` and django-pyforge's closed verb table; this package ships no MCP
server) [SRC:README.md:L27-L33]:

| Name | Kind | What it does |
|---|---|---|
| `start_build` | MCP tool | Starts a supervised run and returns a handle. |
| `get_build` | MCP tool | Returns the supervisor's record of that run. |
| `run_build` | supervisor runner, not an MCP tool | Runs `pyforge mason recipe build recipes/<slug> --format json` in the `pyforge-mason` environment, for a recipe tracked in git; never started again on a redelivery; judged by `data.returncode`, the build's own code (Mason itself exits 1 when the build failed, under the same report, and the row takes that exit as a result). |
| `last_diagnose` | portal job | The `/stations/mason/` page's last diagnosis, read through `PortalClient`. |

The runner refuses while the kill switch `pyforge.steward.start_tool_cli` is off
(django-pyforge reads that key; Mason reads none). No other Mason verb is reachable
through the face: no `recipe new`, `validate`, `submit` or `update`, no `package`,
no `environment` and no `self-check`.

## Common Workflows

**Health check before any CFE-dependent verb:**
`pyforge mason self-check` → read CFE resolution in the report → then a `recipe` verb
[SRC:src/pyforge/mason/cli.py:L1177-L1182].

**Recipe gate in CI:** `pyforge mason recipe validate RECIPE_PATH` — the wrapped
validator's outcome is the exit code (`EXIT_OK` on pass, else `EXIT_FAILED`)
[SRC:src/pyforge/mason/cli.py:L1291-L1316], as the wrapped tool's is for `recipe build`, `diagnose`,
`optimize`, `scan` and `update` (§ *Dispatch rules*).

**Rehearse, then ship:** `pyforge mason package build PROJECT_PATH` →
`pyforge mason package ship --to pypi-test,pypi` (dry run) → add `--yes` to ship
for real [SRC:src/pyforge/mason/cli.py:L149-L153] [SRC:src/pyforge/mason/cli.py:L535-L540];
then read each `data.targets[].state` — exit 0 does not mean shipped.

**Lock, then gate staleness:** `pyforge mason environment lock -o LOCKFILE` →
`pyforge mason environment check --lockfile LOCKFILE` with the same
`--platform` list [SRC:src/pyforge/mason/cli.py:L983-L993].

**Submit a recipe:** `pyforge mason recipe submit RECIPE_DIR` (dry run) → add
`--yes` to push and open the PR, or `--prepare-only` to stop after the branch
push [SRC:src/pyforge/mason/cli.py:L136-L139] [SRC:src/pyforge/mason/cli.py:L777-L787].

## Key API Summary

| Command | Purpose | Key params |
|---|---|---|
| `self-check` | Version, CFE resolution, engine presence; always exit 0 | global flags only |
| `recipe new` | Generate a recipe via CFE | one of `--from-pypi/--from-github/--from-cran/--from-npm`, `--output/-o` |
| `recipe validate` | CFE validator; outcome is the exit code | `recipe_path` |
| `recipe build` | Native build; Docker for CI parity; a `factory/recipes/<r>` path builds on the factory island | `RECIPE_PATH`, `--docker` + `--config` |
| `recipe diagnose` | CFE failure analyzer on a log | `log_path` (not `-`) |
| `recipe optimize` | CFE recipe optimizer lint | `recipe_path` |
| `recipe scan` | CFE vulnerability scan of exact pins | `recipe_path` |
| `recipe submit` | CFE two-phase staged-recipes submission | `recipe_path` (directory), `--yes`, `--prepare-only` |
| `recipe update` | CFE autotick version bump; writes unless `--dry-run` | `recipe_path`, `--dry-run`, `--github`, `--repo`, `--pre` |
| `package build` | wheel + sdist (PEP 517) and `.conda` (pixi build) | `PROJECT_PATH`, `--target library` |
| `package ship` | Ship to targets; dry run by default | `--to TARGETS`, `--yes`, `--recipe-path` |
| `environment lock` | Manifests to one lockfile via conda-lock | `MANIFEST_PATH...`, `--output/-o`, `--platform` |
| `environment check` | Lockfile staleness gate | `MANIFEST_PATH...`, `--lockfile/-l`, `--platform` |
| `main` | Entry point; sole owner of the exit code | `argv` |
| `build_parser` | Builds the `mason` noun → verb parser | — |

Sources: help strings [SRC:src/pyforge/mason/cli.py:L113-L163]; registrations
[AST:src/pyforge/mason/cli.py:L568-L1001]; `main`
[AST:src/pyforge/mason/cli.py:L1145].

<!-- [MANUAL:api-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:api-notes] -->

## Key Exports

`__all__` is `["__version__"]` [SRC:src/pyforge/mason/__init__.py:L13]. The
SKF public-API extract of `cli.py` adds `build_parser`
[AST:src/pyforge/mason/cli.py:L568] and `main`
[AST:src/pyforge/mason/cli.py:L1145]. These three are the whole importable
surface; everything else under `pyforge.mason` is internal.

## Usage

Invoke Mason as `pyforge mason …`; never import `pyforge.mason` internals
[SRC:README.md:L22-L25]. Global flags parse before or after the noun, so
`pyforge mason --format json recipe …` and `pyforge mason recipe … --format json`
are equivalent [SRC:src/pyforge/mason/cli.py:L569-L573]. For recipe content —
what a recipe should contain and why a build fails — consult
[conda-forge-expert](../../../conda-forge-expert/SKILL.md) first; Mason's
`recipe` verbs only run that skill's tools [SRC:README.md:L18-L23].

## Key Types

**Global flags** — AD-13's closed set of six, accepted before or after the noun
and verb; each resolves flag → environment → default
[SRC:src/pyforge/mason/cli.py:L385-L443] [SRC:src/pyforge/mason/cli.py:L165-L173]:

| Flag | Environment | Default |
|---|---|---|
| `--cfe-root PATH` | `MASON_CFE_ROOT` | auto-discovery |
| `--cfe-python PATH` | `MASON_CFE_PYTHON` | running interpreter |
| `--cfe-timeout SECONDS` | `MASON_CFE_TIMEOUT` | none (finite, positive) |
| `--format {text,json}` | `MASON_FORMAT` | `text` |
| `--verbose` | `MASON_VERBOSE` | off |
| `--quiet` | `MASON_QUIET` | off; wins over `--verbose` |

**The other two `MASON_` variables** have no flag form (the six-flag set is closed)
[SRC:src/pyforge/mason/resolve.py:L235-L242]: `MASON_FOUNDRY_ROOT` is read by
`recipe build` on a `factory/recipes/<r>` path as the python-foundry root, before the
walk up for `factory/pixi.toml` with `factory/pixi.lock`, and is set for the CFE
build child; `MASON_FACTORY_ROOT` is set to `<foundry>/factory` for that child, and
the adapter reads it back from the child's environment to report `artifact_dir`.

**Exit codes** — `exit_codes.py` is the one owner; `main()` alone returns them
and a verb never calls `sys.exit()` [SRC:src/pyforge/mason/exit_codes.py:L1-L13]
[SRC:src/pyforge/mason/cli.py:L108-L111]:

| Name | Value | When |
|---|---|---|
| `EXIT_OK` | 0 | The command ran, and the tool it wraps, if any, returned 0. For a ship verb no target is `failed`, which does not mean shipped: read each target's `state` (see *Ship states*) |
| `EXIT_FAILED` | 1 | A `MasonError` other than `cfe:unresolved`, or an unanticipated exception (traceback on stderr); or a verb whose wrapped tool returned non-zero: `recipe validate`, `build`, `diagnose`, `optimize`, `scan` and `update`, `package build` (either engine) and `environment lock`; `environment check` (stale or failed); or a ship state of `failed` (`recipe submit`, or any target of `package ship`). Mason does not interpret the code: a CFE script that exits non-zero to report a finding (a vulnerability, an optimizer suggestion) exits 1 here too. The envelope's `status` stays `ok` |
| `EXIT_USAGE` | 2 | A bare noun with no verb, an argparse-rejected invocation, a `SystemExit` with a non-integer payload |
| `EXIT_CFE_UNAVAILABLE` | 3 | The CFE root could not be resolved for a CFE-dependent command (`cfe:unresolved`) |
| `EXIT_INTERRUPTED` | 130 | A keyboard interrupt (128 + SIGINT) |

[SRC:src/pyforge/mason/exit_codes.py:L17-L40] An unresolved CFE root maps to
`EXIT_CFE_UNAVAILABLE` [SRC:src/pyforge/mason/cli.py:L1687-L1696]; any other
`MasonError` maps to `EXIT_FAILED` [SRC:src/pyforge/mason/cli.py:L1697-L1702];
argparse's own `SystemExit` passes its code through (0 for `--help` and
`--version`, 2 for a usage error) [SRC:src/pyforge/mason/cli.py:L1680-L1686].

**JSON output** — under `--format json` stdout carries exactly one JSON document or
nothing, and every diagnostic goes to stderr. The envelope has exactly five keys,
rendered with sorted keys [SRC:src/pyforge/mason/render.py:L20-L24]
[SRC:src/pyforge/mason/render.py:L52-L58]:

- `schema_version`: `"1"`.
- `command`: the path without `mason` (`"recipe build"`, `"package ship"`,
  `"self-check"`); `"mason"` when the failure comes before the arguments are parsed.
- `status`: `"ok"` when the command ran, whatever the delegated tool did; `"error"`
  when a `MasonError` was raised.
- `data`: the command's result. A delegated tool's return code is data, never an
  error: `data.returncode` (`recipe build`, `environment lock`, `environment check`
  and each verb that wraps a CFE script; `package build` carries
  `data.pep517_returncode` and `data.pixi_returncode`). A non-zero one leaves
  `status` `ok` and `errors` `[]`, and makes the process exit 1
  [SRC:src/pyforge/mason/cli.py:L1356-L1362] [SRC:src/pyforge/mason/cli.py:L1565]. `package ship` puts its results in
  `data.targets[]`, each `{target, state, reference, message}`
  [SRC:src/pyforge/mason/cli.py:L1108-L1116]; `recipe submit` returns one such result
  as `data`. `self-check` puts `mason_version`, `cfe_root`, `cfe_root_step`,
  `cfe_interpreter`, `cfe_interpreter_step`, `cfe_import_floor_satisfied`,
  `cfe_import_floor_missing`, `unavailable_verbs`, `engines` (each `{name, available,
  version}`), `conda_forge_ship_ready` and `conda_forge_ship_blockers`
  [AST:src/pyforge/mason/models.py:L142-L162]. An error envelope has `data` `{}`.
- `errors`: `[]`, or `[{"identifier": …, "message": …}]` for the `MasonError` raised;
  stderr also carries `identifier: message` [SRC:src/pyforge/mason/cli.py:L1119-L1142].

`--format text` is a human summary and is not a contract.

**Ship states** (mason's AD-9) [AST:src/pyforge/mason/models.py:L194-L221] — every ship
target result is in one of four states: `not_attempted` (no `--yes`, a dry run;
nothing was pushed, uploaded or opened; also a `pypi` target whose `pypi-test`
rehearsal did not reach `terminal`), `pending` (a confirmed attempt started something
real not yet confirmed — a conda-forge pull request opened or its branch pushed — or
the target could not be interrogated, so no upload was made), `terminal` (the target
reached its end state: uploaded, or the version was already there) and `failed` (a
confirmed attempt did not succeed, or a precondition refused it). `package ship` exits
1 only when a target is `failed`, and `recipe submit` exits 1 only when its one result
is `failed`; `not_attempted`, `pending` and `terminal` all exit 0
[SRC:src/pyforge/mason/cli.py:L1116] [SRC:src/pyforge/mason/cli.py:L1500]. **Exit 0 does not mean shipped**: read
`data.targets[].state` (or `data.state` for `recipe submit`). `pending` is never
rendered as success.

## Architecture at a Glance

- **recipe** — wraps conda-forge-expert by subprocess; never forked
  [SRC:src/pyforge/mason/cli.py:L8-L12].
- **package** — built natively; no wheel-build/upload path exists to wrap
  [SRC:src/pyforge/mason/cli.py:L13].
- **environment** — built natively; no lock orchestration exists to wrap
  [SRC:src/pyforge/mason/cli.py:L14].
- **self-check** — top-level leaf with no verb level [SRC:src/pyforge/mason/cli.py:L613-L619].
- **CLI** — argparse, not click/typer (FR-41 forbids a CLI-framework dependency)
  [SRC:src/pyforge/mason/cli.py:L79-L80].

## CLI

```text
pyforge mason [global flags] self-check
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

MCP: `POST /stations/mason/mcp` runs `recipe build` only [SRC:README.md:L27-L33].

## Full API Reference

### Dispatch rules

- A bare `pyforge mason` prints help and exits `EXIT_OK`
  [SRC:src/pyforge/mason/cli.py:L1165-L1169].
- A noun with no verb prints that noun's help on stderr and exits `EXIT_USAGE`
  [SRC:src/pyforge/mason/cli.py:L1242-L1249]. The one exception is
  `package --ship TARGETS`, the bare-noun alias of `package ship --to`
  [SRC:src/pyforge/mason/cli.py:L884-L893].
- `--ship` together with an explicit `package` verb is a usage error
  [SRC:src/pyforge/mason/cli.py:L1193-L1214].
- A delegated tool's non-zero return code is data on the result, not a raised
  error; the envelope `status` stays `ok` [SRC:src/pyforge/mason/cli.py:L1356-L1362], and the exit code
  projects it, without interpreting it: `EXIT_FAILED` for `recipe validate`
  [SRC:src/pyforge/mason/cli.py:L1316], `build` [SRC:src/pyforge/mason/cli.py:L1362], `diagnose`
  [SRC:src/pyforge/mason/cli.py:L1410], `optimize` [SRC:src/pyforge/mason/cli.py:L1439], `scan`
  [SRC:src/pyforge/mason/cli.py:L1465] and `update` [SRC:src/pyforge/mason/cli.py:L1547], `package build`
  when either engine failed [SRC:src/pyforge/mason/cli.py:L1565], `environment lock`
  [SRC:src/pyforge/mason/cli.py:L1616] and `environment check` (stale or failed)
  [SRC:src/pyforge/mason/cli.py:L1664]. `recipe submit` [SRC:src/pyforge/mason/cli.py:L1500] and `package ship`
  [SRC:src/pyforge/mason/cli.py:L1116] exit `EXIT_FAILED` on a `failed` ship state; a dry run
  (`not_attempted`) exits `EXIT_OK` whatever its wrapped script returned.

### recipe

| Verb | Arguments | Constraints |
|---|---|---|
| `new` | `--from-pypi PACKAGE` / `--from-github OWNER/REPO` / `--from-cran PACKAGE` / `--from-npm PACKAGE` (exactly one, required); `--output/-o PATH` (required) | [SRC:src/pyforge/mason/cli.py:L634-L666] |
| `validate` | `recipe_path` — recipe file or its directory | exit code follows the validator [SRC:src/pyforge/mason/cli.py:L686-L689] |
| `build` | `RECIPE_PATH` (a file or directory, or `factory/recipes/<r>`); `--docker`; `--config CONFIG` | `--docker` and `--config` require each other; a blank `--config` counts as absent [SRC:src/pyforge/mason/cli.py:L1327-L1340] |
| `diagnose` | `log_path` | `-` (stdin) is refused with `EXIT_USAGE` [SRC:src/pyforge/mason/cli.py:L1384-L1389] |
| `optimize` | `recipe_path` | passed through to CFE unchecked [SRC:src/pyforge/mason/cli.py:L731-L745] |
| `scan` | `recipe_path` | scans exact pins only; calls `api.osv.dev` by default [SRC:src/pyforge/mason/cli.py:L131-L135] |
| `submit` | `recipe_path` (the recipe directory, not a file); `--yes`; `--prepare-only` | dry run unless `--yes` [SRC:src/pyforge/mason/cli.py:L771-L787] |
| `update` | `recipe_path`; `--dry-run`; `--github`; `--repo OWNER/REPO`; `--pre` | writes unless `--dry-run`; `--repo`/`--pre` are ignored with a warning unless `--github` [SRC:src/pyforge/mason/cli.py:L1521-L1522] |

`update`'s `recipe_path` must be a v1 `recipe.yaml`; with `--github` a
directory is also accepted [SRC:src/pyforge/mason/cli.py:L804-L809].

### package

| Verb | Arguments | Constraints |
|---|---|---|
| `build` | `PROJECT_PATH`; `--target {library}` (default `library`) | never reads CFE flags [SRC:src/pyforge/mason/cli.py:L1549-L1569] |
| `ship` | `--to TARGETS` (required); `--yes`; `--target library`; `--recipe-path RECIPE_PATH` | targets: `pypi`, `pypi-test`, `conda-forge`, `channel:NAME`, comma-separated in one value; a repeated `--to` is a usage error [SRC:src/pyforge/mason/cli.py:L549-L556] |

`pypi-test` named alongside `pypi` always runs first and gates it
[SRC:src/pyforge/mason/cli.py:L149-L153]. `--recipe-path` matters only for the
`conda-forge` target [SRC:src/pyforge/mason/cli.py:L541-L548]. `ship` exits
`EXIT_FAILED` when any target result is `failed`, else `EXIT_OK`; an unresolved
CFE root becomes a `failed` target, not exit 3
[SRC:src/pyforge/mason/cli.py:L1076-L1091].

### environment

| Verb | Arguments | Constraints |
|---|---|---|
| `lock` | `MANIFEST_PATH...` (optional); `--output/-o PATH` (required); `--platform PLATFORMS` | exit `EXIT_FAILED` when conda-lock fails [SRC:src/pyforge/mason/cli.py:L916-L944] |
| `check` | `MANIFEST_PATH...` (optional); `--lockfile/-l PATH` (required, never written); `--platform PLATFORMS` | exit `EXIT_FAILED` when stale or when the check fails [SRC:src/pyforge/mason/cli.py:L963-L993] |

Manifests: `pyproject.toml`, `environment.yml`, `requirements*.txt`,
`pixi.toml`; omit them to auto-discover in the current directory, and the
discovered list prints to stderr [SRC:src/pyforge/mason/cli.py:L926-L927]
[SRC:src/pyforge/mason/cli.py:L1594-L1597]. Pass `check` the same
`--platform` list the lockfile was locked with; conda-lock's own default
reports a narrower lockfile as stale [SRC:src/pyforge/mason/cli.py:L983-L993].

### Layout

Mason assumes this layout and creates none of it (`contract.md` § *Layout*). A
factory-island build, `recipe build factory/recipes/<r>` (or `./factory/recipes/<r>`;
never `../factory/…` or an absolute path) [AST:src/pyforge/mason/resolve.py:L260-L268],
needs `<foundry>/factory/pixi.toml`, `<foundry>/factory/pixi.lock` and
`<foundry>/factory/recipes/<r>`, with `<foundry>` from `MASON_FOUNDRY_ROOT` or the
walk up from the current directory [AST:src/pyforge/mason/resolve.py:L302-L315]; a
path that maps to no island raises `factory:missing-island`. The island is wired for
the native build; `--docker` on an island path is recorded, not built. Island
artifacts are reported under `<foundry>/factory/build_artifacts/<config>`, any other
build's under `build_artifacts/<config>`.

### Python entry points

- `main(argv: Sequence[str] | None = None) -> int` — parses, configures
  logging, dispatches, maps outcomes to exit codes; catches
  `KeyboardInterrupt`, `SystemExit`, `CfeUnresolvedError`, `MasonError` and any
  other exception [AST:src/pyforge/mason/cli.py:L1145-L1707]. It replaces root
  logging handlers (`force=True`), so it is not safe to call in-process from a
  host that owns the root logger [SRC:src/pyforge/mason/cli.py:L359-L369].
- `build_parser() -> argparse.ArgumentParser` — the full noun → verb tree
  [AST:src/pyforge/mason/cli.py:L568-L1001].
- `__version__: str` — installed distribution version, or `0.1.0+source` from a
  source tree [SRC:src/pyforge/mason/__init__.py:L16-L25].
