---
name: pyforge-warden
description: >
  Runs the warden dependency-hygiene and vulnerability gate via the warden
  CLI (scan / scan --doctor). Use when scanning Python/Conda/Pixi manifests,
  checking the scanner environment, or working in src/shared/packages/pyforge-warden/.
  Do not import pyforge.warden internals; the CLI is the public contract.
  Do not invent a second PR-gate verdict. Do not use for conda-forge recipe
  authoring (conda-forge-expert) or station personas.
---

# pyforge-warden

## Overview

Compiles `src/shared/packages/pyforge-warden/` (PyPI `pyforge-warden` 0.1.0) as an
agentskills.io content skill for the **warden** station. Source: local path
`src/shared/packages/pyforge-warden` @ commit `b69fd81eb8` (`source_ref: local`).
Forge tier: **Quick** (SKF `skf-extract-public-api` + source-reading; T1-low).
First compiled from `865b95dc951` (Story 10.1); recompiled in place at 0.1.0 on
2026-11-12 (steward Story 29.5, the fixes the EGM audit of 2026-11-05 accepted:
WAR-R-F1, WAR-R-F2, WAR-R-F4) from the current package, the station contract
`contract.md` as a doc source, and the real `warden --help`, the way Story 29.1 and
atlas Stories 33.1 and 33.2 did.
CLI export documented (`main`). The verdict projection (`compose`, `exit_code_for`,
`match_level_rung`) is owned by `verdict.py`
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
[SRC:README.md:L21-L25]:

```bash
pixi run -e pyforge-warden warden scan --doctor
pixi run -e pyforge-warden warden scan .
pixi run -e pyforge-warden warden scan . --warn-only
```

FR-13 unified dispatch (same argv after the station token)
[SRC:src/shared/packages/pyforge-core/src/pyforge/core/dispatch.py:L154-L160]:

```bash
pyforge warden scan .
pyforge warden scan --doctor
```

**Scan** (`warden scan [path]`) [SRC:src/pyforge/warden/cli.py:L449-L455]:
scan a project directory and emit the compliance report. Default path is `.`.
`--format json` puts exactly one schema-valid report on stdout
[SRC:src/pyforge/warden/cli.py:L457-L465]; every diagnostic goes to stderr.

**Doctor** (`warden scan --doctor`) [SRC:src/pyforge/warden/cli.py:L657-L666]:
environment self-check only (engines, the offline OSV database, the KEV, EPSS and
end-of-life feed caches; no discovery, no network). Exits 0 when healthy else 2;
never 1 — doctor reports operability, not policy. **Run it first**: a scan can only
assess what the environment can assess [SRC:README.md:L64-L78].

**`--warn-only`** [SRC:src/pyforge/warden/cli.py:L639-L655] downgrades every
still-blocking rung (`policy-violation`, `indeterminate`) to `warn` before the verdict
composes, so the run exits 0 — the non-blocking on-ramp for adopting the gate over a
repo's existing findings. **Caveat** [SRC:README.md:L53-L62]: a missing or
out-of-range engine still exits 2 under `--warn-only`, but an unprovisioned offline
OSV database does not: the vulnerability axis composes `indeterminate` findings,
which `--warn-only` downgrades like any other, leaving that axis silently unassessed.
A green `--warn-only` run is not a clean vulnerability verdict; run `warden scan
--doctor` first. With `--warn-as-error` the downgraded `warn` still exits 1.

<!-- [MANUAL:additional-notes] -->
The CLI (via `verdict.exit_code_for`) is the sole PR-gate publisher. Do not
recompute status or exit codes. Do not import `pyforge.warden`.
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
and nothing else: no `--doctor`, no `--bypass`, no `--open-fix-prs`, and none of the
fleet management commands.

## Common Workflows

**Default gate:** `warden scan .` → `main` [SRC:src/pyforge/warden/cli.py:L750]
→ `_run_scan` [SRC:src/pyforge/warden/cli.py:L1041]. The exit code comes only from
`exit_code_for` [SRC:src/pyforge/warden/verdict.py:L109].

**Adopt without blocking:** `warden scan --doctor`, then `warden scan . --warn-only`.

**Prove the install:** `warden scan --doctor` → `_run_doctor`
[SRC:src/pyforge/warden/cli.py:L842].

## Key API Summary

| Function | Purpose | Key params |
|---|---|---|
| `main` | argparse entry (`warden` console script) | `argv` after the script name |
| `_run_scan` | project scan + report emission | parsed `scan` args |
| `_run_doctor` | environment self-check | parsed `scan` args with `--doctor` |
| `compose` | lattice compose (CLI-owned; agents do not call it) | rungs |
| `exit_code_for` | exit projection (CLI-owned; agents do not call it) | status, `warn_is_error`, `allow_empty` |
| `match_level_rung` | CVE-match → rung (CLI-owned; agents do not call it) | level |

## Key Exports

Public SKF extract of `cli.py` (Quick mode): `main`
[SRC:src/pyforge/warden/cli.py]. Console script:
`warden = pyforge.warden.cli:main` [SRC:pyproject.toml:L30-L31].

## Usage

Always invoke `warden` (or `pyforge warden`) from repo root. Agents do not
`from pyforge.warden import compose` / `exit_code_for` — not in another station,
not in a persona. The persona relays CLI/MCP output; it does not publish a
second PR-gate verdict.

`--doctor` is a flag on `scan`, not a second subcommand
[SRC:src/pyforge/warden/cli.py:L657].

Exit codes (`contract.md` § 3.1; a closed set, `verdict.py` the sole owner)
[SRC:src/pyforge/warden/verdict.py:L42-L52]:

| Exit | Means |
|---|---|
| `0` | `clean`, `warn`, `bypassed` or `not-applicable`; the sanctioned downgrades (`--allow-empty`, `--warn-only`); a healthy `--doctor`; `--version`, `--help` |
| `1` | `policy-violation` or `indeterminate`; a `warn` under `--warn-as-error` |
| `2` | `error`: an operational failure (one of nine typed error kinds), a usage error, or an unhealthy `--doctor` |
| `130` | interrupted (SIGINT) |

The **knobs** that move a projection without touching the lattice
[SRC:src/pyforge/warden/verdict.py:L109-L146]: `--warn-as-error` (`warn_is_error`)
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
[SRC:src/pyforge/warden/cli.py:L31-L33] [SRC:src/pyforge/warden/report.py:L192].

## Architecture at a Glance

- **CLI** — sole public contract; `prog` is `warden` [SRC:src/pyforge/warden/report.py:L193].
- **Scan** — discovery → extract → engines → policy → report.
- **Verdict** — sole owner of lattice + exit projection
  [SRC:src/pyforge/warden/verdict.py:L1-L21].
- **Doctor** — operability, never a project policy verdict
  [SRC:src/pyforge/warden/cli.py:L657-L666].

## CLI

```text
warden --version
warden scan [path] [--format text|json] [--warn-only] [--doctor]
warden scan [path] [--fail-on TIER] [--fail-under-coverage N] [--warn-as-error] [--allow-empty]
warden scan [path] [--allow-licenses IDS] [--deny-licenses IDS] [--max-lag N] [--require-lts] [--fail-on-eol] [--min-epss N]
warden scan [path] [--baseline PATH] [--baseline-emit] [--bypass --reason TEXT]
warden scan [path] [--sbom-output PATH] [--deterministic] [--pixi-environment NAME] [--pixi-platform PLATFORM]
warden scan [path] [--open-fix-prs] [--fix-prs-dry-run]
pyforge warden scan [path]
pyforge warden scan --doctor
```

`[project.scripts]` name is `warden`; FR-13 grammar is `pyforge warden …`
(never a second public grammar that skips `pyforge`).

<!-- [MANUAL:api-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:api-notes] -->
