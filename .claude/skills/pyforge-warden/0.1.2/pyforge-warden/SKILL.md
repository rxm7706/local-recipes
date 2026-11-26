---
name: pyforge-warden
description: >
  Runs the warden dependency-hygiene and vulnerability gate via the warden
  CLI (scan / scan --self-check). Use when scanning Python/Conda/Pixi manifests,
  checking the scanner environment, or working in src/shared/packages/pyforge-warden/.
  Do not import pyforge.warden internals; the CLI is the public contract.
  Do not invent a second PR-gate verdict. Do not use for conda-forge recipe
  authoring (conda-forge-expert) or station personas.
---

# pyforge-warden

## Overview

Compiles `src/shared/packages/pyforge-warden/` (PyPI `pyforge-warden` 0.1.0) as an
agentskills.io content skill for the **warden** station. Source: local path
`src/shared/packages/pyforge-warden` @ commit `4c72fc94de`, read as it stands (`source_ref: local`).
Forge tier: **Forge** (SKF `skf-extract-public-api` over ast-grep 0.45.3; T1).
First compiled from `865b95dc951` (Story 10.1); recompiled in place at 0.1.0 on
2026-11-12 (steward Story 29.5, the fixes the EGM audit of 2026-11-05 accepted:
WAR-R-F1, WAR-R-F2, WAR-R-F4) from the current package, the station contract
`contract.md` as a doc source, and the real `warden --help`, the way Story 29.1 and
atlas Stories 33.1 and 33.2 did.
Rebuilt as 0.1.1 on 2026-11-25 (steward Story 136.10) with `skf-update-skill` at Forge
tier over ast-grep 0.45.3, at `5f22584869`: the first Forge-tier build, over the whole
scope the brief names, with the requirement and capability ids cited in qualified form.
Updated to 0.1.2 on 2026-11-26 by `skf-update-skill`, from the package as it stands at
`4c72fc94de`: the environment self-check is `scan --self-check`, and its old spelling,
the doctor station's name, is gone from the CLI; the citations follow the moved lines.
9 exports documented (6 at T1; at T1-low `_run_scan` and `_run_doctor`, private and
read by eye, and the signature of `match_level_rung`, carried from the 0.1.0 map): the
CLI entry `main` in `cli.py`, the report assembly and its
two renderers (`assemble_report`, `render_json`, `render_text`) in `report.py`
(§ *Full API Reference*), and the verdict projection (`compose`, `exit_code_for`,
`match_level_rung`), owned by `verdict.py`
[SRC:src/pyforge/warden/verdict.py:L1-L21]. **Agents invoke warden through the
CLI or its MCP face and do not import `pyforge.warden` or call its verdict
functions**: the CLI is the sole PR-gate publisher, and an agent that computes a
verdict itself publishes a second PR-gate. The package `__init__.py` exports only
`__version__` [SRC:src/pyforge/warden/__init__.py:L12].

## Description

Unified dependency-hygiene + vulnerability scanner that orchestrates deptry
and osv-scanner over Python / Conda / Pixi manifests, emitting one
schema-validated `ComplianceReport` and a strict CI/CD exit-code gate
[SRC:pyproject.toml:L8].

**The public contract** is
`_bmad-output/projects/pyforge-warden/planning-artifacts/specs/spec-pyforge-warden/contract.md`
(spec-pyforge-warden:CAP-28): the CLI verb and every flag, the
`[tool.pyforge-warden]` keys, the exit codes, status rungs, error kinds and finding
ids, the feature flags per environment, the environment variables and the MCP tools
[SRC:README.md:L11-L17]. The MCP tool names, exit codes, rungs and flag keys in this
skill are rows of that file; where they differ, the contract and the code win.

## Quick Start

Run from the repository root (never a hardcoded absolute path)
[SRC:README.md:L21-L27]:

```bash
pixi run -e pyforge-warden warden scan --self-check
pixi run -e pyforge-warden warden scan .
pixi run -e pyforge-warden warden scan . --warn-only
```

canopy:FR-13 unified dispatch (same argv after the station token)
[SRC:src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py:L158-L164]:

```bash
pyforge warden scan .
pyforge warden scan --self-check
```

**Scan** (`warden scan [path]`) [SRC:src/pyforge/warden/cli.py:L454-L460]:
scan a project directory and emit the compliance report. Default path is `.`.
`--format json` puts exactly one schema-valid report on stdout
[SRC:src/pyforge/warden/cli.py:L461-L470]; every diagnostic goes to stderr.

**Self-check** (`warden scan --self-check`) [SRC:src/pyforge/warden/cli.py:L661-L672]:
environment self-check only (engines, the offline OSV database, the KEV, EPSS and
end-of-life feed caches; no discovery, no network). Exits 0 when healthy else 2;
never 1 — the self-check reports operability, not policy. **Run it first**: a scan can only
assess what the environment can assess [SRC:README.md:L66-L80].

**`--warn-only`** [SRC:src/pyforge/warden/cli.py:L642-L660] downgrades every
still-blocking rung (`policy-violation`, `indeterminate`) to `warn` before the verdict
composes, so the run exits 0 — the non-blocking on-ramp for adopting the gate over a
repo's existing findings. **Caveat** [SRC:README.md:L55-L64]: a missing or
out-of-range engine still exits 2 under `--warn-only`, but an unprovisioned offline
OSV database does not: the vulnerability axis composes `indeterminate` findings,
which `--warn-only` downgrades like any other, leaving that axis silently unassessed.
A green `--warn-only` run is not a clean vulnerability verdict; run `warden scan
--self-check` first. With `--warn-as-error` the downgraded `warn` still exits 1.

<!-- [MANUAL:additional-notes] -->
The CLI (via `verdict.exit_code_for`) is the sole PR-gate publisher. Do not
recompute status or exit codes. Do not import `pyforge.warden`.

**`--json`.** Every verb that takes `--format {text,json}` also takes `--json`, another spelling of `--format json`
(`pyforge.core.cli_output.align_json_options` adds it when the parser is built, so source extraction does not see it;
steward Story 144.1). `scan --self-check` also reports the advisory `tea` check (tea-test-review) beside the engines,
the OSV database and the KEV, EPSS and end-of-life feeds. Its JSON document keeps the key `"doctor": true`.
<!-- [/MANUAL:additional-notes] -->

## Station MCP runner

What `POST /stations/warden/mcp` runs, as the code stands (`contract.md` § 6; the
face is django-warden's `mcp_asgi.py`, the runner a row of django-pyforge's closed
verb table; this package ships no MCP server):

| Tool | Arguments | Returns |
|---|---|---|
| `start_audit` | `target`, `assertion` | A handle, at once. |
| `get_audit` | `handle`, `assertion` | The supervisor run for that handle. |

`start_audit` hands the supervisor runner `run_audit`: `warden scan <target> --format
json` in the `pyforge-warden` environment, where the target is a directory under the
checkout (the portal's default is `src/platform`), passing
`OSV_SCANNER_LOCAL_DB_CACHE_DIRECTORY` and `PYFORGE_WARDEN_FEED_CACHE_DIR` through.
Exits 0 and 1 are a result; 2 is an audit that did not finish. It runs that one scan
and nothing else: no `--self-check`, no `--bypass`, no `--open-fix-prs`, and none of the
fleet management commands.

## Common Workflows

**Default gate:** `warden scan .` → `main` [AST:src/pyforge/warden/cli.py:L756]
→ `_run_scan` [SRC:src/pyforge/warden/cli.py:L1049]. The exit code comes only from
`exit_code_for` [AST:src/pyforge/warden/verdict.py:L111].

**Adopt without blocking:** `warden scan --self-check`, then `warden scan . --warn-only`.

**Prove the install:** `warden scan --self-check` → `_run_doctor`
[SRC:src/pyforge/warden/cli.py:L848].

## Key API Summary

| Function | Purpose | Key params |
|---|---|---|
| `main` | argparse entry (`warden` console script) | `argv` after the script name |
| `_run_scan` | project scan + report emission | parsed `scan` args |
| `_run_doctor` | environment self-check | parsed `scan` args with `--self-check` |
| `compose` | lattice compose (CLI-owned; agents do not call it) | rungs, each a status with its driver |
| `exit_code_for` | exit projection (CLI-owned; agents do not call it) | status, `warn_is_error`, `driver`, `allow_empty` |
| `match_level_rung` | CVE-match → rung (CLI-owned; agents do not call it) | level |
| `assemble_report` | builds the `ComplianceReport` from the pipeline's outputs (CLI-owned; agents do not call it) | keyword-only: inventory, findings, rungs, errors, the manifest counts, `vuln_data` |
| `render_json` | the one schema-valid JSON document `--format json` prints (CLI-owned) | report |
| `render_text` | the non-contract text summary (CLI-owned) | report, the waiver and baseline notices, `warn_only` |

## Key Exports

Public SKF extract over the brief's scope (Forge tier, ast-grep): `main`
[AST:src/pyforge/warden/cli.py:L756]; `compose`, `exit_code_for` and
`match_level_rung` in `verdict.py`; `assemble_report`, `render_json` and
`render_text` in `report.py`. Console script:
`warden = pyforge.warden.cli:main` [SRC:pyproject.toml:L30-L31].

## Usage

Always invoke `warden` (or `pyforge warden`) from repo root. Agents do not
`from pyforge.warden import compose` / `exit_code_for` — not in another station,
not in a persona. The persona relays CLI/MCP output; it does not publish a
second PR-gate verdict.

`--self-check` is a flag on `scan`, not a second subcommand
[SRC:src/pyforge/warden/cli.py:L661].

Exit codes (`contract.md` § 3.1; a closed set, `verdict.py` the sole owner)
[SRC:src/pyforge/warden/verdict.py:L43-L50]:

| Exit | Means |
|---|---|
| `0` | `clean`, `warn`, `bypassed` or `not-applicable`; the sanctioned downgrades (`--allow-empty`, `--warn-only`); a healthy `--self-check`; `--version`, `--help` |
| `1` | `policy-violation` or `indeterminate`; a `warn` under `--warn-as-error` |
| `2` | `error`: an operational failure (one of nine typed error kinds), a usage error, or an unhealthy `--self-check` |
| `130` | interrupted (SIGINT) |

The **knobs** that move a projection without touching the lattice
[AST:src/pyforge/warden/verdict.py:L111-L146]: `--warn-as-error` (`warn_is_error`)
makes a composed `warn` exit 1; `--allow-empty` (`allow_empty`) exits 0 on the one
empty-extraction `indeterminate` while the status stays `indeterminate`;
`--warn-only` downgrades blocking rungs to `warn` before composing. `--fail-on`,
`--fail-under-coverage`, the licence and currency flags and `--min-epss` decide which
findings compose which rung; each has a `[tool.pyforge-warden]` key (`contract.md`
§ 2).

## Key Types

**`Status`** — the seven-rung lattice owned by `verdict.py`
[SRC:src/pyforge/warden/verdict.py:L3-L9], strongest first, with its exit:
`error` (2), `policy-violation` (1), `indeterminate` (1), `warn` (0), `bypassed` (0),
`clean` (0), `not-applicable` (0). Other modules feed rungs; only `verdict.py`
projects exit codes.

**`ComplianceReport`** — schema-validated stdout contract under `--format json`
(schema `urn:local-recipes:pyforge-warden:report-schema`, frozen at 1.1.0)
[SRC:src/pyforge/warden/cli.py:L31-L33] [SRC:src/pyforge/warden/report.py:L192] [SRC:src/pyforge/warden/data/report-schema.json:L3].

## Architecture at a Glance

- **CLI** — sole public contract; `prog` is `warden` [SRC:src/pyforge/warden/report.py:L193] [SRC:src/pyforge/warden/cli.py:L446].
- **Scan** — discovery → extract → engines → policy → report.
- **Verdict** — sole owner of lattice + exit projection
  [SRC:src/pyforge/warden/verdict.py:L1-L21].
- **Self-check** — operability, never a project policy verdict
  [SRC:src/pyforge/warden/cli.py:L661-L672].

## CLI

```text
warden --version
warden scan [path] [--format text|json] [--warn-only] [--self-check]
warden scan [path] [--fail-on TIER] [--fail-under-coverage N] [--warn-as-error] [--allow-empty]
warden scan [path] [--allow-licenses IDS] [--deny-licenses IDS] [--max-lag N] [--require-lts] [--fail-on-eol] [--min-epss N]
warden scan [path] [--baseline PATH] [--baseline-emit] [--bypass --reason TEXT]
warden scan [path] [--sbom-output PATH] [--deterministic] [--pixi-environment NAME] [--pixi-platform PLATFORM]
warden scan [path] [--open-fix-prs] [--fix-prs-dry-run]
pyforge warden scan [path]
pyforge warden scan --self-check
```

`[project.scripts]` name is `warden`; canopy:FR-13 grammar is `pyforge warden …`
(never a second public grammar that skips `pyforge`).

<!-- [MANUAL:api-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:api-notes] -->

## Full API Reference

The 7 functions the extract found and the 2 private ones read by eye, as the source
declares them, for reading the code. Agents, other stations and `src/platform/` do not
import them: the CLI is the contract (§ *Usage*).

### `cli.py`

- `main(argv: list[str] | None = None) -> int` — the `warden` console script's entry;
  the source gives it no docstring. [AST:src/pyforge/warden/cli.py:L756]
- `_run_doctor(args: argparse.Namespace) -> int` — private; the environment self-check
  behind `scan --self-check`. [SRC:src/pyforge/warden/cli.py:L848]
- `_run_scan(args: argparse.Namespace) -> int` — private; the project scan and the
  report it emits. [SRC:src/pyforge/warden/cli.py:L1049]

### `report.py`

- `assemble_report(*, inventory: ResolvedInventory, findings: Sequence[Finding], rungs:
  Iterable[tuple[Status | str, StatusDriver | None]], errors: Sequence[ErrorRecord],
  manifests_found: int, manifests_parsed: int, vuln_data: VulnData, engine_results:
  Sequence[EngineResult] = (), has_locked_closure: bool = False, hygiene_applicable: bool =
  True, allow_empty: bool = False, empty_extraction: bool = False, fail_under_coverage:
  float = 0.0, suppressions: Sequence[SuppressedFinding] = (), kev_data: FeedProvenance |
  None = None, epss_data: FeedProvenance | None = None, license_gating: bool = False,
  currency_data: FeedProvenance | None = None, currency_gating: bool = False,
  warn_as_error: bool = False, actuation: object | None = None, advisory: object | None =
  None) -> ComplianceReport` — Assemble the `ComplianceReport` from the pipeline's
  outputs. [AST:src/pyforge/warden/report.py:L208]
- `render_json(report: ComplianceReport) -> str` — Render the report as ONE
  deterministic, schema-valid JSON document. [AST:src/pyforge/warden/report.py:L498]
- `render_text(report: ComplianceReport, *, applied_waivers: Sequence[WaiverNotice] = (),
  expired_waivers: Sequence[WaiverNotice] = (), applied_baseline: Sequence[BaselineNotice]
  = (), expired_baseline: Sequence[BaselineNotice] = (), warn_only: bool = False,
  warn_only_downgraded: int = 0, actuation: object | None = None, advisory: object | None
  = None, manifest_locations: Mapping[str, tuple[str, ...]] = MappingProxyType({}),
  fixed_versions: Mapping[str, str] = MappingProxyType({})) -> str` — Render the report
  as a human-readable, explicitly NON-CONTRACT summary.
  [AST:src/pyforge/warden/report.py:L689]

### `verdict.py`

- `compose(rungs: Iterable[tuple[Status | str, StatusDriver | None]]) -> tuple[Status,
  StatusDriver | None]` — Compose fed rungs: the highest rung wins and its driver
  propagates. [AST:src/pyforge/warden/verdict.py:L71]
- `exit_code_for(status: Status | str, *, warn_is_error: bool = False, driver:
  StatusDriver | None = None, allow_empty: bool = False) -> int` — Project a status to
  its exit code — TOTAL over all 7 rungs (C0a). [AST:src/pyforge/warden/verdict.py:L111]
- `match_level_rung(level: CveMatchLevel | str) -> Status` — Rung for a CVE-match level:
  `exact` -> `clean`; `name-only`, `none`, and ANY unrecognized future value ->
  `indeterminate`. [AST:src/pyforge/warden/verdict.py:L149]
