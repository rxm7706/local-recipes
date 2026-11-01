---
name: pyforge-marshal
description: "Deterministic BMAD-loop supervisor: fleet status, loop homes, detector check, and Genesis seed via the marshal CLI. Use when running marshal status / homes / check / seed, or working in src/shared/packages/pyforge-marshal/. Do not import pyforge.marshal internals; the CLI is the public contract. Do not use for conda-forge recipe authoring (conda-forge-expert) or station personas."
---

# pyforge-marshal

## Overview

Compiles `src/shared/packages/pyforge-marshal/` (PyPI `pyforge-marshal` 0.1.0) as an
agentskills.io content skill for the **marshal** station. Source: local path
`src/shared/packages/pyforge-marshal` @ commit `03a7aff5d9` (`source_ref: local`).
Forge tier: **Quick** (SKF `skf-extract-public-api` + source-reading; T1-low).
First compiled from `865b95dc951` (Story 29.1); recompiled in place at 0.1.0 on
2026-11-01 (steward Story 29.4) from the widened scope (`cli/spin.py`,
`cli/dispatch.py`, `cli/context.py`, `cli/challenge.py`) and the real
`marshal --help`, the way Story 29.1 and atlas Stories 33.1 and 33.2 did.
Quick extract of `cli/main.py` documents `main` (console script
`marshal = pyforge.marshal.cli.main:main`) [SRC:src/pyforge/marshal/cli/main.py:L332]
[SRC:pyproject.toml:L48]. The package `__init__.py` is empty — other
components integrate via the CLI, never by importing internal modules
[SRC:src/pyforge/marshal/__init__.py].

## Description

Deterministic BMAD-loop supervisor: wraps bmad-loop with gates-as-objects,
run supervision, landing, fleet status, and adapter portability
[SRC:pyproject.toml:L8]. Genesis (`marshal seed …`) installs the operating
model; Marshal operates it [SRC:README.md:L10-L13].

## Quick Start

Run from the repository root (never a hardcoded absolute path)
[SRC:README.md:L95]. `pyforge-guild`, the session default environment,
carries marshal; the station's own suite runs in `-e pyforge-marshal`:

```bash
pixi run -e pyforge-guild marshal status
pixi run -e pyforge-guild marshal homes
pixi run -e pyforge-guild marshal check
pixi run -e pyforge-guild marshal seed check --repo-root .
pixi run -e pyforge-guild marshal factory dispatch <station> <story-key>
pixi run -e pyforge-guild marshal context advisory
```

**Status** (`marshal status`) [SRC:src/pyforge/marshal/cli/status.py:L473]:
one row per loop home (runtime state, current story, elapsed, budget) from
journals — never a hand-maintained story feed [SRC:src/pyforge/marshal/cli/status.py:L1-L9].
`--project SLUG` scopes the fleet; `--run RUN_ID` needs `--project`.

**Homes** (`marshal homes`) [SRC:src/pyforge/marshal/cli/init.py:L326]:
lists every discovered `loop/<slug>` worktree and verifies isolation. Read-only.

**Check** (`marshal check`) [SRC:src/pyforge/marshal/cli/check.py:L88]:
routes to `scripts/detectors.py` (`--scope repo|runtime|all`, default `all`).

**Seed check** (`marshal seed check`) [SRC:src/pyforge/marshal/cli/seed.py:L1367]:
read-only Genesis conformance report. Eight verbs total:
`init`/`adopt`/`check`/`update`/`explain`/`version`/`kit`/`accept`.

**Seed accept** (`marshal seed accept <artifact-id>[#<region>]`): records an
intended edit to a tool-owned file or region as the new baseline, the way
`update --force` cannot (that one *discards* the edit). Dry run by default;
`--apply --reason "..."` re-records the hash and appends one `acceptances`
journal entry to `.marshal/seed-state.yml` in the same atomic replace, on a
clean worktree. It writes nothing else. A `copied-seeded` (repo-owned) file
needs no accept: the guard follows the manifest's current class.

**Seed kit** (`marshal seed kit`) [SRC:src/pyforge/marshal/cli/seed.py:L1393]:
provisions a LOOP HOME's token-economy kit (caveman skill + articulate
carve-out, CCR store dir, codegraph index), each gated by its own
`[context]` layer. Dry-run by default, `--apply` provisions; exits 0 on
every completed run -- an unavailable instrument skips its layer with a
named finding and never blocks.

**Factory dispatch** (`marshal factory dispatch <slug> [<story>]`)
[SRC:src/pyforge/marshal/cli/dispatch.py:L267-L285]: provisions a fresh
isolated worktree from `origin/main` and launches exactly one detached
`bmad-build-auto` story session with `BMAD_ACTIVE_PROJECT` set per invocation,
journals the launch and returns promptly. `--stories K1,K2,…` chains an
ordered sequence on one station through `factory drain`'s campaign machinery;
`--harness` overrides the session-harness preference for this invocation;
`--hold-landing` keeps the landing for the operator. The measured front door
for one story.

**Factory spin** (`marshal factory spin <slug>`)
[SRC:src/pyforge/marshal/cli/spin.py:L1111-L1137]: resolves the provisioned
loop home, verifies the raw story feed resolves completely, mints a run id
and detach-launches `bmad-loop run` (`--epic`, `--story`, `--max-count`;
`--foreground` blocks and relays the exit code). The multi-story front door.
`attach`, `resume`, `dispatch-attach`, `dispatch-resume`, `drain` and
`checkpoint` are the other `factory` verbs [SRC:src/pyforge/marshal/cli/spin.py:L1216-L1248].

**Factory challenge** (`marshal factory challenge`)
[SRC:src/pyforge/marshal/cli/challenge.py:L109-L141]: a fresh-context EGM
review of one chain artifact (`--project`, `--stage
mint|decompose|readiness|drift|rules`, `--target`, `--epic` with
`drift`), or `--audit` over every station's Dream, Spec, `epics.md` and the
repo rules (`--force` re-runs a station whose report exists). `challenge
resolve --project P --report R --accept ID --reject ID` writes memlog lines
on marshal's Spec and prints the command for any other. Off unless the flag
`pyforge.marshal.egm_challenge` is on [SRC:src/pyforge/marshal/cli/challenge.py:L50];
while it is off the verb stays listed and refuses with the usage code.

**Context** (`marshal context …`) [SRC:src/pyforge/marshal/cli/context.py:L130]:
the derived-context layer. `advisory` [SRC:src/pyforge/marshal/cli/context.py:L288]
reports which declared-active `[context]` layers have lapsed (one MRS-CTX-009
WARN per lapsed layer, one journal entry, never blocks); `retrieve --epic N
[--story M]` [SRC:src/pyforge/marshal/cli/context.py:L193] returns scoped
planning context for one story through Scribe's recall grammar, or reports
the distill fallback; `refresh` reports one epic's derived-context freshness;
`bundle` assembles the digest-pinned context bundle; `bootstrap` / `pack`
fetch-or-rebuild and write the shared substrate. `--project` defaults to
`BMAD_ACTIVE_PROJECT`, then the active-project marker — never `scripts/bmad-switch`.

<!-- [MANUAL:additional-notes] -->
<!-- Persona grammar is `pyforge marshal …` (FR-13), not the `marshal` binary. -->
<!-- Track writer is `steward track assemble` (Story 53.3); marshal supplies field enumeration, not track.json. -->
<!-- Session-close ritual, every harness: `scribe capture` and `marshal context advisory` (AGENTS.md § Team memory), not restated here. -->
<!-- [/MANUAL:additional-notes] -->

<!-- [MANUAL:station-mcp] -->
Station host: marshal's MCP face is `POST /stations/marshal/mcp` on the platform host. How to start the host, get the
assertion it accepts and send a request: `docs/how-to/reach-a-station-mcp-endpoint.md`.
<!-- [/MANUAL:station-mcp] -->

## Common Workflows

**Fleet snapshot:** `run_status` [SRC:src/pyforge/marshal/cli/status.py:L1731]
via `_build_parser` → `status` handler [SRC:src/pyforge/marshal/cli/main.py:L244].

**Isolation audit:** `run_homes` [SRC:src/pyforge/marshal/cli/init.py:L1057]
after `add_homes_subparser` [SRC:src/pyforge/marshal/cli/init.py:L326].

**Detector front door:** `run_check` [SRC:src/pyforge/marshal/cli/check.py:L199]
with `--scope` mirrored from `scripts/detectors.py`.

**Genesis conformance:** `marshal seed check --repo-root .` then optional
`marshal seed adopt` / `marshal seed update` [SRC:README.md:L27-L40]; an
intended edit to a tool-owned file is recorded with `marshal seed accept`.

**Loop-home kit:** `marshal seed kit --repo-root <home> --apply` (or let
`marshal preflight` do it) -- Story 28.3's per-home token-economy kit.

**One story, measured:** `marshal factory dispatch <station> <story-key>` →
`run_dispatch` [SRC:src/pyforge/marshal/cli/dispatch.py:L2992]; follow it with
`marshal factory dispatch-attach`. Many stories on a loop home:
`marshal factory spin <station>` → `run_spin` [SRC:src/pyforge/marshal/cli/spin.py:L1569].

**Session close:** `marshal context advisory` → `run_context_advisory`
[SRC:src/pyforge/marshal/cli/context.py:L802].

**Chain review:** `marshal factory challenge --project <station> --stage <stage>
--target <path>` → `run_challenge` [SRC:src/pyforge/marshal/cli/challenge.py:L772],
then `marshal factory challenge resolve`.

## Key API Summary

| Function | Purpose | Key params |
|---|---|---|
| `main` | argparse entry (`marshal` console script) | `argv` |
| `run_status` | Fleet-wide runtime status | `--project`, `--run` |
| `run_homes` | List loop homes + isolation | `--format` |
| `run_check` | Detector registry front door | `--scope`, `--project` |
| `run_check` (seed) | Genesis read-only check | `--repo-root`, `--project`, `--strict` |
| `run_kit` (seed) | Provision a loop home's token-economy kit | `--repo-root`, `--project`, `--apply` |
| `run_dispatch` | `factory dispatch`: one detached story session | `slug`, `story`, `--stories`, `--harness`, `--hold-landing` |
| `run_spin` | `factory spin`: detach-launch a bmad-loop run | `slug`, `--epic`, `--story`, `--max-count`, `--foreground` |
| `run_challenge` | `factory challenge`: fresh-context EGM review | `--project`, `--stage`, `--target`, `--epic`, `--audit` |
| `run_context_advisory` | `context advisory`: lapsed `[context]` layers | `--project`, `--format` |
| `run_context_retrieve` | `context retrieve`: scoped planning context | `--project`, `--epic`, `--story` |

## Key Exports

Public SKF extract of `cli/main.py` (Quick mode): `main`
[SRC:src/pyforge/marshal/cli/main.py:L332]. Console script:
`marshal = pyforge.marshal.cli.main:main` [SRC:pyproject.toml:L48].
Handlers used by the CLI tasks are documented from source-reading
(`run_status`, `run_homes`, `run_check`, `run_dispatch`, `run_spin`,
`run_challenge`, `run_context_advisory`, `run_context_retrieve`).

## Usage

Always invoke `marshal` from repo root. Do not
`from pyforge.marshal import …` in other stations. Unified grammar for
personas is `pyforge marshal …` — do not treat the `marshal` binary as a
second public grammar. Do not implement bmad-loop → supervisor ingest here.

## Key Types

**`MarshalContext`** [SRC:src/pyforge/marshal/core/context.py:L52] —
resolved once at the front door when `--project` is present (`slug`,
`loop_home`, composed `policy`, optional `story`)
[SRC:src/pyforge/marshal/cli/main.py:L284].

**Exit domain** [SRC:src/pyforge/marshal/cli/main.py:L332-L344] —
`main` returns an int in the frozen `{0, 1, 2, 3, 4, 130}` set (AD-7).

## Architecture at a Glance

- **CLI front door** — `main` builds the subparser tree and relays handler
  exit codes [SRC:src/pyforge/marshal/cli/main.py:L244-L281].
- **Status** — runtime state from journals, not sprint-status.yaml
  [SRC:src/pyforge/marshal/cli/status.py:L1-L9].
- **Homes** — structural isolation of loop worktrees
  [SRC:src/pyforge/marshal/cli/init.py:L326].
- **Check** — existing detector registry, not a second engine
  [SRC:src/pyforge/marshal/cli/check.py:L1-L10].
- **Factory** — detached launches: `spin` (bmad-loop) and `dispatch`
  (one `bmad-build-auto` story) [SRC:src/pyforge/marshal/cli/dispatch.py:L1-L20].
- **CLI** — sole public contract [SRC:src/pyforge/marshal/cli/main.py:L1-L12].

## CLI

```text
marshal --version
marshal status [--project SLUG] [--run RUN_ID]
marshal homes [--format text|json]
marshal check [--scope repo|runtime|all] [--project SLUG]
marshal seed check --repo-root .
marshal seed init <PATH> --slug <SLUG>
marshal seed adopt --repo-root . [--apply --yes]
marshal seed accept <ARTIFACT-ID>[#<REGION>] --repo-root . [--apply --reason TEXT]
marshal seed kit --repo-root <LOOP-HOME> [--apply]
marshal factory dispatch <SLUG> [<STORY>] [--stories K1,K2] [--harness H] [--hold-landing] [--format text|json]
marshal factory spin <SLUG> [--epic N] [--story KEY] [--max-count N] [--foreground]
marshal factory attach|resume|dispatch-attach|dispatch-resume|drain|checkpoint …
marshal factory challenge [--project P] [--stage mint|decompose|readiness|drift|rules] [--target PATH] [--epic N] [--audit [--force]]
marshal factory challenge resolve --project P --report REPORT [--accept ID[:NOTE]] [--reject ID[:REASON]]
marshal context advisory [--project SLUG] [--format text|json]
marshal context retrieve [--project SLUG] --epic N [--story M] [--format text|json]
marshal context refresh|bundle|bootstrap|pack …
marshal config|init|preflight|teardown|gate|deploy|land|retire|watch|adapters|upstream|refresh|planning|login|benchmark|preserve …
```

Bare `marshal` prints usage and exits 0 [SRC:src/pyforge/marshal/cli/main.py:L359-L366].
`marshal <verb> --help` names each verb's own flags; a verb whose feature
flag is off stays listed, marked `[disabled: flag … is off]`.

<!-- [MANUAL:api-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:api-notes] -->
