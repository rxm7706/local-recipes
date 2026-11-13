---
name: pyforge-herald
description: >
  Seeds, pulls, and reports Claude Design deck bridge state via the herald
  CLI. Use when running herald deck seed / pull / status, or working in
  src/shared/packages/pyforge-herald/. Do not import pyforge.herald
  internals; the CLI is the public contract. Do not use for conda-forge
  recipe authoring (conda-forge-expert) or Lane 1 CMS (steward).
---

# pyforge-herald

## Overview

Compiles `src/shared/packages/pyforge-herald/` (PyPI `pyforge-herald` 0.1.0) as an
agentskills.io content skill for the **herald** station. Source: local path
`src/shared/packages/pyforge-herald` @ commit `b69fd81eb8` (`source_ref: local`).
Forge tier: **Quick** (SKF `skf-extract-public-api` + source-reading; T1-low).
First compiled from `865b95dc951` (Story 29.1); recompiled in place at 0.1.0 on
2026-11-12 (steward Story 29.5, the fixes the EGM audit of 2026-11-05 accepted:
HER-R-F1, HER-R-F17, HER-R-F27, HER-R-F28, with HER-R-F16 and HER-R-F29 carried)
from the scope widened with `errors.py`, `deck_pipeline.py` and
`transport/mcp_transport.py`, the `cli.py` help strings herald Story 50.3 corrected,
the station contract `contract.md` and `bridge-protocol.md` as doc sources, and the
real `herald --help`, the way Story 29.1 and atlas Stories 33.1 and 33.2 did.
2 CLI exports documented (`main`, `dispatch`).
The package `__init__.py` exports only `__version__` — other components integrate
via the CLI, never by importing internal modules [SRC:src/pyforge/herald/__init__.py:L12].

## Description

Dream-to-deck bridge CLI that seeds, pulls, and syncs Claude Design decks
against this repo's `docs/dreams/` and `presentations/` trees via the
`herald deck` subcommands [SRC:pyproject.toml:L8]; also the Herald Moments 2-4
CLI (`progress`, `success`, `notice`) and the `scheduler` [SRC:src/pyforge/herald/cli.py:L207-L224].

**Claude Design** is Anthropic's design surface (`https://claude.ai/design`), where
each deck lives as a Design project. Herald reaches it through the `claude-design`
MCP server at `https://api.anthropic.com/v1/design/mcp`, as a plain MCP client
authenticated with the OAuth token the Claude Code CLI stored for `/design-login`
(`~/.claude/.credentials.json`, or the file `HERALD_DESIGN_CREDENTIALS` names).
Herald only reads that token: a missing or expired one is an `AuthError` (exit 4)
whose message names `/design-login` — the operator signs in again; herald never
mints or refreshes a token [SRC:src/pyforge/herald/transport/mcp_transport.py:L1-L21]
[SRC:src/pyforge/herald/transport/mcp_transport.py:L90-L97].

**The public contract** is
`_bmad-output/projects/pyforge-herald/planning-artifacts/specs/spec-pyforge-herald/contract.md`
(spec-pyforge-herald:CAP-62): every CLI verb with its arguments and the capability it
realizes, the MCP tools, the feature-flag keys, the environment variables, the error
classes and the exit codes. The tool-call loop the deck verbs wrap is
`bridge-protocol.md` in the same Spec folder. The MCP tool names, exit codes, flag
keys and capability ids in this skill are rows of those files; where they differ,
the contract and the code win.

## Quick Start

Run from the repository root (never a hardcoded absolute path)
[SRC:src/pyforge/herald/cli.py:L231-L236]:

```bash
pixi run -e pyforge-herald herald deck seed <slug>
pixi run -e pyforge-herald herald deck pull <slug>
pixi run -e pyforge-herald herald deck status [slug]
```

Unified grammar for Path B is `pyforge herald …` (same argv after `pyforge`).

**Seed** (`herald deck seed <slug>`) [SRC:src/pyforge/herald/cli.py:L231-L245]:
seed a deck slug into Claude Design (spec-pyforge-herald:CAP-1, CAP-4). It writes a
**new project into the operator's Claude Design account**: after proving the local
prototype (`npm run extract` and `npm run build` in `presentations/<slug>/`), it
fetches the design-system prompt, creates the project, writes `support.js`, a
server-side copy of `deck-stage.js` and the prototype, then records the project in
the bridge state and the deck README's § *Design project*. It refuses with
`SeedConflictError` (exit 3) when the slug is already seeded
[SRC:src/pyforge/herald/deck_pipeline.py:L158-L174].

**Pull** (`herald deck pull <slug> [--commit] [--target …]`)
[SRC:src/pyforge/herald/cli.py:L246-L275]: pull a deck's prototype (or, with
`--target`, a Marp source or the standalone bundle) from Claude Design into the repo
(spec-pyforge-herald:CAP-1, CAP-4). It needs a prior seed. An unchanged etag returns
at once and writes nothing; a change **overwrites the tracked file under
`presentations/<slug>/`**, records the new etag and re-derives the deck (extract,
build, `deck-export`). The files stay **uncommitted** unless `--commit`, which
stages and commits `presentations/<slug>/` and the bridge-state file — and never
commits an unchanged pull [SRC:src/pyforge/herald/deck_pipeline.py:L716-L729].

**Status** (`herald deck status [slug] [--account]`) [SRC:src/pyforge/herald/cli.py:L276-L301]:
print one JSON array of bridge state for one slug or every known deck
(spec-pyforge-herald:CAP-4) [SRC:src/pyforge/herald/cli.py:L940-L1008]; each row is
`{slug, linked, project_id, sync, last_pull, stale_mirror}`. `sync` is `null` for an
unlinked deck and, for a linked one, `"unchanged"` (every tracked artifact's etag
still matches, or nothing was pulled yet), `"changed"` (at least one etag moved) or
`"conflict"` (a comparison itself failed: the transport raised, or the tracked file
is gone server-side — resolve it before pulling); `stale_mirror` flags a
hand-mirrored Design project [SRC:src/pyforge/herald/deck_pipeline.py:L1316-L1338].
`--account` reports every Design project the signed-in account can see, reconciled
against the registry (spec-pyforge-herald:CAP-29), and takes no slug.

**The other deck verbs** [SRC:src/pyforge/herald/cli.py:L302-L481]: `watch <slug>...`
polls for Design-side edits and pulls once settled; `push <slug> [--prove]` pushes
regenerated derived exports back into Design (spec-pyforge-herald:CAP-4, CAP-34);
`publish <slug> [--dry-run]` and `exports <slug> --json` publish and read a deck's
exports in object storage (spec-pyforge-herald:CAP-54, behind
`pyforge.herald.deck_publish`); `sync-all [--slug S] [--dry-run] [--proof-dir D]` runs
enumerate, pull, refresh, derive, push, prove and publish in order
(spec-pyforge-herald:CAP-36); `qa <slug>` runs the visual-QA gates
(spec-pyforge-herald:CAP-26..CAP-28); `pptx-spec` and `pptx-fill` parse and fill a
`.pptx`/`.potx` template (spec-pyforge-herald:CAP-41); `pptx-native <slug>` exports
the Marp source as a native editable `.pptx` (spec-pyforge-herald:CAP-57, behind
`pyforge.herald.deck_export_native`). A verb whose flag is off stays listed in
`--help`, marked disabled, and exits 2.

<!-- [MANUAL:additional-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:additional-notes] -->

## Station MCP runner

What `POST /stations/herald/mcp` runs, as the code stands (`contract.md` § *MCP
tools*; the host face is django-herald's `mcp_asgi.py`, the runner a row of
django-pyforge's closed verb table; this package ships no MCP server):

| Tool | What it does |
|---|---|
| `start_notice` | Takes a `target` and an `assertion`; returns a handle at once. |
| `get_notice` | Takes a `handle` and an `assertion`; returns that supervised run. |

Behind them the supervisor runs herald's row under the runner key `run_notice` (not
an MCP tool): `herald notice get <target>` in `pyforge-guild`, where the target is
one name. It runs that read and nothing else: no `deck` verb (no seed, pull or push
into Claude Design), no `success`, `progress` or `scheduler`, and no notice write.

## Common Workflows

**Seed then inspect:** `herald deck seed <slug>` then `herald deck status <slug>`.

**Pull a settled edit:** `herald deck pull <slug>` then `herald deck status <slug>`
to read `stale_mirror` / `sync` in the JSON report; review the pulled files, then
commit them yourself, or pull again with `--commit`.

**Whole fleet:** `herald deck sync-all --dry-run`, then without `--dry-run`.

## Key API Summary

| Function | Purpose | Key params |
|---|---|---|
| `main` | Argparse entry (`herald` console script) | `argv` |
| `dispatch` | Sole `HeraldError` catch point (AD-6) | `operation`, `json_output` |
| `_run_deck_seed` | `deck seed` (spec-pyforge-herald:CAP-1, CAP-4) | `args.slug`, `--support-source-project` |
| `_run_deck_pull` | `deck pull` (spec-pyforge-herald:CAP-1, CAP-4) | `args.slug`, `--commit`, `--target` |
| `_run_deck_status` | `deck status`, JSON (spec-pyforge-herald:CAP-4, CAP-29) | `args.slug` optional, `--account` |

## Key Exports

Public SKF extract of `cli.py` (Quick mode): `main`, `dispatch`
[SRC:src/pyforge/herald/cli.py]. Console script:
`herald = pyforge.herald.cli:main` [SRC:pyproject.toml:L73-L74].
Top-level commands: `deck`, `progress`, `success`, `notice`, `scheduler`
[SRC:src/pyforge/herald/cli.py:L87].

## Usage

Always invoke `herald` from repo root. Do not `from pyforge.herald import …`
in other stations or under `src/platform/`. Agents acting as the herald
persona must emit canopy:FR-13 `pyforge herald …` or canopy:FR-11
`POST /stations/herald/mcp`. Lane 1 CMS stays steward. `deck seed` and `deck push`
write into the operator's Claude Design account, and `deck pull` overwrites tracked
deck files: run them when the operator asks.

Exit codes (`contract.md` § *Exit codes*; `exit_code_for` is the one owner of the
projection) [SRC:src/pyforge/herald/errors.py:L219-L232]: `0` success, `--help`,
`--version` · `1` no command given, or any `HeraldError` the map does not name ·
`2` usage (argparse's own exit, `DeckUsageError`, a verb whose flag is off, `deck
exports` without `--json`) · `3` a conflict (`SeedConflictError`,
`PullConflictError`, `ExportConflictError`) · `4` a transport failure
(`TransportError` and every class under it, `AuthError` included). A
`KeyboardInterrupt` returns `130`, outside the closed set. `dispatch` writes one line
to stderr (one JSON object with `--json`) and returns the code
[SRC:src/pyforge/herald/cli.py:L1915].

## Key Types

**`TOOL_NAME`** [SRC:src/pyforge/herald/cli.py:L85] — `"herald"`.

**`TOP_LEVEL_COMMANDS`** [SRC:src/pyforge/herald/cli.py:L87] —
`deck`, `progress`, `success`, `notice`, `scheduler`.

**`DeckStatus`** [SRC:src/pyforge/herald/deck_pipeline.py:L1316] — one deck's status
row: `slug`, `linked`, `project_id`, `sync`, `last_pull`, `stale_mirror`.

## Architecture at a Glance

- **Deck** — twelve verbs against Claude Design: seed / pull / status / watch / push /
  publish / exports / sync-all / qa / pptx-spec / pptx-fill / pptx-native
  [SRC:src/pyforge/herald/cli.py:L229-L481].
- **Transport** — one MCP client over the `claude-design` server; one session per
  call [SRC:src/pyforge/herald/transport/mcp_transport.py:L1-L11].
- **Status** — machine-readable JSON array only; no extra prose line
  [SRC:src/pyforge/herald/cli.py:L947-L950].
- **CLI** — sole public contract; `__init__` exports `__version__` only
  [SRC:src/pyforge/herald/__init__.py:L12].

## CLI

```text
herald --version
herald deck seed <slug> [--repo-root PATH] [--support-source-project ID]
herald deck pull <slug> [--repo-root PATH] [--commit] [--target prototype|marp-deck|marp-executive-summary|marp-infographic|standalone]
herald deck status [slug] [--repo-root PATH] [--account]
herald deck watch <slug>... [--repo-root PATH] [--interval SECONDS]
herald deck push <slug> [--repo-root PATH] [--prove]
herald deck publish <slug> [--repo-root PATH] [--dry-run]
herald deck exports <slug> [--repo-root PATH] --json
herald deck sync-all [--slug SLUG] [--repo-root PATH] [--dry-run] [--proof-dir DIR]
herald deck qa <slug> [--repo-root PATH]
herald deck pptx-spec --template PATH -o PATH
herald deck pptx-fill <content_plan> --template PATH -o PATH
herald deck pptx-native <slug> [--repo-root PATH]
herald progress|success|notice|scheduler …
```

Parser `prog` is `herald` [SRC:src/pyforge/herald/cli.py:L207].

<!-- [MANUAL:api-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:api-notes] -->
