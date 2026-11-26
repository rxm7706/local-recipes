---
name: pyforge-marshal
description: "Deterministic BMAD-loop supervisor: fleet status, loop homes, detector check, and Genesis seed via the marshal CLI. Use when running marshal status / homes / check / seed, or working in src/shared/packages/pyforge-marshal/. Do not import pyforge.marshal internals; the CLI is the public contract. Do not use for conda-forge recipe authoring (conda-forge-expert) or station personas."
---

# pyforge-marshal

## Overview

Compiles `src/shared/packages/pyforge-marshal/` (PyPI `pyforge-marshal` 0.1.0) as an
agentskills.io content skill for the **marshal** station. Source: local path
`src/shared/packages/pyforge-marshal` @ commit `5f22584869` (`source_ref: local`).
Forge tier: **Forge** (SKF `skf-extract-public-api` over ast-grep 0.45.3; 150 exports, all T1).
First compiled from `865b95dc951` (Story 29.1); recompiled in place at 0.1.0 on
2026-11-01 (steward Story 29.4) from the widened scope (`cli/spin.py`,
`cli/dispatch.py`, `cli/context.py`, `cli/challenge.py`), and again on 2026-11-12
(steward Story 29.5, the fixes the EGM audit of 2026-11-05 accepted: MAR-R-F1,
MAR-R-F2, MAR-R-F20, MAR-R-F47, MAR-R-F49) from the scope widened with
`mcp/tools.py`, `mcp/server.py`, `seed/errors.py` and `core/verdict.py`, the station
contract `contract.md` as a doc source, and the real `marshal --help`, the way
Story 29.1 and atlas Stories 33.1 and 33.2 did.
Rebuilt as 0.1.1 on 2026-11-18 (steward Story 126.5) with `skf-update-skill` at Forge
tier over ast-grep 0.45.3, a full re-extraction at `424ce69fc2`.
Updated to 0.1.2 on 2026-11-25 (steward Story 136.10) by `skf-update-skill` at the same
tier, from the source at `5f22584869`: no export changed; `main` now returns usage for a
flag tree that cannot be composed and the error code for any other exception (marshal
Story 121.1), and the citations into `cli/main.py` follow its lines.
The extract documents 150 exports (129 functions, 21 classes) in 13 modules; `main` is the console script
(`marshal = pyforge.marshal.cli.main:main`) [AST:src/pyforge/marshal/cli/main.py:L348]
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
[SRC:README.md:L118]. `pyforge-guild`, the session default environment,
carries marshal; the station's own suite runs in `-e pyforge-marshal`:

```bash
pixi run -e pyforge-guild marshal status
pixi run -e pyforge-guild marshal homes
pixi run -e pyforge-guild marshal check
pixi run -e pyforge-guild marshal seed check --repo-root .
pixi run -e pyforge-guild marshal factory dispatch <station> <story-key>
pixi run -e pyforge-guild marshal context advisory
```

**Status** (`marshal status`) [AST:src/pyforge/marshal/cli/status.py:L474]:
one row per loop home (runtime state, current story, elapsed, budget) from
journals — never a hand-maintained story feed [SRC:src/pyforge/marshal/cli/status.py:L1-L9].
`--project SLUG` scopes the fleet; `--run RUN_ID` needs `--project`.

**Homes** (`marshal homes`) [AST:src/pyforge/marshal/cli/init.py:L326]:
lists every discovered `loop/<slug>` worktree and verifies isolation. Read-only.

**Check** (`marshal check`) [AST:src/pyforge/marshal/cli/check.py:L88]:
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
[AST:src/pyforge/marshal/cli/dispatch.py:L268-L286]: provisions a fresh
isolated worktree from `origin/main` and launches exactly one detached
`bmad-build-auto` story session with `BMAD_ACTIVE_PROJECT` set per invocation,
journals the launch and returns promptly. `--stories K1,K2,…` chains an
ordered sequence on one station through `factory drain`'s campaign machinery;
`--harness` overrides the session-harness preference for this invocation;
`--hold-landing` keeps the landing for the operator. The measured front door
for one story.

**Factory spin** (`marshal factory spin <slug>`)
[AST:src/pyforge/marshal/cli/spin.py:L1112-L1138]: resolves the provisioned
loop home, verifies the raw story feed resolves completely, mints a run id
and detach-launches `bmad-loop run` (`--epic`, `--story`, `--max-count`;
`--foreground` blocks and relays the exit code). The multi-story front door.
`attach`, `resume`, `dispatch-attach`, `dispatch-resume`, `drain` and
`checkpoint` are the other `factory` verbs [SRC:src/pyforge/marshal/cli/spin.py:L1181-L1249].

**Factory challenge** (`marshal factory challenge`)
[AST:src/pyforge/marshal/cli/challenge.py:L126-L181] [SRC:src/pyforge/marshal/cli/challenge.py:L1-L24]:
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
(`--force` re-runs a station whose report exists) [AST:src/pyforge/marshal/cli/challenge.py:L838-L867].
`challenge resolve --project P --report R --accept ID --reject ID` writes memlog lines
on marshal's Spec and prints the command for any other. Off unless the flag
`pyforge.marshal.egm_challenge` is on [SRC:src/pyforge/marshal/cli/challenge.py:L59];
while it is off the verb stays listed and refuses with the usage code. Its
prerequisites, cost, exit codes and report path are in the notes below.

**Context** (`marshal context …`) [AST:src/pyforge/marshal/cli/context.py:L131]:
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
<!-- Persona grammar is `pyforge marshal …` (canopy:FR-13), not the `marshal` binary. -->
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
[SRC:pyproject.toml:L52], `build_server()` [AST:src/pyforge/marshal/mcp/server.py:L30],
registers exactly the tools `TOOL_SPECS` lists [SRC:src/pyforge/marshal/mcp/tools.py:L17-L82].
Each tool but `list_marshal_tools` runs the `marshal` CLI in-process and returns its
JSON report: `list_marshal_tools` (runs no CLI), `marshal_check`, `marshal_homes`,
`marshal_preflight` (`{slug}`), `marshal_preserve_list`, `marshal_preserve_push`,
`marshal_preserve_retire` (`{tag, evidence}`), `marshal_refresh`, `marshal_status`,
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

**Fleet snapshot:** `run_status` [AST:src/pyforge/marshal/cli/status.py:L1734]
via `_build_parser` → `status` handler [SRC:src/pyforge/marshal/cli/main.py:L260].

**Isolation audit:** `run_homes` [AST:src/pyforge/marshal/cli/init.py:L1057]
after `add_homes_subparser` [AST:src/pyforge/marshal/cli/init.py:L326].

**Detector front door:** `run_check` [AST:src/pyforge/marshal/cli/check.py:L199]
with `--scope` mirrored from `scripts/detectors.py`.

**Genesis conformance:** `marshal seed check --repo-root .` then optional
`marshal seed adopt` / `marshal seed update` [SRC:README.md:L49-L62]; an
intended edit to a tool-owned file is recorded with `marshal seed accept`.

**Loop-home kit:** `marshal seed kit --repo-root <home> --apply` (or let
`marshal preflight` do it) -- Story 28.3's per-home token-economy kit.

**One story, measured:** `marshal factory dispatch <station> <story-key>` →
`run_dispatch` [AST:src/pyforge/marshal/cli/dispatch.py:L2993]; follow it with
`marshal factory dispatch-attach`. Many stories on a loop home:
`marshal factory spin <station>` → `run_spin` [AST:src/pyforge/marshal/cli/spin.py:L1570].

**Session close:** `marshal context advisory` → `run_context_advisory`
[AST:src/pyforge/marshal/cli/context.py:L803].

**Chain review:** `marshal factory challenge --project <station> --stage <stage>
--target <path> [--section SELECTOR] [--dream-section SELECTOR]` → `run_challenge`
[AST:src/pyforge/marshal/cli/challenge.py:L1030], then `marshal factory challenge resolve`.

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

Public SKF extract (Forge tier, ast-grep): 150 exports in 13 modules, listed under
Full API Reference and Full Type Definitions below; `main`
[AST:src/pyforge/marshal/cli/main.py:L348]. Console scripts:
`marshal = pyforge.marshal.cli.main:main` [SRC:pyproject.toml:L48] and
`marshal-mcp = pyforge.marshal.mcp.server:main` [SRC:pyproject.toml:L52].
Handlers used by the CLI tasks come from the same extract
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

**Exit domain** [AST:src/pyforge/marshal/cli/main.py:L348-L371]
[SRC:src/pyforge/marshal/core/verdict.py:L462-L468] — `main` returns an int in the frozen
`{0, 1, 2, 3, 4, 130}` set (marshal's AD-7), the rows of `contract.md` § *Exit codes*:
`0` ok (`clean`, `warn`; a warning never changes the code) · `1` unevaluable ·
`2` usage (an argparse error, a verb whose switch is off; also `scope-violation`) ·
`3` a gate failed · `4` an operation was attempted and failed or was blocked ·
`130` interrupted. Any other value a handler returns is clamped to `2`. A flag tree
that cannot be composed (a bad `PYFORGE_ENVIRONMENT`, say) is usage, `2`, with one
stderr line; any other exception leaves as `4` with one `marshal: internal error: …`
line, never a traceback [SRC:src/pyforge/marshal/cli/main.py:L431-L441]
[SRC:src/pyforge/marshal/cli/main.py:L477-L486].

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
  [AST:src/pyforge/marshal/cli/init.py:L326].
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
marshal status [--project SLUG] [--run RUN_ID] [--escalations] [--reconcile-ledger] [--format text|json]
marshal homes [--format text|json]
marshal check [--scope repo|runtime|all] [--project SLUG] [--format text|json]
marshal seed check [--repo-root PATH] [--strict] [--project SLUG] [--json] [--quiet]
marshal seed init <PATH> [--slug SLUG] [--agents LIST] [--force] [--dry-run] [--json] [--quiet]
marshal seed adopt [--repo-root PATH] [--apply] [--yes] [--agents LIST] [--skip GLOB] [--force] [--project SLUG] [--dry-run] [--json] [--quiet]
marshal seed accept <ARTIFACT-ID>[#<REGION>] [--repo-root PATH] [--apply] [--reason TEXT] [--dry-run] [--json] [--quiet]
marshal seed kit [--repo-root PATH] [--apply] [--project SLUG] [--dry-run] [--json] [--quiet]
marshal factory dispatch <SLUG> [<STORY>] [--stories K1,K2] [--harness H] [--hold-landing] [--format text|json]
marshal factory spin <SLUG> [--epic N] [--story KEY] [--max-count N] [--foreground] [--format text|json]
marshal factory attach|resume|dispatch-attach|dispatch-resume|drain|checkpoint …
marshal factory challenge [--project P] [--stage mint|decompose|readiness|drift|rules] [--target PATH] [--section SELECTOR] [--dream-section SELECTOR] [--epic N] [--audit [--force]] [--format text|json]
marshal factory challenge resolve [--project P] --report REPORT [--accept ID[:NOTE]] [--reject ID[:REASON]]
marshal context advisory [--project SLUG] [--root PATH] [--format text|json]
marshal context retrieve [--project SLUG] --epic N [--story M] [--root PATH] [--format text|json]
marshal context refresh|bundle|bootstrap|pack …
marshal config|init|preflight|teardown|gate|deploy|land|retire|watch|adapters|upstream|refresh|planning|login|benchmark|preserve …
```

Bare `marshal` prints usage and exits 0 [SRC:src/pyforge/marshal/cli/main.py:L385-L392].
`marshal <verb> --help` names each verb's own flags; a verb whose feature
flag is off stays listed, marked `[disabled: flag … is off]`.

<!-- [MANUAL:api-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:api-notes] -->

## Full API Reference

Every public function the extract found, by module, in source order: signature, the first sentence of its
docstring where it has one, and its definition line. 129 functions; the 21 classes are under Full Type Definitions.
These are the CLI's internals, listed so a change in `src/shared/packages/pyforge-marshal/` can be traced: other
stations call the `marshal` CLI, never these names.

### `cli/challenge.py`

- `add_factory_challenge_subparser(factory_subparsers: argparse._SubParsersAction) -> None` [AST:src/pyforge/marshal/cli/challenge.py:L126]
- `flag_on(key: str) -> bool` — A default-off EGM switch. [AST:src/pyforge/marshal/cli/challenge.py:L187]
- `compose_effective(slug: str) -> policy.EffectivePolicy` [AST:src/pyforge/marshal/cli/challenge.py:L196]
- `challenge_config(effective: policy.EffectivePolicy) -> core.ChallengeConfig` — The composed block, or ``OFF`` while the policy-block switch is off. [AST:src/pyforge/marshal/cli/challenge.py:L211]
- `adapter_models(effective: policy.EffectivePolicy) -> list[str]` — The ``[adapter]`` (``dev``) and ``[adapter.review]`` (``review``) baselines of the station's bmad-loop policy that a session can still run on by the station's declared tiers (Story 113.9, narrowed by Story 113.16): a … [AST:src/pyforge/marshal/cli/challenge.py:L219]
- `spin_models(effective: policy.EffectivePolicy) -> list[str]` — Every model a ``marshal factory spin`` session can author with (Story 113.17): the ``dev`` and ``review`` models of the policy spin renders for each ``model_tier_map`` tier and for a run with no declared difficulty. [AST:src/pyforge/marshal/cli/challenge.py:L246]
- `session_models(effective: policy.EffectivePolicy, *, launch_model: str | None = None) -> list[str]` — Every model the station's sessions can author with (CAP-299, Stories 113.9 and 113.16): its ``model_tier_map`` models, the ``adapter_models`` baselines a tier can still fall to, and, in a dispatch, the run's resolved … [AST:src/pyforge/marshal/cli/challenge.py:L271]
- `challenger_catalog(slug: str, effective: policy.EffectivePolicy) -> Mapping[str, object]` — Marshal's own ``model_cost_catalog``, read for every ``--project`` (operator ruling 2026-11-01, Story 113.9); ``render_refusals`` keeps only its Anthropic entries. [AST:src/pyforge/marshal/cli/challenge.py:L288]
- `challenger_aliases() -> tuple[str, ...]` — The packaged claude profile's ``[model_list]`` aliases: the profile the challenger runs on. [AST:src/pyforge/marshal/cli/challenge.py:L296]
- `model_refusals(config: core.ChallengeConfig, *, slug: str, effective: policy.EffectivePolicy, launch_model: str | None = None, stage: str | None = None) -> list[str]` — ``core.render_refusals`` with the challenger's catalog, the station's session models and the claude profile's aliases (CAP-299, Story 113.9). [AST:src/pyforge/marshal/cli/challenge.py:L304]
- `plugins_root(env: Mapping[str, str] | None = None) -> Path` [AST:src/pyforge/marshal/cli/challenge.py:L337]
- `plugin_refusal(plugins: Path, version: str, personas: tuple[str, ...] = ()) -> str | None` — ``None`` when ``egm@egm`` is enabled in the challenge session's own ``--settings`` (the scope the session runs with, from outside the repo -- Story 113.10), Claude Code's installed-plugins index holds exactly the pinned … [AST:src/pyforge/marshal/cli/challenge.py:L342]
- `glossary_path(root: Path, slug: str) -> Path` [AST:src/pyforge/marshal/cli/challenge.py:L392]
- `spec_path(root: Path, slug: str) -> Path` [AST:src/pyforge/marshal/cli/challenge.py:L396]
- `dream_path(root: Path, slug: str) -> Path` [AST:src/pyforge/marshal/cli/challenge.py:L400]
- `epics_path(root: Path, slug: str) -> Path` [AST:src/pyforge/marshal/cli/challenge.py:L404]
- `station_skill_path(root: Path, station: str) -> Path | None` [AST:src/pyforge/marshal/cli/challenge.py:L408]
- `owner_override(root: Path, stage: str, target: Path) -> Path | None` — The Spec folder that governs a rules target outside its run's station (Story 113.13, CAP-303): ``AGENTS.md`` is ``spec-pyforge-scribe``'s, ``CHAIN-STANDARD.md`` ``spec-one-chain-per-station``'s. [AST:src/pyforge/marshal/cli/challenge.py:L419]
- `owning_spec(root: Path, slug: str, stage: str, target: Path) -> Path` — The Spec folder a run's findings belong to: the override, else the station's own Spec. [AST:src/pyforge/marshal/cli/challenge.py:L431]
- `artifact_dir(root: Path, slug: str, config: core.ChallengeConfig) -> Path` [AST:src/pyforge/marshal/cli/challenge.py:L436]
- `default_standards(root: Path, slug: str, stage: str) -> tuple[Path, ...]` — Each stage's standard when the ``[challenge]`` block names none for it (CAP-299, Story 113.12): mint is judged against the bmad-spec five-field template, decompose against the station Spec whose capability range its … [AST:src/pyforge/marshal/cli/challenge.py:L440]
- `build_context(root: Path, slug: str, stage: str, target: Path, config: core.ChallengeConfig, *, dream: Path | None = None, standards_fallback: tuple[Path, ...] = (), omit_dream: bool = False) -> core.ChallengeContext` — The reviewer's context. [AST:src/pyforge/marshal/cli/challenge.py:L455]
- `append_journal(journal: Path, *, writer: str, counter: int, run_id: str, kind: str, phase: Phase, payload: Mapping[str, object], now: datetime, intent: JournalEntryId | None = None) -> JournalEntryId` [AST:src/pyforge/marshal/cli/challenge.py:L494]
- `tree_snapshot(root: Path) -> str | None` — ``git status --porcelain`` at ``root``; ``None`` when it is not a git tree. [AST:src/pyforge/marshal/cli/challenge.py:L520]
- `journal_refusal(out_dir: Path, slug: str, reason: str, now: datetime) -> Path` — S6: a refusal is a journaled fact, not only a line on stderr. [AST:src/pyforge/marshal/cli/challenge.py:L529]
- `new_run_dir(out_dir: Path, slug: str, moment: datetime) -> Path` — A fresh run directory, named by its run id, under ``out_dir``. [AST:src/pyforge/marshal/cli/challenge.py:L550]
- `run_one(*, root: Path, slug: str, stage: str, target: Path, config: core.ChallengeConfig, runner: ChallengeRunner, out_dir: Path, now: Callable[[], datetime] = lambda: datetime.now(UTC), dream: Path | None = None, owner: Path | None = None, standards: tuple[Path, ...] = (), dream_choice: str = "", omit_dream: bool = False, run_dir: Path | None = None) -> RunOutcome` — Run one stage on one target. [AST:src/pyforge/marshal/cli/challenge.py:L557]
- `epic_drift_paths(epics_text: str, epic: str) -> tuple[list[str], list[str]]` — The epic's story-spec paths and the ``src/`` paths its stories name. [AST:src/pyforge/marshal/cli/challenge.py:L685]
- `write_drift_target(root: Path, slug: str, epic: str, out_dir: Path) -> Path` [AST:src/pyforge/marshal/cli/challenge.py:L707]
- `cut_slice(source: Path, selector: core.Selector) -> tuple[str, str]` — ``(file name, text)`` of ``selector``'s section of ``source``, cut in memory so a selector that names nothing refuses before anything is written. [AST:src/pyforge/marshal/cli/challenge.py:L756]
- `write_slice(root: Path, source: Path, selector: core.Selector, out_dir: Path) -> Path` — Cut ``selector``'s section of ``source`` into a Tier-3 file under ``out_dir`` holding exactly that section, the way ``write_drift_target`` writes the drift target (Story 113.14, CAP-302). [AST:src/pyforge/marshal/cli/challenge.py:L766]
- `write_dream_entry(root: Path, slug: str, cap_slice: core.CapSlice, out_dir: Path) -> tuple[Path, str]` — The Dream entry ``cap_slice`` takes, cut from the station's Dream into a Tier-3 file, and the rule that chose it (``core.dream_entry_section``): the entry or dated bullet it cites, else the newest entry naming one of … [AST:src/pyforge/marshal/cli/challenge.py:L772]
- `audit_plan(root: Path, slice_dir: Path) -> tuple[list[AuditRun], list[str]]` — Every audit run, in order, and why any station's slice could not be cut: the repo rules first, then each station's skill (rules), its newest CAP slice (mint) and the epic range that decomposes it (decompose), the slices … [AST:src/pyforge/marshal/cli/challenge.py:L838]
- `run_audit(*, root: Path, config: core.ChallengeConfig, runner: ChallengeRunner, out_root: Path, force: bool, now: Callable[[], datetime]) -> tuple[Path, dict[str, list[core.ChallengeReport]], list[str]]` [AST:src/pyforge/marshal/cli/challenge.py:L870]
- `append_memlog(root: Path, workspace: str, text: str) -> None` [AST:src/pyforge/marshal/cli/challenge.py:L947]
- `resolve_owner(root: Path, project: str, report: core.ChallengeReport) -> Path` — The Spec folder ``resolve`` acts on (Story 113.13, CAP-303), derived from ``--project``, or for a rules report that records an owner override, from ``RULES_OWNER_OVERRIDES``; never taken from the report. [AST:src/pyforge/marshal/cli/challenge.py:L966]
- `run_resolve(args: argparse.Namespace, *, root: Path, memlog: Callable[[Path, str, str], None]) -> int` — Marshal writes only its own Spec (Story 113.13): an accepted finding another Spec owns is printed as the exact ``memlog.py`` command the operator runs; rejections go back into the report either way. [AST:src/pyforge/marshal/cli/challenge.py:L985]
- `run_challenge(args: argparse.Namespace, *, runner: ChallengeRunner | None = None, root: Path | None = None, now: Callable[[], datetime] = lambda: datetime.now(UTC), memlog: Callable[[Path, str, str], None] = append_memlog) -> int` [AST:src/pyforge/marshal/cli/challenge.py:L1030]
- `readiness_for_dispatch(*, root: Path, slug: str, story_spec: Path, effective: policy.EffectivePolicy, runner: ChallengeRunner | None = None, now: Callable[[], datetime] = lambda: datetime.now(UTC), plugins: Path | None = None, launch_model: str | None = None) -> ReadinessResult` — Run the readiness stage before a dispatch's harness launches, when the switch is on and the station's block names the stage. [AST:src/pyforge/marshal/cli/challenge.py:L1176]
- `readiness_payload(result: ReadinessResult) -> dict[str, object]` [AST:src/pyforge/marshal/cli/challenge.py:L1240]

### `cli/check.py`

- `add_check_subparser(subparsers: argparse._SubParsersAction) -> None` — Register the ``check`` subcommand on ``main.py``'s subparser tree -- a NEW top-level command, sibling to ``status``/``land``/``retire``. [AST:src/pyforge/marshal/cli/check.py:L88]
- `run_check(args: argparse.Namespace, *, process: ProcessPort | None = None, context: MarshalContext | None = None) -> int` [AST:src/pyforge/marshal/cli/check.py:L199]

### `cli/context.py`

- `add_context_subparser(subparsers: argparse._SubParsersAction) -> None` — Register ``context`` with its nested ``refresh``, ``retrieve``, ``bundle``, ``advisory``, ``bootstrap`` and ``pack`` actions. [AST:src/pyforge/marshal/cli/context.py:L131]
- `run_context_refresh(args: argparse.Namespace, *, scribe: ScribeCli | None = None) -> int` — CLI entry for ``marshal context refresh``. [AST:src/pyforge/marshal/cli/context.py:L345]
- `run_context_retrieve(args: argparse.Namespace, *, scribe: ScribeCli | None = None) -> int` — CLI entry for ``marshal context retrieve``. [AST:src/pyforge/marshal/cli/context.py:L486]
- `run_context_bundle(args: argparse.Namespace) -> int` — CLI entry for ``marshal context bundle`` (Story 46.2, spec-pyforge-marshal CAP-192). [AST:src/pyforge/marshal/cli/context.py:L671]
- `run_context_advisory(args: argparse.Namespace, *, scribe: ScribeCli | None = None, process: PosixProcess | None = None, fs: FsPort | None = None) -> int` — CLI entry for ``marshal context advisory`` (Story 46.6, spec-pyforge-marshal CAP-193, fold-remint of spec-marshal-token-economy CAP-20). [AST:src/pyforge/marshal/cli/context.py:L803]

### `cli/dispatch.py`

- `add_factory_dispatch_subparser(factory_subparsers: argparse._SubParsersAction) -> None` [AST:src/pyforge/marshal/cli/dispatch.py:L268]
- `one_in_flight_enabled() -> bool` — Whether a second dispatch onto a busy station is refused (CAP-163's kill switch, ON by default). [AST:src/pyforge/marshal/cli/dispatch.py:L346]
- `dispatch_codegraph_index_enabled() -> bool` — Whether a dispatch worktree is given a codegraph index (CAP-282's kill switch, ON by default). [AST:src/pyforge/marshal/cli/dispatch.py:L351]
- `story_dispatch_preserve_tag(fs: FsPort, repo_root: Path, slug: str, story_key: str) -> str | None` — Story 87.5: the ``preserve_tag`` from this story's latest dispatch run, if any. [AST:src/pyforge/marshal/cli/dispatch.py:L1551]
- `gather_fleet_finalize_escalations(*, fs: FsPort, repo_root: Path) -> dict[str, dispatch_fleet.FinalizeEscalation]` — Active supervisor-finalize shell failures (Story 28.24, CAP-7). [AST:src/pyforge/marshal/cli/dispatch.py:L1679]
- `iter_dispatch_run_dirs(repo_root: Path, slug: str) -> tuple[Path, ...]` [AST:src/pyforge/marshal/cli/dispatch.py:L1811]
- `latest_dispatch_run_dir(repo_root: Path, slug: str) -> Path | None` [AST:src/pyforge/marshal/cli/dispatch.py:L1827]
- `gather_dispatch_journal_facts(fs: FsPort, run_dir: Path, run_id: str) -> dispatch_core.DispatchJournalFacts` [AST:src/pyforge/marshal/cli/dispatch.py:L1834]
- `resolve_dispatch_session_verdict(*, fs: FsPort, vcs: VcsPort, process: ProcessPort, repo_root: Path, slug: str, journal: dispatch_core.DispatchJournalFacts, effective_policy: policy.EffectivePolicy, run_dir: Path | None = None, spec_relative_path: str | None = None) -> DispatchSessionVerdict | None` [AST:src/pyforge/marshal/cli/dispatch.py:L2043]
- `resolve_max_parallel(effective_policy: policy.EffectivePolicy, *, cli_override: int | None = None, policy_flags: dict[str, object] | None = None) -> int` — Factory-dispatch parallel cap (Story 28.16, CAP-4; Story 33.8, CAP-6). [AST:src/pyforge/marshal/cli/dispatch.py:L2223]
- `station_finalize_pending_story(*, fs: FsPort, process: ProcessPort, repo_root: Path, slug: str, backlog: Sequence[str], effective_policy: policy.EffectivePolicy) -> tuple[str, str] | None` — ``(story, evidence)`` when this station's head is mid-finalize (50.1). [AST:src/pyforge/marshal/cli/dispatch.py:L2274]
- `station_in_flight_conflict(*, fs: FsPort, vcs: VcsPort, process: ProcessPort, repo_root: Path, slug: str, story_key: str, effective_policy: policy.EffectivePolicy, harness_reported_failure: bool = False, candidate_spec_text: str | None = None, deps_graph: Mapping[str, tuple] | None = None, parallel_dispatch: bool = False, preflight_advisories: list[Finding] | None = None) -> DispatchPreflightConflict | None` — Refuse when an in-flight story blocks this candidate (22.5 / 28.16). [AST:src/pyforge/marshal/cli/dispatch.py:L2435]
- `spin_loop_home_in_flight_conflict(*, fs: FsPort, vcs: VcsPort, process: ProcessPort, harness: HarnessPort, home: Path, slug: str, story_key: str, effective_policy: policy.EffectivePolicy, preflight_advisories: list[Finding] | None = None) -> DispatchPreflightConflict | None` — Refuse ``factory spin`` when this loop home already has a live run (34.1). [AST:src/pyforge/marshal/cli/dispatch.py:L2614]
- `cross_station_surface_overlap_advisories(*, fs: FsPort, vcs: VcsPort, process: ProcessPort, repo_root: Path, requested_slug: str, requested_story_key: str, requested_spec_text: str) -> tuple[Finding, ...]` — Loud WARN advisories for overlapping declared surfaces (Story 22.5). [AST:src/pyforge/marshal/cli/dispatch.py:L2676]
- `station_story_block_facts(*, fs: FsPort, vcs: VcsPort, process: ProcessPort, repo_root: Path, slug: str, story_key: str, effective_policy: policy.EffectivePolicy, followup_entry: bool = False) -> dispatch_fleet.StationBlockEvidence | None` — Evidence + environment/story classification for a blocked story (34.3). [AST:src/pyforge/marshal/cli/dispatch.py:L2738]
- `station_story_blocked_evidence(*, fs: FsPort, vcs: VcsPort, process: ProcessPort, repo_root: Path, slug: str, story_key: str, effective_policy: policy.EffectivePolicy) -> str | None` [AST:src/pyforge/marshal/cli/dispatch.py:L2944]
- `live_dispatch_conflict(*, fs: FsPort, vcs: VcsPort, process: ProcessPort, repo_root: Path, slug: str, story_key: str, effective_policy: policy.EffectivePolicy, harness_reported_failure: bool = False) -> str | None` — Same-story live redispatch refusal (Story 22.2); delegates to CAP-5 guard. [AST:src/pyforge/marshal/cli/dispatch.py:L2966]
- `run_dispatch(args: argparse.Namespace, *, fs: FsPort | None = None, vcs: CommittingVcs | None = None, build_harness: BuildHarnessPort | None = None, process: ProcessPort | None = None, harness: HarnessPort | None = None, context: MarshalContext | None = None) -> int` — ``marshal factory dispatch <slug> <story>`` -- or, with ``--stories`` (Story 22.11, FR-193 CAP-10), a caller-supplied ordered sequence chained on this one station via ``run_fleet_drain``'s existing campaign machinery  … [AST:src/pyforge/marshal/cli/dispatch.py:L2993]
- `dispatch_once(*, slug: str, story: str, fs: FsPort | None = None, vcs: CommittingVcs | None = None, build_harness: BuildHarnessPort | None = None, process: ProcessPort | None = None, policy_flags: dict[str, object] | None = None, parallel_dispatch: bool = False, hold_landing: bool = False) -> DispatchAttempt` — Launch exactly one governed story session and report data + findings. [AST:src/pyforge/marshal/cli/dispatch.py:L3122]
- `add_factory_dispatch_attach_subparser(factory_subparsers: argparse._SubParsersAction) -> None` [AST:src/pyforge/marshal/cli/dispatch.py:L4276]
- `add_factory_dispatch_resume_subparser(factory_subparsers: argparse._SubParsersAction) -> None` [AST:src/pyforge/marshal/cli/dispatch.py:L4290]
- `run_dispatch_attach(args: argparse.Namespace, *, fs: FsPort | None = None, vcs: VcsPort | None = None, process: ProcessPort | None = None) -> int` [AST:src/pyforge/marshal/cli/dispatch.py:L4310]
- `run_dispatch_resume(args: argparse.Namespace, *, fs: FsPort | None = None, vcs: VcsPort | None = None, process: ProcessPort | None = None) -> int` [AST:src/pyforge/marshal/cli/dispatch.py:L4407]
- `add_factory_drain_subparser(factory_subparsers: argparse._SubParsersAction) -> None` [AST:src/pyforge/marshal/cli/dispatch.py:L4482]
- `gather_fleet_missing_spec_escalations(*, fs: FsPort, harness: HarnessPort, vcs: VcsPort, repo_root: Path) -> dict[str, dispatch_fleet.MissingSpecEscalation]` — Active ``MRS-DISP-005`` campaign blocks that still lack a tracked spec. [AST:src/pyforge/marshal/cli/dispatch.py:L4729]
- `resolve_cycle_slugs(repo_root: Path, station: str | None) -> CycleSlugs` — The live pyforge stations one cycle walks, ``station`` narrowing to one. [AST:src/pyforge/marshal/cli/dispatch.py:L5187]
- `plan_followup_reviews(*, repo_root: Path, slugs: Sequence[str], vcs: VcsPort, launched: frozenset[tuple[str, StoryKey]] = frozenset(), policy_flags: dict[str, object] | None = None, fetch: bool = True) -> FollowupPlan` — The campaign's follow-up review decision for ``slugs`` (Story 73.2, spec-pyforge-marshal CAP-281). [AST:src/pyforge/marshal/cli/dispatch.py:L5273]
- `plan_station_cycle(*, repo_root: Path, slug: str, mode: dispatch_fleet.FleetCampaignMode, leave_remaining: int, campaign_blocked: Mapping[str, str], order_override: Sequence[str] | None, station_skips: Mapping[str, str], explicit_stories: tuple[str, ...] | None, policy_flags: dict[str, object] | None, max_in_flight: int | None, retry_environment_blocks: bool, fs: FsPort, vcs: VcsPort, process: ProcessPort, harness: HarnessPort, mint_wave_id: Callable[[], str], followups: Sequence[dispatch_fleet.FollowupCandidate] = ()) -> StationCyclePlan` — One station's per-cycle queue computation -- READ-ONLY (Story 65.1). [AST:src/pyforge/marshal/cli/dispatch.py:L5489]
- `wave_held_stories(cycle: StationCyclePlan) -> tuple[str, ...]` — Every story a parallel wave holds out of this cycle (pure, Story 81.1). [AST:src/pyforge/marshal/cli/dispatch.py:L5665]
- `skip_basis(*, story: str, reason: str, station_skips: Mapping[str, str], block_classes: Mapping[str, dispatch_fleet.FleetBlockClass], mode: dispatch_fleet.FleetCampaignMode) -> str` — Why ``plan_station_queue`` stepped past ``story`` -- the wording the cycle's ``MRS-DRAIN-004`` names and ``factory drain --plan`` reports. [AST:src/pyforge/marshal/cli/dispatch.py:L5682]
- `execute_fleet_cycle(*, repo_root: Path, mode: dispatch_fleet.FleetCampaignMode, leave_remaining: int, campaign_blocked: dict[str, dict[str, str]], fs: FsPort, vcs: CommittingVcs, build_harness: BuildHarnessPort, process: ProcessPort, harness: HarnessPort, station: str | None = None, explicit_stories: tuple[str, ...] | None = None, policy_flags: dict[str, object] | None = None, max_in_flight: int | None = None, retry_environment_blocks: bool = False, followups_launched: frozenset[tuple[str, StoryKey]] = frozenset()) -> FleetCycleReport` — One fleet-drain cycle: plan every station, dispatch the eligible ones. [AST:src/pyforge/marshal/cli/dispatch.py:L5705]
- `run_fleet_drain(args: argparse.Namespace, *, fs: FsPort | None = None, vcs: CommittingVcs | None = None, build_harness: BuildHarnessPort | None = None, process: ProcessPort | None = None, harness: HarnessPort | None = None, context: MarshalContext | None = None) -> int` — ``marshal factory drain`` -- the one documented fleet-drain command. [AST:src/pyforge/marshal/cli/dispatch.py:L6403]

### `cli/init.py`

- `add_init_subparser(subparsers: argparse._SubParsersAction) -> None` — Register the ``init`` subcommand on ``main.py``'s subparser tree. [AST:src/pyforge/marshal/cli/init.py:L301]
- `add_homes_subparser(subparsers: argparse._SubParsersAction) -> None` — Register the ``homes`` subcommand on ``main.py``'s subparser tree (Story 1.6, FR-4/FR-8). [AST:src/pyforge/marshal/cli/init.py:L326]
- `published_story_tasks(project_slug: str) -> dict[str, dict] | None` — Published-plane per-story task records; None when the host plane is unreachable. [AST:src/pyforge/marshal/cli/init.py:L349]
- `run_init(args: argparse.Namespace, *, vcs: VcsPort | None = None, fs: FsPort | None = None) -> int` [AST:src/pyforge/marshal/cli/init.py:L630]
- `run_homes(args: argparse.Namespace, *, vcs: VcsPort | None = None, fs: FsPort | None = None) -> int` [AST:src/pyforge/marshal/cli/init.py:L1057]
- `add_preflight_subparser(subparsers: argparse._SubParsersAction) -> None` — Register the ``preflight`` subcommand (Story 1.7, FR-7/FR-47/FR-52). [AST:src/pyforge/marshal/cli/init.py:L1253]
- `run_preflight(args: argparse.Namespace, *, vcs: VcsPort | None = None, fs: FsPort | None = None, harness: HarnessPort | None = None, kit_probe=None, kit_index_builder=None, mcp_probe: McpProbePort | None = None) -> int` — Story 28.3 adds two more DI seams alongside ``vcs``/``fs``/``harness``: ``kit_probe`` (a ``seed.detect.kit.probe_instrument``-shaped callable deciding whether an instrument is available) and ``kit_index_builder`` (a … [AST:src/pyforge/marshal/cli/init.py:L1406]
- `add_teardown_subparser(subparsers: argparse._SubParsersAction) -> None` — Register the ``teardown`` subcommand (Story 1.8, NFR-6/AD-29). [AST:src/pyforge/marshal/cli/init.py:L2110]
- `run_teardown(args: argparse.Namespace, *, vcs: VcsPort | None = None, fs: FsPort | None = None) -> int` [AST:src/pyforge/marshal/cli/init.py:L2321]

### `cli/main.py`

- `main(argv: list[str] | None = None) -> int` — Parse ``argv`` and return an exit code -- never raises ``SystemExit`` itself. [AST:src/pyforge/marshal/cli/main.py:L348]

### `cli/seed.py`

- `packaged_seed_model_version() -> ModelVersion` — The bundled manifest's ``model_version``, for a caller that needs the clock but not the model (Story 28.3: ``cli/init.py``'s preflight stamps it into the deployed skill's managed-region marker). [AST:src/pyforge/marshal/cli/seed.py:L147]
- `resolve_context_layers(repo_root: Path, explicit_slug: str | None) -> dict[str, dict[str, object]]` — Story 28.1's `[context]` declaration, resolved for ``repo_root``. [AST:src/pyforge/marshal/cli/seed.py:L275]
- `run_check(args: argparse.Namespace, *, manifest: Manifest | None = None, vcs: VcsPort | None = None) -> int` — ``marshal seed check`` (Story 10.5): thin CLI plumbing over ``seed.verbs.check.run_check``, the pure read-only detector -- this function performs no detect/plan/hash/region logic of its own. [AST:src/pyforge/marshal/cli/seed.py:L458]
- `run_adopt(args: argparse.Namespace, *, manifest: Manifest | None = None, confirm: Callable[[], bool] | None = None) -> int` — ``marshal seed adopt`` (Story 10.6): thin CLI plumbing over ``seed.verbs.adopt.run_adopt`` -- this function performs no detect/plan/apply/materialize logic of its own; every real decision is that module's (see its own … [AST:src/pyforge/marshal/cli/seed.py:L642]
- `run_init(args: argparse.Namespace, *, manifest: Manifest | None = None) -> int` — ``marshal seed init`` (Story 10.7): thin CLI plumbing over ``seed.verbs.init.run_init`` -- this function performs no bootstrap/detect/plan/apply/materialize logic of its own; every real decision is that module's (see … [AST:src/pyforge/marshal/cli/seed.py:L778]
- `run_update(args: argparse.Namespace, *, manifest: Manifest | None = None, confirm: Callable[[], bool] | None = None) -> int` — ``marshal seed update`` (Story 11.4): thin CLI plumbing over ``seed.verbs.update.run_update`` -- this function performs no detect/plan/migrate/apply/materialize logic of its own; every real decision is that module's … [AST:src/pyforge/marshal/cli/seed.py:L902]
- `run_kit(args: argparse.Namespace, *, manifest: Manifest | None = None, fs: FsPort | None = None) -> int` — ``marshal seed kit`` (Story 28.3): thin CLI plumbing over ``seed.verbs.kit.run_kit`` -- Genesis's provisioning of the per-loop-home token-economy kit (SPEC-marshal-token-economy CAP-3/CAP-4). [AST:src/pyforge/marshal/cli/seed.py:L1037]
- `run_accept(args: argparse.Namespace, *, manifest: Manifest | None = None) -> int` — ``marshal seed accept`` (Story 97.1): thin CLI plumbing over ``seed.verbs.accept.run_accept`` -- this function performs no hash/region/state logic of its own. [AST:src/pyforge/marshal/cli/seed.py:L1109]
- `run_explain(args: argparse.Namespace, *, manifest: Manifest | None = None) -> int` — ``marshal seed explain`` (Story 11.6): thin CLI plumbing over ``seed.verbs.explain.run_explain`` -- read-only manifest lookup. [AST:src/pyforge/marshal/cli/seed.py:L1165]
- `run_version(args: argparse.Namespace, *, manifest: Manifest | None = None) -> int` — ``marshal seed version`` (Story 11.6): thin CLI plumbing over ``seed.verbs.version.run_version`` -- read-only version reporting. [AST:src/pyforge/marshal/cli/seed.py:L1207]
- `add_seed_subparser(subparsers: argparse._SubParsersAction) -> None` — Register the ``seed`` subcommand on ``main.py``'s subparser tree, with eight nested verb actions -- mirrors ``cli/gate.py::add_gate_subparser``'s identical nested-subparsers shape, one level down (eight verbs instead of … [AST:src/pyforge/marshal/cli/seed.py:L1250]

### `cli/spin.py`

- `add_factory_subparser(subparsers: argparse._SubParsersAction) -> None` — Register the ``factory`` subcommand on ``main.py``'s subparser tree, with nested ``spin``/``attach`` actions (mirrors ``cli/gate.py``'s own nested-action shape). [AST:src/pyforge/marshal/cli/spin.py:L1112]
- `run_spin(args: argparse.Namespace, *, fs: FsPort | None = None, harness: HarnessPort | None = None, process: ProcessPort | None = None, context: MarshalContext | None = None) -> int` [AST:src/pyforge/marshal/cli/spin.py:L1570]
- `run_resume(args: argparse.Namespace, *, fs: FsPort | None = None, harness: HarnessPort | None = None, process: ProcessPort | None = None) -> int` [AST:src/pyforge/marshal/cli/spin.py:L2475]
- `run_attach(args: argparse.Namespace, *, fs: FsPort | None = None, harness: HarnessPort | None = None) -> int` — ``marshal factory attach <slug>`` -- unlike ``run_spin``, this NEVER builds an ``Envelope`` (the spec's own Always bullet: "attach does NOT [build one] -- it hands the terminal to the multiplexer and relays bmad-loop's … [AST:src/pyforge/marshal/cli/spin.py:L3004]

### `cli/status.py`

- `dispatch_only_fleet_rows_enabled() -> bool` — Whether a dispatch-only station gets a placeholder fleet row (CAP-259's kill switch, ON by default). [AST:src/pyforge/marshal/cli/status.py:L208]
- `add_status_subparser(subparsers: argparse._SubParsersAction) -> None` — Register the ``status`` subcommand on ``main.py``'s subparser tree -- a NEW top-level command, sibling to ``deploy``/``land``/``retire`` (the story's own Code Map). [AST:src/pyforge/marshal/cli/status.py:L474]
- `list_live_dispatch_stories(*, fs: FsPort, vcs: VcsPort, process: ProcessPort, repo_root: Path, slug: str, effective_policy) -> tuple[str, ...]` — Every LIVE factory-dispatch story key on ``slug`` (Story 28.16). [AST:src/pyforge/marshal/cli/status.py:L900]
- `latest_dispatch_wave_id(repo_root: Path, slug: str) -> str | None` — Most recent ``dispatch-wave`` journal id for ``slug``, if any. [AST:src/pyforge/marshal/cli/status.py:L922]
- `run_status(args: argparse.Namespace, *, vcs: VcsPort | None = None, fs: FsPort | None = None, harness: HarnessPort | None = None, process: ProcessPort | None = None, clock: ClockPort | None = None, context: MarshalContext | None = None) -> int` [AST:src/pyforge/marshal/cli/status.py:L1734]

### `core/verdict.py`

- `classify(code: str) -> Verdict` — Total classification: a registered finding ``code`` -> its lattice member (AD-31). [AST:src/pyforge/marshal/core/verdict.py:L1436]
- `compute_verdict(findings: Iterable[Finding], *, floor: Verdict = Verdict.CLEAN) -> Verdict` — The verdict for a command: the maximum (strongest, per ``LATTICE_ORDER``) over every emitted finding's classification, plus a command-declared ``floor`` (AD-31). [AST:src/pyforge/marshal/core/verdict.py:L1453]
- `exit_code_for(verdict: Verdict | str) -> int` — Project a ``Verdict`` to its process exit code -- TOTAL over the closed 6-member lattice (AD-7). [AST:src/pyforge/marshal/core/verdict.py:L1473]
- `relay_exit_code(child_code: int) -> int` — Project a RELAYED child process's exit code into the frozen domain (AD-7) -- for the handlers that hand a terminal to another process and report its result instead of an ``Envelope``'s (Story 3.3's ``marshal factory … [AST:src/pyforge/marshal/core/verdict.py:L1480]

### `mcp/server.py`

- `build_server(name: str = SERVER_NAME)` — Build the official MCP server exposing Marshal's named typed tools. [AST:src/pyforge/marshal/mcp/server.py:L30]
- `main(argv: list[str] | None = None) -> int` — Console-script entry for ``marshal-mcp``. [AST:src/pyforge/marshal/mcp/server.py:L116]

### `mcp/tools.py`

- `list_marshal_tools() -> dict[str, Any]` — Structured inventory of named tools (no CLI invocation). [AST:src/pyforge/marshal/mcp/tools.py:L87]
- `run_marshal(argv: Sequence[str], *, main: Callable[[list[str] | None], int] | None = None) -> dict[str, Any]` — Invoke the marshal CLI in-process; return a structured answer. [AST:src/pyforge/marshal/mcp/tools.py:L103]
- `marshal_status(project: str | None = None, *, main: Callable[[list[str] | None], int] | None = None) -> dict[str, Any]` [AST:src/pyforge/marshal/mcp/tools.py:L176]
- `marshal_check(scope: str = "all", project: str | None = None, *, main: Callable[[list[str] | None], int] | None = None) -> dict[str, Any]` [AST:src/pyforge/marshal/mcp/tools.py:L184]
- `marshal_homes(*, main: Callable[[list[str] | None], int] | None = None) -> dict[str, Any]` [AST:src/pyforge/marshal/mcp/tools.py:L196]
- `marshal_preflight(slug: str, *, main: Callable[[list[str] | None], int] | None = None) -> dict[str, Any]` [AST:src/pyforge/marshal/mcp/tools.py:L203]
- `marshal_upstream(*, main: Callable[[list[str] | None], int] | None = None) -> dict[str, Any]` [AST:src/pyforge/marshal/mcp/tools.py:L211]
- `marshal_refresh(project: str | None = None, base: str | None = None, *, main: Callable[[list[str] | None], int] | None = None) -> dict[str, Any]` [AST:src/pyforge/marshal/mcp/tools.py:L218]
- `marshal_watch(project: str | None = None, run: str | None = None, fleet: bool = False, *, main: Callable[[list[str] | None], int] | None = None) -> dict[str, Any]` [AST:src/pyforge/marshal/mcp/tools.py:L230]
- `marshal_preserve_list(station: str | None = None, story: str | None = None, producer: str | None = None, state: str | None = None, *, main: Callable[[list[str] | None], int] | None = None) -> dict[str, Any]` [AST:src/pyforge/marshal/mcp/tools.py:L243]
- `marshal_preserve_push(pending: bool = False, *, main: Callable[[list[str] | None], int] | None = None) -> dict[str, Any]` [AST:src/pyforge/marshal/mcp/tools.py:L263]
- `marshal_preserve_retire(tag: str, evidence: str, *, main: Callable[[list[str] | None], int] | None = None) -> dict[str, Any]` [AST:src/pyforge/marshal/mcp/tools.py:L271]
- `mcp_server_registration_spec() -> Mapping[str, Mapping[str, object]]` — Policy-shaped ``mcp_servers`` entry for Marshal itself (FR-154). [AST:src/pyforge/marshal/mcp/tools.py:L280]
- `assert_no_absolute_command(command: str) -> None` — Raise ``ValueError`` if ``command`` looks machine-absolute. [AST:src/pyforge/marshal/mcp/tools.py:L295]

## Full Type Definitions

Every public class the extract found, by module, in source order.

### `cli/challenge.py` types

- `class ChallengeRunner(Protocol)` — Runs one session on ``root``'s files; ``target`` is the artifact under review, which the session's Read denies leave readable (Story 113.10). [AST:src/pyforge/marshal/cli/challenge.py:L100]
- `class ChallengeRefused(PyforgeError, Exception)` — A refusal the verb reports with the usage code; never a finding. [AST:src/pyforge/marshal/cli/challenge.py:L110]
- `class RunOutcome` [AST:src/pyforge/marshal/cli/challenge.py:L115]
- `class AuditRun` — One review the sweep makes. [AST:src/pyforge/marshal/cli/challenge.py:L794]
- `class ReadinessResult` — What the dispatch hook journals and reports. [AST:src/pyforge/marshal/cli/challenge.py:L1165]

### `cli/dispatch.py` types

- `class DispatchPreflightConflict` — A dispatch refusal with its registered finding code (Story 22.2/22.5). [AST:src/pyforge/marshal/cli/dispatch.py:L202]
- `class DispatchAttempt` — One ``dispatch_once`` outcome: envelope ``data`` plus its findings. [AST:src/pyforge/marshal/cli/dispatch.py:L212]
- `class FleetCycleReport` — One fleet-drain cycle's per-station results, findings, and data. [AST:src/pyforge/marshal/cli/dispatch.py:L229]
- `class Cap4VerificationResult` — Independent verify outcome for the harness-done land-only path (Story 22.17). [AST:src/pyforge/marshal/cli/dispatch.py:L357]
- `class StructureGraphSeed` — ``_seed_dispatch_structure_graph``'s outcome for ONE dispatch (Story 77.1, CAP-282), the ``structure-graph`` twin of ``harness_profile.WireWrap``. [AST:src/pyforge/marshal/cli/dispatch.py:L921]
- `class DispatchWorktreeResolution` — A provisioned dispatch worktree, or the refusal that stopped it (22.9). [AST:src/pyforge/marshal/cli/dispatch.py:L1763]
- `class CycleSlugs` — The stations one drain cycle walks (Story 65.1: extracted from ``execute_fleet_cycle`` so ``factory drain --plan`` resolves them the same way). [AST:src/pyforge/marshal/cli/dispatch.py:L5175]
- `class FollowupPlan` — What a drain campaign does about the follow-up reviews landed stories recommended (Story 73.2, CAP-281). [AST:src/pyforge/marshal/cli/dispatch.py:L5228]
- `class StationCyclePlan` — One station's queue computation for one drain cycle (Story 65.1). [AST:src/pyforge/marshal/cli/dispatch.py:L5446]

### `seed/errors.py` types

- `class SeedError(PyforgeError, Exception)` — Root of every `seed` exception. [AST:src/pyforge/marshal/seed/errors.py:L70]
- `class ConformanceFailure(SeedError)` — A target repo failed conformance (HARD findings). [AST:src/pyforge/marshal/seed/errors.py:L132]
- `class UsageError(SeedError)` — A caller-supplied argument or flag was invalid. [AST:src/pyforge/marshal/seed/errors.py:L142]
- `class PreconditionFailure(SeedError)` — A required precondition did not hold: a dirty worktree, a target that is not a git repo, or hand-edited managed content. [AST:src/pyforge/marshal/seed/errors.py:L152]
- `class NeverWriteViolation(SeedError)` — A write target matched the never-write set (Tier-0 Dreams, Tier-2 planning artifacts, Tier-3, legacy specs, BMAD installer files; architecture AD-61). [AST:src/pyforge/marshal/seed/errors.py:L163]
- `class StateInvalid(SeedError)` — `.marshal/seed-state.yml` (or other persisted `seed` state) was missing, unreadable, or failed its schema. [AST:src/pyforge/marshal/seed/errors.py:L174]
- `class InternalError(SeedError)` — An unanticipated internal failure -- the catch-all for anything not covered by the five leaves above. [AST:src/pyforge/marshal/seed/errors.py:L184]
