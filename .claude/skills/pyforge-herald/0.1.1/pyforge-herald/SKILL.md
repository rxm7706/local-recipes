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
`src/shared/packages/pyforge-herald` @ commit `424ce69fc2` (`source_ref: local`).
Forge tier: **Forge** (SKF `skf-extract-public-api` over ast-grep 0.45.3; T1).
First compiled from `865b95dc951` (Story 29.1); recompiled in place at 0.1.0 on
2026-11-12 (steward Story 29.5, the fixes the EGM audit of 2026-11-05 accepted:
HER-R-F1, HER-R-F17, HER-R-F27, HER-R-F28, with HER-R-F16 and HER-R-F29 carried)
from the scope widened with `errors.py`, `deck_pipeline.py` and
`transport/mcp_transport.py`, the `cli.py` help strings herald Story 50.3 corrected,
the station contract `contract.md` and `bridge-protocol.md` as doc sources, and the
real `herald --help`, the way Story 29.1 and atlas Stories 33.1 and 33.2 did.
Rebuilt as 0.1.1 on 2026-11-18 (steward Story 126.5) with `skf-update-skill` at Forge
tier over ast-grep 0.45.3, a full re-extraction at `424ce69fc2`.
49 exports documented (13 functions, 36 classes; all T1): `main` and `dispatch` in
`cli.py`, the rest in `deck_pipeline.py`, `errors.py` and `transport/mcp_transport.py`.
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

**Seed** (`herald deck seed <slug> [--repo-root PATH] [--support-source-project ID]`)
[SRC:src/pyforge/herald/cli.py:L231-L245]:
seed a deck slug into Claude Design (spec-pyforge-herald:CAP-1, CAP-4). It writes a
**new project into the operator's Claude Design account**: after proving the local
prototype (`npm run extract` and `npm run build` in `presentations/<slug>/`), it
fetches the design-system prompt, creates the project, writes `support.js`, a
server-side copy of `deck-stage.js` and the prototype, then records the project in
the bridge state and the deck README's § *Design project*. It refuses with
`SeedConflictError` (exit 3) when the slug is already seeded
[SRC:src/pyforge/herald/deck_pipeline.py:L158-L174].

**Pull** (`herald deck pull <slug> [--repo-root PATH] [--commit] [--target …]`)
[SRC:src/pyforge/herald/cli.py:L246-L275]: pull a deck's prototype (or, with
`--target`, a Marp source or the standalone bundle) from Claude Design into the repo
(spec-pyforge-herald:CAP-1, CAP-4). It needs a prior seed. An unchanged etag returns
at once and writes nothing; a change **overwrites the tracked file under
`presentations/<slug>/`**, records the new etag and re-derives the deck (extract,
build, `deck-export`). The files stay **uncommitted** unless `--commit`, which
stages and commits `presentations/<slug>/` and the bridge-state file — and never
commits an unchanged pull [SRC:src/pyforge/herald/deck_pipeline.py:L716-L729].

**Status** (`herald deck status [slug] [--repo-root PATH] [--account]`)
[SRC:src/pyforge/herald/cli.py:L276-L301]:
print one JSON array of bridge state for one slug or every known deck
(spec-pyforge-herald:CAP-4) [SRC:src/pyforge/herald/cli.py:L940-L1008]; each row is
`{slug, linked, project_id, sync, last_pull, stale_mirror}`. `sync` is `null` for an
unlinked deck and, for a linked one, `"unchanged"` (every tracked artifact's etag
still matches, or nothing was pulled yet), `"changed"` (at least one etag moved) or
`"conflict"` (a comparison itself failed: the transport raised, or the tracked file
is gone server-side — resolve it before pulling); `stale_mirror` flags a
hand-mirrored Design project [AST:src/pyforge/herald/deck_pipeline.py:L1316-L1338].
`--account` reports every Design project the signed-in account can see, reconciled
against the registry (spec-pyforge-herald:CAP-29), and takes no slug.

**The other deck verbs** [SRC:src/pyforge/herald/cli.py:L302-L481]:
`watch <slug>... [--repo-root PATH] [--interval SECONDS]` polls for Design-side edits
and pulls once settled; `push <slug> [--repo-root PATH] [--prove]` pushes
regenerated derived exports back into Design (spec-pyforge-herald:CAP-4, CAP-34);
`publish <slug> [--repo-root PATH] [--dry-run]` and
`exports <slug> [--repo-root PATH] [--json]` (`--json` is bracketed in `--help` but
required today: without it the verb exits 2) publish and read a deck's
exports in object storage (spec-pyforge-herald:CAP-54, behind
`pyforge.herald.deck_publish`);
`sync-all [--slug SLUG] [--repo-root PATH] [--dry-run] [--proof-dir DIR]` runs
enumerate, pull, refresh, derive, push, prove and publish in order
(spec-pyforge-herald:CAP-36); `qa <slug> [--repo-root PATH]` runs the visual-QA gates
(spec-pyforge-herald:CAP-26..CAP-28); `pptx-spec [--template PATH] [-o PATH]` and
`pptx-fill <content_plan> [--template PATH] -o PATH` parse and fill a
`.pptx`/`.potx` template (spec-pyforge-herald:CAP-41);
`pptx-native <slug> [--repo-root PATH]` exports
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
| `main` | Argparse entry (`herald` console script) [AST:src/pyforge/herald/cli.py:L783] | `argv` |
| `dispatch` | Sole `HeraldError` catch point (AD-6) [AST:src/pyforge/herald/cli.py:L1919] | `operation`, `json_output` |
| `seed` | Seed a slug into Claude Design; refuses an already seeded one [AST:src/pyforge/herald/deck_pipeline.py:L149] | `transport`, `slug`, `repo_root`, `support_source_project_id` |
| `pull_prototype` | Pull the main prototype; needs a prior seed [AST:src/pyforge/herald/deck_pipeline.py:L704] | `transport`, `slug`, `repo_root`, `commit` |
| `pull_marp_source` | Pull one authored Marp source [AST:src/pyforge/herald/deck_pipeline.py:L809] | `slug`, `kind`, `commit` |
| `pull_standalone_bundle` | Pull the standalone infographic bundle [AST:src/pyforge/herald/deck_pipeline.py:L911] | `slug`, `commit` |
| `status` | Bridge state of one or every known deck, read-only [AST:src/pyforge/herald/deck_pipeline.py:L1453] | `slug` optional, `repo_root` |
| `account_status` | Every Design project the account sees, reconciled against the registry [AST:src/pyforge/herald/deck_pipeline.py:L1589] | `transport`, `repo_root` |
| `push_exports` | Push the derived export set back into Design [AST:src/pyforge/herald/deck_pipeline.py:L1922] | `slug`, `prove` |
| `adopt` | Adopt an existing Design project that has no local twin [AST:src/pyforge/herald/deck_pipeline.py:L1175] | `state_key`, `project_id`, `artifacts`, `dest_dir` |
| `select_exporter` | Pick a deck's derive path (`.potx` template fill or `deck-export`) [AST:src/pyforge/herald/deck_pipeline.py:L608] | `slug`, `repo_root` |
| `exit_code_for` | Project a `HeraldError` to its exit code; sole owner of the map [AST:src/pyforge/herald/errors.py:L219] | `error` |
| `resolve_design_credential` | Read the stored `/design-login` credential; `AuthError` when unusable [AST:src/pyforge/herald/transport/mcp_transport.py:L169] | `credentials_path`, `env` |

## Key Exports

Public SKF extract (`skf-extract-public-api`, ast-grep): `main` [AST:src/pyforge/herald/cli.py:L783]
and `dispatch` [AST:src/pyforge/herald/cli.py:L1919] in `cli.py`; the other 47 exports are in
§ *Full API Reference* and § *Full Type Definitions*. Console script:
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
projection) [AST:src/pyforge/herald/errors.py:L219-L232]: `0` success, `--help`,
`--version` · `1` no command given, or any `HeraldError` the map does not name ·
`2` usage (argparse's own exit, `DeckUsageError`, a verb whose flag is off, `deck
exports` without `--json`) · `3` a conflict (`SeedConflictError`,
`PullConflictError`, `ExportConflictError`) · `4` a transport failure
(`TransportError` and every class under it, `AuthError` included). A
`KeyboardInterrupt` returns `130`, outside the closed set. `dispatch` writes one line
to stderr (one JSON object with `--json`) and returns the code
[AST:src/pyforge/herald/cli.py:L1919].

## Key Types

**`TOOL_NAME`** [SRC:src/pyforge/herald/cli.py:L85] — `"herald"`.

**`TOP_LEVEL_COMMANDS`** [SRC:src/pyforge/herald/cli.py:L87] —
`deck`, `progress`, `success`, `notice`, `scheduler`.

**`DeckStatus`** [AST:src/pyforge/herald/deck_pipeline.py:L1316] — one deck's status
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
herald deck exports <slug> [--repo-root PATH] [--json]   # --json: bracketed in --help, required today (exit 2 without it)
herald deck sync-all [--slug SLUG] [--repo-root PATH] [--dry-run] [--proof-dir DIR]
herald deck qa <slug> [--repo-root PATH]
herald deck pptx-spec [--template PATH] [-o PATH]
herald deck pptx-fill <content_plan> [--template PATH] -o PATH
herald deck pptx-native <slug> [--repo-root PATH]
herald progress|success|notice|scheduler …
```

Parser `prog` is `herald` [SRC:src/pyforge/herald/cli.py:L209].

<!-- [MANUAL:api-notes] -->
<!-- Add custom notes here. This section is preserved during skill updates. -->
<!-- [/MANUAL:api-notes] -->

## Full API Reference

The 13 functions, as the source declares them, for reading the code. Other stations
and `src/platform/` do not import them: the CLI is the contract (§ *Usage*).

### `cli.py`

- `main(argv: list[str] | None = None) -> int` — the `herald` console-script entry;
  returns the exit code. [AST:src/pyforge/herald/cli.py:L783]
- `dispatch(operation: Callable[[], None], *, json_output: bool = False) -> int` — runs
  `operation`; on a `HeraldError` writes one line to stderr (one JSON object when
  `json_output`) and returns `exit_code_for`'s code, else `0`.
  [AST:src/pyforge/herald/cli.py:L1919]

### `deck_pipeline.py`

- `seed(transport: DesignTransport, *, slug: str, repo_root: Path, support_source_project_id: str = PILOT_SUPPORT_SOURCE_PROJECT_ID, state_path: Path | None = None, prover: LocalProver | None = None) -> SeedResult`
  — seeds `slug` into Claude Design; `SeedConflictError` when it is already seeded.
  [AST:src/pyforge/herald/deck_pipeline.py:L149]
- `pull_prototype(transport: DesignTransport, *, slug: str, repo_root: Path, commit: bool = False, state_path: Path | None = None, prover: LocalProver | None = None, exporter: DeckExporter | None = None, committer: GitCommitter | None = None, now: Callable[[], datetime] | None = None) -> PullResult`
  — pulls the main prototype; an unchanged etag writes nothing and never commits.
  [AST:src/pyforge/herald/deck_pipeline.py:L704]
- `pull_marp_source(transport: DesignTransport, *, slug: str, repo_root: Path, kind: str, commit: bool = False, state_path: Path | None = None, exporter: DeckExporter | None = None, committer: GitCommitter | None = None, now: Callable[[], datetime] | None = None) -> PullResult`
  — pulls one authored Marp source; no local-prove step.
  [AST:src/pyforge/herald/deck_pipeline.py:L809]
- `pull_standalone_bundle(transport: DesignTransport, *, slug: str, repo_root: Path, commit: bool = False, state_path: Path | None = None, exporter: DeckExporter | None = None, committer: GitCommitter | None = None, now: Callable[[], datetime] | None = None) -> PullResult`
  — pulls the Design-authored standalone infographic bundle; no local-prove step.
  [AST:src/pyforge/herald/deck_pipeline.py:L911]
- `adopt(transport: DesignTransport, *, state_key: str, project_id: str, artifacts: Sequence[tuple[str, str]], dest_dir: Path, repo_root: Path, project_name: str | None = None, project_url: str | None = None, state_path: Path | None = None, now: Callable[[], datetime] | None = None) -> AdoptResult`
  — adopts an existing Design project that has no local twin; idempotent by etag;
  `HeraldError` on empty `artifacts` or a `state_key` already adopted against another
  project. [AST:src/pyforge/herald/deck_pipeline.py:L1175]
- `status(transport: DesignTransport, *, slug: str | None = None, repo_root: Path, state_path: Path | None = None) -> list[DeckStatus]`
  — read-only; an unknown or unlinked `slug` returns one unlinked row, never an error.
  [AST:src/pyforge/herald/deck_pipeline.py:L1453]
- `account_status(transport: DesignTransport, *, repo_root: Path) -> list[AccountProjectStatus]`
  — read-only; calls only `transport.list_projects`.
  [AST:src/pyforge/herald/deck_pipeline.py:L1589]
- `push_exports(transport: DesignTransport, *, slug: str, repo_root: Path, export_dir: Path | None = None, state_path: Path | None = None, prove: bool = False, now: Callable[[], datetime] | None = None) -> ExportPushResult`
  — skips a file whose hash matches the last push; after the batch raises
  `ExportConflictError` for per-file conflicts, or `ReadBackMismatchError` for a
  failed `prove` read-back. [AST:src/pyforge/herald/deck_pipeline.py:L1922]
- `select_exporter(slug: str, repo_root: Path) -> DeckExporter` — `PptxTemplateExporter`
  when the deck README declares a `.potx` template, else `PixiDeckExporter`.
  [AST:src/pyforge/herald/deck_pipeline.py:L608]

### `errors.py`

- `exit_code_for(error: HeraldError) -> int` — `2` for `DeckUsageError`, `3` for the
  three conflict types, `4` for `TransportError` and everything under it, `1` for any
  other `HeraldError`. [AST:src/pyforge/herald/errors.py:L219]

### `transport/mcp_transport.py`

- `resolve_design_credential(*, credentials_path: Path | None = None, env: Mapping[str, str] | None = None) -> DesignCredential`
  — reads `credentials_path`, else the file `HERALD_DESIGN_CREDENTIALS` names, else
  `~/.claude/.credentials.json`; a missing, unreadable or expired credential is an
  `AuthError`; never refreshes or writes one.
  [AST:src/pyforge/herald/transport/mcp_transport.py:L169]

## Full Type Definitions

The 36 classes. A dataclass line lists its fields; a Protocol or class line its one
method or what it runs.

### `deck_pipeline.py`

- `@dataclass(frozen=True) class SeedResult` — what `seed` returns: `project: ProjectRef`,
  `persona: str`, `prototype_filename: str`. [AST:src/pyforge/herald/deck_pipeline.py:L88]
- `@runtime_checkable class LocalProver(Protocol)` — the local-prove seam:
  `prove(self, deck_dir: Path) -> None`. [AST:src/pyforge/herald/deck_pipeline.py:L99]
- `class NpmLocalProver` — the real `LocalProver`: `npm run extract` then
  `npm run build` in `deck_dir`. [AST:src/pyforge/herald/deck_pipeline.py:L112]
- `@dataclass(frozen=True) class PullResult` — what a `pull_*` function returns:
  `slug: str`, `artifact: str`, `local_path: Path | None`, `unchanged: bool`,
  `etag: str | None`, `committed: bool = False`.
  [AST:src/pyforge/herald/deck_pipeline.py:L341]
- `@runtime_checkable class DeckExporter(Protocol)` — the `deck-export` seam:
  `export(self, *, slug: str, repo_root: Path) -> None`.
  [AST:src/pyforge/herald/deck_pipeline.py:L463]
- `class PixiDeckExporter` — the real `DeckExporter`:
  `pixi run -e pyforge-guild deck-export <slug>` in `repo_root`.
  [AST:src/pyforge/herald/deck_pipeline.py:L475]
- `class PptxTemplateExporter` — fills the deck's `.potx` template for the deck PPTX
  target only; the other targets still derive through `deck-export`.
  [AST:src/pyforge/herald/deck_pipeline.py:L561]
- `@runtime_checkable class GitCommitter(Protocol)` — the git-commit seam:
  `commit(self, *, repo_root: Path, paths: list[Path], message: str) -> None`.
  [AST:src/pyforge/herald/deck_pipeline.py:L640]
- `class SubprocessGitCommitter` — the real `GitCommitter`: `git add -- <paths>` then
  `git commit -m <message> -- <paths>` in `repo_root`.
  [AST:src/pyforge/herald/deck_pipeline.py:L653]
- `@dataclass(frozen=True) class AdoptedArtifact` — one artifact `adopt` considered:
  `remote_path: str`, `local_path: Path`, `unchanged: bool`.
  [AST:src/pyforge/herald/deck_pipeline.py:L1022]
- `@dataclass(frozen=True) class AdoptResult` — what `adopt` returns: `state_key: str`,
  `bootstrapped: bool`, `registered: bool`, `artifacts: tuple[AdoptedArtifact, ...]`.
  [AST:src/pyforge/herald/deck_pipeline.py:L1035]
- `@dataclass(frozen=True) class DeckStatus` — one deck's status row: `slug: str`,
  `linked: bool`, `project_id: str | None`, `sync: str | None`, `last_pull: str | None`,
  `stale_mirror: bool`. [AST:src/pyforge/herald/deck_pipeline.py:L1316]
- `@dataclass(frozen=True) class AccountProjectStatus` — one Design project's
  reconciliation row: `project_id: str`, `name: str`, `url: str`, `status: str`
  (`"linked"`, `"untwinned"`, `"mirrored"` or `"excluded"`), `slug: str | None = None`,
  `reason: str | None = None`. [AST:src/pyforge/herald/deck_pipeline.py:L1527]
- `@dataclass(frozen=True) class ExportPushResult` — what `push_exports` returns:
  `slug: str`, `pushed: tuple[str, ...]`, `skipped: tuple[str, ...]`,
  `proven: tuple[str, ...] = ()`. [AST:src/pyforge/herald/deck_pipeline.py:L1692]

### `errors.py`

Exit codes follow `_EXIT_BY_ERROR` [SRC:src/pyforge/herald/errors.py:L202-L208]: `1`
unless a line says otherwise.

- `class HeraldError(PyforgeError)` — root of every error herald raises deliberately.
  [AST:src/pyforge/herald/errors.py:L26]
- `class TransportError(HeraldError)` — a failure reaching or talking to the
  `claude-design` surface; exit `4`, with every class under it.
  [AST:src/pyforge/herald/errors.py:L35]
- `class AuthError(TransportError)` — no usable stored `/design-login` credential
  (absent or expired); the message names `/design-login`.
  [AST:src/pyforge/herald/errors.py:L39]
- `class TransportUnreachableError(TransportError)` — no session could be established,
  so no tool call was answered. [AST:src/pyforge/herald/errors.py:L47]
- `class TransportCallError(TransportError)` — the server answered, but the tool call
  failed; carries the tool name and the server's message.
  [AST:src/pyforge/herald/errors.py:L56]
- `class UnconditionalWriteError(TransportError)` — a write with no etag precondition,
  refused before any network call. [AST:src/pyforge/herald/errors.py:L64]
- `class SeedConflictError(HeraldError)` — `deck seed` found Design-side edits it would
  clobber; exit `3`. [AST:src/pyforge/herald/errors.py:L73]
- `class PullConflictError(HeraldError)` — `deck pull` found a conflict it will not
  silently resolve; exit `3`. [AST:src/pyforge/herald/errors.py:L82]
- `class ExportConflictError(HeraldError)` — the export push-back found a conflict it
  will not silently resolve; exit `3`. [AST:src/pyforge/herald/errors.py:L90]
- `class ReadBackMismatchError(HeraldError)` — `deck push --prove` read a pushed file
  back and it did not match the bytes sent. [AST:src/pyforge/herald/errors.py:L98]
- `class OperatorAuthorizationError(HeraldError)` — a write that needs the operator
  role (`success publish`; `notice author`, `publish`, `close` and `archive`;
  `progress --update`) ran without a verified `operator` role, or with no auth
  context. [AST:src/pyforge/herald/errors.py:L112]
  [SRC:src/pyforge/herald/cli.py:L1378] [SRC:src/pyforge/herald/cli.py:L1558]
  [SRC:src/pyforge/herald/cli.py:L1707-L1819]
- `class InvalidDateRangeError(HeraldError)` — `--date-range` did not parse as
  `<start>..<end>`. [AST:src/pyforge/herald/errors.py:L125]
- `class EvidenceLinkError(HeraldError)` — a publish-time evidence link is unreachable
  or answered outside 200-299. [AST:src/pyforge/herald/errors.py:L135]
- `class ClaimNotFoundError(HeraldError)` — a `success` subcommand named a claim id the
  claims store does not hold. [AST:src/pyforge/herald/errors.py:L145]
- `class ClaimStateError(HeraldError)` — `success publish` on a claim that is not
  `draft`. [AST:src/pyforge/herald/errors.py:L153]
- `class DeckPublishError(HeraldError)` — `deck publish` / `deck exports` could not
  reach the store. [AST:src/pyforge/herald/errors.py:L159]
- `class DeckUsageError(HeraldError)` — a `deck publish` / `deck exports` usage problem,
  such as an unknown slug; exit `2`. [AST:src/pyforge/herald/errors.py:L163]
- `class PptxTemplateError(HeraldError)` — the `--template` path of `pptx-spec` or
  `pptx-fill` does not exist, or does not open as a `.pptx`/`.potx`.
  [AST:src/pyforge/herald/errors.py:L167]
- `class InvalidContentPlanError(HeraldError)` — `pptx-fill`'s `content_plan.json` is
  malformed, names a layout or placeholder idx the template lacks, gives a placeholder
  a value that is neither a string nor a list of strings, or carries an invalid
  `shapes` entry (not a JSON array, an entry that is not an object, unknown `type`,
  missing or malformed field, non-positive geometry); raised before any file is
  written. [AST:src/pyforge/herald/errors.py:L175]
- `class PaginationStalledError(HeraldError)` — a windowed read's next window did not
  advance; names the file and the stalled line.
  [AST:src/pyforge/herald/errors.py:L190]

### `transport/mcp_transport.py`

- `@dataclass(frozen=True) class DesignCredential` — a stored `/design-login`
  credential: `access_token: str` (kept out of `repr`), `expires_at_ms: int | None = None`
  (epoch milliseconds); `is_expired(self, *, now_ms: float | None = None) -> bool`.
  [AST:src/pyforge/herald/transport/mcp_transport.py:L147]
- `class McpTransport` — `DesignTransport` over the remote `claude-design` MCP server;
  methods `get_design_prompt`, `create_project`, `finalize_plan`, `create_support_js`,
  `copy_files`, `write_files`, `read_file`, `render_preview`, `list_files`,
  `list_projects`, `fetch_rendered_bytes`.
  [AST:src/pyforge/herald/transport/mcp_transport.py:L294]
