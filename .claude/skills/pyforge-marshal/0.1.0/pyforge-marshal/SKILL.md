---
name: pyforge-marshal
description: "Deterministic BMAD-loop supervisor: fleet status, loop homes, detector check, and Genesis seed via the marshal CLI. Use when running marshal status / homes / check / seed, or working in src/shared/packages/pyforge-marshal/. Do not import pyforge.marshal internals; the CLI is the public contract. Do not use for conda-forge recipe authoring (conda-forge-expert) or station personas."
---

# pyforge-marshal

## Overview

Compiles `src/shared/packages/pyforge-marshal/` (PyPI `pyforge-marshal` 0.1.0) as an
agentskills.io content skill for the **marshal** station. Source: local path
`src/shared/packages/pyforge-marshal` @ commit `b69fd81eb8` (`source_ref: local`).
Forge tier: **Quick** (SKF `skf-extract-public-api` + source-reading; T1-low).
First compiled from `865b95dc951` (Story 29.1); recompiled in place at 0.1.0 on
2026-11-01 (steward Story 29.4) from the widened scope (`cli/spin.py`,
`cli/dispatch.py`, `cli/context.py`, `cli/challenge.py`), and again on 2026-11-12
(steward Story 29.5, the fixes the EGM audit of 2026-11-05 accepted: MAR-R-F1,
MAR-R-F2, MAR-R-F20, MAR-R-F47, MAR-R-F49) from the scope widened with
`mcp/tools.py`, `mcp/server.py`, `seed/errors.py` and `core/verdict.py`, the station
contract `contract.md` as a doc source, and the real `marshal --help`, the way
Story 29.1 and atlas Stories 33.1 and 33.2 did.
Quick extract of `cli/main.py` documents `main` (console script
`marshal = pyforge.marshal.cli.main:main`) [SRC:src/pyforge/marshal/cli/main.py:L348]
[SRC:pyproject.toml:L48]. The package `__init__.py` is empty — other
components integrate via the CLI, never by importing internal modules
[SRC:src/pyforge/marshal/__init__.py].

## Description

Deterministic BMAD-loop supervisor: wraps bmad-loop with gates-as-objects,
run supervision, landing, fleet status, and adapter portability
[SRC:pyproject.toml:L8]. Genesis (`marshal seed …`) installs the operating
model; Marshal operates it [SRC:README.md:L10-L13].

**The public contract** is
`_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/contract.md`
(spec-pyforge-marshal:CAP-304): every CLI verb path and flag, both MCP surfaces, every
feature-flag key, environment variable, diagnostic code and exit code. The MCP tool
names, exit codes and flag keys in this skill are rows of that file; where they
differ, the contract and the code win.

## Quick Start

Run from the repository root (never a hardcoded absolute path)
[SRC:README.md:L117]. `pyforge-guild`, the session default environment,
carries marshal; the station's own suite runs in `-e pyforge-marshal`:

```bash
pixi run -e pyforge-guild marshal status
pixi run -e pyforge-guild marshal homes
pixi run -e pyforge-guild marshal check
pixi run -e pyforge-guild marshal seed check --repo-root .
pixi run -e pyforge-guild marshal factory dispatch <station> <story-key>
pixi run -e pyforge-guild marshal context advisory
```

**Status** (`marshal status`) [SRC:src/pyforge/marshal/cli/status.py:L475]:
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
[SRC:src/pyforge/marshal/cli/dispatch.py:L268-L286]: provisions a fresh
isolated worktree from `origin/main` and launches exactly one detached
`bmad-build-auto` story session with `BMAD_ACTIVE_PROJECT` set per invocation,
journals the launch and returns promptly. `--stories K1,K2,…` chains an
ordered sequence on one station through `factory drain`'s campaign machinery;
`--harness` overrides the session-harness preference for this invocation;
`--hold-landing` keeps the landing for the operator. The measured front door
for one story.

**Factory spin** (`marshal factory spin <slug>`)
[SRC:src/pyforge/marshal/cli/spin.py:L1112-L1138]: resolves the provisioned
loop home, verifies the raw story feed resolves completely, mints a run id
and detach-launches `bmad-loop run` (`--epic`, `--story`, `--max-count`;
`--foreground` blocks and relays the exit code). The multi-story front door.
`attach`, `resume`, `dispatch-attach`, `dispatch-resume`, `drain` and
`checkpoint` are the other `factory` verbs [SRC:src/pyforge/marshal/cli/spin.py:L1217-L1249].

**Factory challenge** (`marshal factory challenge`)
[SRC:src/pyforge/marshal/cli/challenge.py:L126-L181] [SRC:src/pyforge/marshal/cli/challenge.py:L1-L24]:
a fresh-context EGM review of one chain artifact (`--project`, `--stage
mint|decompose|readiness|drift|rules`, `--target`, `--epic` with `drift`). A whole
`SPEC.md`, `epics.md` or Dream outgrows one reviewer, so a review can take a slice:
`--section SELECTOR` cuts one part of `--target` (a CAP range such as
`CAP-298..CAP-303`, an epic range such as `epic:112..113,115`, or `heading:<text>`
with `#N` to pick the Nth match), and `--dream-section SELECTOR` cuts the
`--project` station's Dream context the same way (not with `--audit`); each slice is
written under the run's own Tier-3 directory. `--audit` sweeps the repo rules
(`AGENTS.md`, `CHAIN-STANDARD.md`), and for every station its skill (`rules`), its
newest CAP slice (`mint`) and the epic range that decomposes it (`decompose`), each
with the Dream entry the slice cites — never a whole `SPEC.md`, `epics.md` or Dream
(`--force` re-runs a station whose report exists) [SRC:src/pyforge/marshal/cli/challenge.py:L838-L867].
`challenge resolve --project P --report R --accept ID --reject ID` writes memlog lines
on marshal's Spec and prints the command for any other. Off unless the flag
`pyforge.marshal.egm_challenge` is on [SRC:src/pyforge/marshal/cli/challenge.py:L59];
while it is off the verb stays listed and refuses with the usage code. Its
prerequisites, cost, exit codes and report path are in the notes below.

**Context** (`marshal context …`) [SRC:src/pyforge/marshal/cli/context.py:L131]:
the derived-context layer. `advisory` [SRC:src/pyforge/marshal/cli/context.py:L289]
reports which declared-active `[context]` layers have lapsed (one MRS-CTX-009
WARN per lapsed layer, one journal entry, never blocks); `retrieve --epic N
[--story M]` [SRC:src/pyforge/marshal/cli/context.py:L194] returns scoped
planning context for one story through Scribe's recall grammar, or reports
the distill fallback; `refresh` reports one epic's derived-context freshness;
`bundle` assembles the digest-pinned context bundle; `bootstrap` / `pack`
fetch-or-rebuild and write the shared substrate. `--project` defaults to
`BMAD_ACTIVE_PROJECT`, then the active-project marker — never `scripts/bmad-switch`.

<!-- [MANUAL:additional-notes] -->
<!-- Persona grammar is `pyforge marshal …` (FR-13), not the `marshal` binary. -->
<!-- Track writer is `steward track assemble` (Story 53.3); marshal supplies field enumeration, not track.json. -->
<!-- Session-close ritual, every harness: `scribe capture` and `marshal context advisory` (AGENTS.md § Team memory), not restated here. -->
**One CLI, two spellings** (EGM audit 2026-11-05 MAR-R-F1, MAR-R-F20, MAR-R-F47). `pyforge marshal …` forwards to the
same `marshal` console script: the verb paths, flags and exit codes are one CLI. The examples in this skill use the
console script; a persona writes the `pyforge marshal …` spelling (canopy:FR-13). The MCP faces below are transports
onto the same verbs, not a third grammar.

**Before `marshal factory challenge`** (MAR-R-F2, MAR-R-F49). Each run is a paid Claude Code session, and `--audit`
runs one per review it sweeps: run it only when asked. A review refuses with exit 2, naming the cause, unless the
switches `pyforge.marshal.egm_challenge` and `pyforge.marshal.egm_policy_block` are on (`--audit` also needs
`pyforge.marshal.egm_audit`, `--stage drift` `pyforge.marshal.egm_retro_drift`; all default off), the `--project`
policy has an enabled `[challenge]` block whose `model` is an `anthropic` entry of marshal's own
`model_cost_catalog`, the plugin `egm@egm` is installed and enabled at the pinned `[challenge].plugin_version`
(default `0.1.0`), and `claude --version` is 2.1.271 or later. `resolve` starts no session: it needs only
`pyforge.marshal.egm_challenge` and `pyforge.marshal.egm_resolve_bridge`.
Exit 0 means a report was written (a finding never changes the code); 1 is unevaluable (a session failed or timed
out past `[challenge].timeout_s`, or left no valid report; for `--audit`, any review that did not report); 2 is a
refusal. Reports land under Tier 3, `_bmad-output/projects/<slug>/implementation-artifacts/egm/<run>/report.json`.
`resolve` writes memlog lines on marshal's own Spec only and prints the `memlog.py` command for any other owning
Spec. The vocabulary is `glossary.md` § *Challenger vocabulary* in
`_bmad-output/projects/pyforge-marshal/planning-artifacts/specs/spec-pyforge-marshal/`; the switch matrix is spec-pyforge-marshal:CAP-299.
<!-- [/MANUAL:additional-notes] -->

<!-- [MANUAL:station-mcp] -->
Station host: marshal's MCP face is `POST /stations/marshal/mcp` on the platform host. How to start the host, get the
assertion it accepts and send a request: `docs/how-to/reach-a-station-mcp-endpoint.md`.
<!-- [/MANUAL:station-mcp] -->

## Station MCP faces

Marshal has two MCP surfaces, as the code stands (`contract.md` § *MCP tools*).

**`marshal-mcp` (stdio)** — the console script `marshal-mcp`
[SRC:pyproject.toml:L52], `build_server()` [SRC:src/pyforge/marshal/mcp/server.py:L30],
registers exactly the tools `TOOL_SPECS` lists [SRC:src/pyforge/marshal/mcp/tools.py:L17-L22].
Each tool but `list_marshal_tools` runs the `marshal` CLI in-process and returns its
JSON report: `list_marshal_tools` (runs no CLI), `marshal_check`, `marshal_homes`,
`marshal_preflight` (`{slug}`), `marshal_preserve_list`, `marshal_preserve_push`,
`marshal_preserve_retire` (`{tag}`), `marshal_refresh`, `marshal_status`,
`marshal_upstream` and `marshal_watch`. The two preserve writes refuse with the usage
code while `pyforge.marshal.preserve_refs` is off. Nothing else is reachable: no
`factory`, `seed`, `gate`, `land` or `context` verb.

**Station face (`POST /stations/marshal/mcp`)** — django-marshal's `mcp_asgi.py`
on the platform host; every call carries a signed assertion. Its tools: `start_loop`,
`get_loop`, `run_loop` (the supervisor runner `start_loop` hands its work to),
`publish_loop_run`, `heartbeat_loop_run`, `complete_loop_run`,
`list_loop_story_tasks` and `marshal_watch`. Its runner runs one verb and nothing
else: `marshal factory dispatch <slug> <story> --format json` in `pyforge-guild`, at
most once per run, only for a `pyforge:admin` caller and only while
`pyforge.steward.start_loop_dispatch` is on — that flag ships off, so today
`start_loop` refuses every caller before a run row exists. `marshal_watch` returns
`marshal watch --format json`'s report.

## Common Workflows

**Fleet snapshot:** `run_status` [SRC:src/pyforge/marshal/cli/status.py:L1734]
via `_build_parser` → `status` handler [SRC:src/pyforge/marshal/cli/main.py:L260].

**Isolation audit:** `run_homes` [SRC:src/pyforge/marshal/cli/init.py:L1057]
after `add_homes_subparser` [SRC:src/pyforge/marshal/cli/init.py:L326].

**Detector front door:** `run_check` [SRC:src/pyforge/marshal/cli/check.py:L199]
with `--scope` mirrored from `scripts/detectors.py`.

**Genesis conformance:** `marshal seed check --repo-root .` then optional
`marshal seed adopt` / `marshal seed update` [SRC:README.md:L49-L62]; an
intended edit to a tool-owned file is recorded with `marshal seed accept`.

**Loop-home kit:** `marshal seed kit --repo-root <home> --apply` (or let
`marshal preflight` do it) -- Story 28.3's per-home token-economy kit.

**One story, measured:** `marshal factory dispatch <station> <story-key>` →
`run_dispatch` [SRC:src/pyforge/marshal/cli/dispatch.py:L2993]; follow it with
`marshal factory dispatch-attach`. Many stories on a loop home:
`marshal factory spin <station>` → `run_spin` [SRC:src/pyforge/marshal/cli/spin.py:L1570].

**Session close:** `marshal context advisory` → `run_context_advisory`
[SRC:src/pyforge/marshal/cli/context.py:L803].

**Chain review:** `marshal factory challenge --project <station> --stage <stage>
--target <path> [--section SELECTOR] [--dream-section SELECTOR]` → `run_challenge`
[SRC:src/pyforge/marshal/cli/challenge.py:L1030], then `marshal factory challenge resolve`.

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
| `run_challenge` | `factory challenge`: fresh-context EGM review | `--project`, `--stage`, `--target`, `--section`, `--dream-section`, `--epic`, `--audit` |
| `run_context_advisory` | `context advisory`: lapsed `[context]` layers | `--project`, `--format` |
| `run_context_retrieve` | `context retrieve`: scoped planning context | `--project`, `--epic`, `--story` |

## Key Exports

Public SKF extract of `cli/main.py` (Quick mode): `main`
[SRC:src/pyforge/marshal/cli/main.py:L348]. Console scripts:
`marshal = pyforge.marshal.cli.main:main` [SRC:pyproject.toml:L48] and
`marshal-mcp = pyforge.marshal.mcp.server:main` [SRC:pyproject.toml:L52].
Handlers used by the CLI tasks are documented from source-reading
(`run_status`, `run_homes`, `run_check`, `run_dispatch`, `run_spin`,
`run_challenge`, `run_context_advisory`, `run_context_retrieve`).

## Usage

Run `marshal` from the repository root. `pyforge marshal …` and `marshal …` are one
CLI: the examples here use the console script, and a persona uses the `pyforge
marshal …` spelling (canopy:FR-13). Do not `from pyforge.marshal import …` in other
stations. Do not implement bmad-loop → supervisor ingest here.

## Key Types

**`MarshalContext`** [SRC:src/pyforge/marshal/core/context.py:L52] —
resolved once at the front door when `--project` is present (`slug`,
`loop_home`, composed `policy`, optional `story`)
[SRC:src/pyforge/marshal/cli/main.py:L300].

**Exit domain** [SRC:src/pyforge/marshal/cli/main.py:L348-L369]
[SRC:src/pyforge/marshal/core/verdict.py:L462-L468] — `main` returns an int in the frozen
`{0, 1, 2, 3, 4, 130}` set (marshal's AD-7), the rows of `contract.md` § *Exit codes*:
`0` ok (`clean`, `warn`; a warning never changes the code) · `1` unevaluable ·
`2` usage (an argparse error, a verb whose switch is off; also `scope-violation`) ·
`3` a gate failed · `4` an operation was attempted and failed or was blocked ·
`130` interrupted. Any other value a handler returns is clamped to `2`.

**Seed exit domain** [SRC:src/pyforge/marshal/seed/errors.py:L195-L201] — a `seed`
verb may also return one code per `SeedError` leaf: `1` `ConformanceFailure` (HARD
findings) · `2` `UsageError` · `3` `PreconditionFailure` (dirty worktree, not a git
repository, hand-edited managed content) · `4` `NeverWriteViolation` · `5`
`StateInvalid` (`.marshal/seed-state.yml` missing, unreadable or off-schema) · `10`
`InternalError`.

## Architecture at a Glance

- **CLI front door** — `main` builds the subparser tree and relays handler
  exit codes [SRC:src/pyforge/marshal/cli/main.py:L260-L297].
- **Status** — runtime state from journals, not sprint-status.yaml
  [SRC:src/pyforge/marshal/cli/status.py:L1-L9].
- **Homes** — structural isolation of loop worktrees
  [SRC:src/pyforge/marshal/cli/init.py:L326].
- **Check** — existing detector registry, not a second engine
  [SRC:src/pyforge/marshal/cli/check.py:L1-L10].
- **Factory** — detached launches: `spin` (bmad-loop) and `dispatch`
  (one `bmad-build-auto` story) [SRC:src/pyforge/marshal/cli/dispatch.py:L1-L20].
- **MCP** — `marshal-mcp` wraps the CLI one tool per verb, no craft logic
  [SRC:src/pyforge/marshal/mcp/tools.py:L1-L6].
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
marshal factory challenge [--project P] [--stage mint|decompose|readiness|drift|rules] [--target PATH] [--section SELECTOR] [--dream-section SELECTOR] [--epic N] [--audit [--force]] [--format text|json]
marshal factory challenge resolve --project P --report REPORT [--accept ID[:NOTE]] [--reject ID[:REASON]]
marshal context advisory [--project SLUG] [--format text|json]
marshal context retrieve [--project SLUG] --epic N [--story M] [--format text|json]
marshal context refresh|bundle|bootstrap|pack …
marshal config|init|preflight|teardown|gate|deploy|land|retire|watch|adapters|upstream|refresh|planning|login|benchmark|preserve …
```

Bare `marshal` prints usage and exits 0 [SRC:src/pyforge/marshal/cli/main.py:L383-L390].
`marshal <verb> --help` names each verb's own flags; a verb whose feature
flag is off stays listed, marked `[disabled: flag … is off]`.

<!-- [MANUAL:api-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:api-notes] -->
