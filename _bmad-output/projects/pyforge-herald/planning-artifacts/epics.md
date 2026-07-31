---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - planning-artifacts/prds/prd-pyforge-herald-2026-07-25/prd.md
  - planning-artifacts/architecture/architecture-pyforge-herald-2026-07-25/ARCHITECTURE-SPINE.md
  - planning-artifacts/specs/spec-design-code-bridge/SPEC.md
  - planning-artifacts/specs/spec-design-code-bridge/bridge-protocol.md
  - planning-artifacts/briefs/brief-pyforge-herald-2026-07-25/brief.md
---

# pyforge-herald - Epic Breakdown

## Overview

Complete epic and story breakdown for **pyforge-herald** — a deterministic CLI (`herald`)
packaging the proven Design↔Code Bridge (`SPEC-design-code-bridge`, CAP-1..5) as five
repeatable commands: `herald deck seed/pull/status/watch` + export push-back. Decomposed from
the finalized PRD (FR-01–FR-26 + NFR-01–NFR-09) and the finalized architecture spine (AD-1–AD-8,
hexagonal ports-and-adapters, pixi workspace-member packaging). **No UX design contract** — this
is a non-interactive/CLI-only surface with no human-UI beyond terminal output, matching the
`pyforge-warden` precedent's "N/A — non-interactive CLI" UX posture. `updates compile`,
`broadcast`, `deck generate`, and `bmad init` are **explicitly out of scope** — see § Deferred /
Roadmap at the end of this document; no epic or story below touches them.

## Requirements Inventory

### Functional Requirements

**A. Transport & Foundation (cross-cutting infrastructure the five CAPs share)**
- FR-21: primary transport is a pure MCP client on the `claude-design` remote server, reusing
  the stored `/design-login` OAuth credential, validated by a time-boxed spike as the first V1
  story.
- FR-22: fallback transport is a headless Claude Code / Agent SDK wrapper with a tool
  allowlist, reusing the same stored login.
- FR-23: every bridge operation is deterministic — no LLM in the decision path, regardless of
  transport.
- FR-24: every cross-surface read/write carries `if_none_match`/`if_match`; unconditional
  writes are not possible through the CLI.
- FR-25: Herald ships as a pixi-workspace-member package (`pyforge-herald` / `pyforge.herald` /
  `herald`).
- FR-26: `herald deck --help` documents every subcommand without requiring `bridge-protocol.md`.

**B. CAP-1 — Seed (repo → Design)**
- FR-01: `herald deck seed <slug>` yields a Modernist-bound Design project carrying the runtime
  + a contract-compliant starter prototype.
- FR-02: seed proves the prototype locally (`extract` + `build`) before any Design write; a
  failing prove blocks the seed.
- FR-03: seed refuses structurally over existing Design-side edits, writing nothing.
- FR-04: seed prints only the `claude.ai/design/...` URL and registers the project in the deck
  README § *Design project*.

**C. CAP-2 — Pull (Design → repo)**
- FR-05: unchanged etag → "unchanged" report, exit 0, zero bytes transferred.
- FR-06: changed etag → decode, write `project/<Deck>.dc.html`, re-run
  `extract` → `build` → `deck-export`.
- FR-07: pulls Design-authored Marp sources into `src/marp/` via the same etag/decode loop, no
  extract/build.
- FR-08: pulls a Design-authored standalone bundle, superseding the marp `--html` fallback.
- FR-09: commits are the operator's by default; `--commit` opts into an automatic commit.
- FR-10: the returned etag is stored after every successful pull.

**D. CAP-3 — Status**
- FR-11: `herald deck status [<slug>]` reports linked/unlinked, unchanged/changed/conflict, and
  last-pull timestamp, machine-readable.
- FR-12: detects a stale hand-mirror (a Design project holding a repo app-tree copy), verified
  against a planted fixture.
- FR-13: `status` never writes to either surface.

**E. CAP-4 — Watch**
- FR-14: polls each watched deck's etag on a 60 s default interval (30 s hard floor, jittered).
- FR-15: defers a pull until the etag is stable for one full poll interval.
- FR-16: idle backoff doubles after ~10 unchanged polls, capped at 10 min, reset on change.
- FR-17: halts (never retries) on an auth error, reporting the failure structurally.

**F. CAP-5 — Export push-back**
- FR-18: pushes the regenerated derived set into Design via `finalize_plan` + `write_files`,
  per-file etags.
- FR-19: an unchanged file (hash matches last-pushed etag record) is skipped.
- FR-20: a conflict on any export file is refused structurally, no partial clobber of the rest
  of the push set.

### NonFunctional Requirements

- NFR-01 (Determinism): no bridge operation may invoke an LLM in its control-flow decision
  path, under either transport.
- NFR-02 (Structured failure): every conflict surfaces structured and machine-parseable, never
  a silent no-op or partial write.
- NFR-03 (Unreachable-surface failure): a clear structured failure at every command; `watch`
  halts rather than retries on auth errors.
- NFR-04 (URL hygiene): output/files carry only `claude.ai/design/...` URLs, never a tokenized
  `serve_url`.
- NFR-05 (Credential reuse): Herald reuses the existing stored `/design-login` credential; no
  new credential storage mechanism.
- NFR-06 (Directional integrity): inbound = authored sources only; outbound = seeds + derived
  exports only; no code path constructs a mirrored app tree either direction.
- NFR-07 (Portability): every FR's acceptance is exit-code + file-artifact based, framework
  agnostic.
- NFR-08 (Zero-byte unchanged): an unchanged pull/status/watch-poll transfers zero file bodies.
- NFR-09 (Poll floor): default 60 s poll; 30 s hard floor enforced by the CLI.

### Additional Requirements (from Architecture)

*From `ARCHITECTURE-SPINE.md` — these shape epic/story design. **No starter template applies**
(this is a from-scratch package, unlike a scaffolded-template greenfield project); the
concrete scaffolding precedent is the sibling `src/shared/packages/pyforge-warden/` and
`src/shared/packages/pyforge-atlas/` packages, both already shipped in this repo.*

- **AD-1** (package shape): `src/shared/packages/pyforge-herald/` — own `[package]` table,
  `pixi-build-python` backend, no `[workspace]` table; root `pixi.toml` wires it into a
  dedicated `no-default-feature` `pyforge-herald` environment. Epic 1 Story 1 is the
  scaffolding story, mirroring `pyforge-warden`'s own bootstrap.
- **AD-2** (CLI framework): argparse, matching `pyforge.warden.cli:main` — `[project.scripts]
  herald = "pyforge.herald.cli:main"`.
- **AD-3** (transport-agnostic core): `bridge-core` depends only on a `DesignTransport`
  protocol; two adapters (`McpTransport` primary, `AgentSdkTransport` fallback) implement it.
- **AD-4** (determinism boundary): the harness inside `AgentSdkTransport` is plumbing only;
  `bridge-core`'s branch logic never depends on model inference under either adapter.
- **AD-5** (state persistence): `.herald/bridge-state.json` is the operational etag/state
  source of truth; the README § *Design project* stays the human-readable registry, read only
  as a bootstrap fallback.
- **AD-6** (error model): a `HeraldError` hierarchy caught once at the CLI boundary, mapped to
  fixed exit codes; stdout carries only machine-readable success output.
- **AD-7** (deck-pipeline adapter): `deck_pipeline.py` wraps `npm run extract`/`build` and
  `pixi run -e local-recipes deck-export <slug>` as opaque subprocess calls — never
  reimplemented.
- **AD-8** (registry ownership): `registry.py` is the sole module that reads/writes the deck
  README's § *Design project* block.

### UX Design Requirements

**N/A** — non-interactive CLI, no human-UI surface beyond terminal output. The
human-facing affordances (`--help`, structured error messages, `claude.ai/design` links) are
owned as FR-04/FR-26 + NFR-02/03/04, not as UX artifacts — matching `pyforge-warden`'s
established posture for this project family.

### FR Coverage Map

FR-21, FR-22, FR-23, FR-24, FR-25: **Epic 1** (foundation, spans the epic's stories 1.1–1.5)
FR-01, FR-02, FR-03, FR-04, FR-26: **Epic 1** (story 1.6, the epic's payoff)
FR-05, FR-06, FR-07, FR-08, FR-09, FR-10: **Epic 2**
FR-11, FR-12, FR-13: **Epic 3**
FR-14, FR-15, FR-16, FR-17: **Epic 4**
FR-18, FR-19, FR-20: **Epic 5**

All 26 FRs covered. NFR-01–NFR-09 are cross-cutting acceptance gates applied wherever their
concern is exercised (cited per-story below), not a separate epic — same convention
`pyforge-warden`'s epics.md established for its own cross-cutting gates (C0, NFR-S\*, NFR-R\*).

## Epic List

*Vertical-slice epics, one per CAP, in the spec's own dependency order. Epic 1 carries the
shared foundation (transport, state, errors, registry, package scaffold) **as part of
delivering CAP-1's real user value** — never a standalone "build the spine" epic — per the
`pyforge-warden` precedent (its own Epic 1 folds spine-building into the first vertical slice).
Epics 2–5 each build on Epic 1's foundation but are independently complete for their own
domain: Epic 3 does not require Epic 4; Epic 4 does not require Epic 5; and so on.*

### Epic 1: Seed a deck into Claude Design
An operator can turn a locally-authored, locally-proven prototype into a live, Modernist-bound
Design project with one command — while this epic also stands up the transport, state, error,
and registry foundation every later epic depends on.
**FRs covered:** FR-01, FR-02, FR-03, FR-04, FR-21, FR-22, FR-23, FR-24, FR-25, FR-26

### Epic 2: Pull Design edits back into the repo
An operator can pull whatever a human changed in Claude Design — the prototype, Marp sources,
or a Design-authored standalone bundle — straight into a green, re-derived repo state, or learn
cheaply that nothing changed.
**FRs covered:** FR-05, FR-06, FR-07, FR-08, FR-09, FR-10

### Epic 3: See the bridge's state at a glance
An operator can ask, for any deck or all of them, whether it's linked, in sync, conflicted, or
sitting on a stale hand-mirror — without touching either surface.
**FRs covered:** FR-11, FR-12, FR-13

### Epic 4: Stay in sync automatically
An operator can leave Herald watching a set of decks and trust that a Design-side edit lands in
the repo on its own, without babysitting a pull loop or burning cycles on idle decks.
**FRs covered:** FR-14, FR-15, FR-16, FR-17

### Epic 5: Keep Design current with the shipped exports
An operator (via the pull-then-export-then-push cycle) can trust that after `deck-export`
regenerates a deck's derived artifacts, Design ends up holding the same complete set —
without ever risking a clobber on either side.
**FRs covered:** FR-18, FR-19, FR-20

---

## Epic 1: Seed a deck into Claude Design

An operator can turn a locally-authored, locally-proven prototype into a live, Modernist-bound
Design project with one command. This epic also stands up the foundation (package scaffold,
transport port + both adapters, bridge-core with its state/error backbone, and the registry
module) that Epics 2–5 build on — delivered as part of shipping CAP-1's real value, not as a
separate infrastructure epic.

### Story 1.1: Package scaffold for `pyforge-herald`

As an operator,
I want a working `herald` CLI package wired into this repo's pixi workspace,
So that Herald exists as a real, installable command before any bridge logic is built.

**Acceptance Criteria:**

**Given** the repo has no `pyforge-herald` package yet
**When** the scaffold is created at `src/shared/packages/pyforge-herald/` (its own `[package]`
table, `pixi-build-python` backend, no `[workspace]` table, hatchling `pyproject.toml` with
`[project.scripts] herald = "pyforge.herald.cli:main"`) and the root `pixi.toml` gains
`[feature.pyforge-herald.dependencies] pyforge-herald = { path = "src/shared/packages/pyforge-herald" }`
plus a dedicated `pyforge-herald = { features = ["pyforge-herald"], no-default-feature = true }`
environment
**Then** `pixi run -e pyforge-herald herald deck --help` runs and exits 0, printing the
`deck` subcommand group (empty of real logic — this story only wires the entrypoint) (FR-25)
**And** the package installs cleanly via `pixi run -e pyforge-herald pyforge-herald-build`
(mirroring the `pyforge-warden-build`/`pyforge-atlas-build` task shape: conda pkg + wheel/sdist)
**And** `herald deck --help`'s output is generated by argparse from the registered
subcommands — no hand-written help text to keep in sync (FR-26, satisfied incrementally as
later stories add subcommands)

### Story 1.2: Transport port + primary MCP-client adapter (the transport spike)

As an operator,
I want Herald's primary transport to reach the `claude-design` MCP server outside a Claude Code
session,
So that the bridge doesn't require a live interactive session just to run a command.

**Acceptance Criteria:**

**Given** the `DesignTransport` protocol is defined (`get_design_prompt`, `create_project`,
`finalize_plan`, `create_support_js`, `copy_files`, `write_files`, `read_file`,
`render_preview` — the exact `bridge-protocol.md` tool surface) in `transport/base.py`
**When** `McpTransport` is implemented against the `mcp` >=1.28.1 official SDK, reusing the
stored `/design-login` OAuth credential (NFR-05), and exercised against a real
`claude-design` remote MCP call (e.g. `get_design_prompt` for the Modernist design system)
**Then** the call succeeds from a plain, non-interactive Python process — not inside a live
Claude Code session — proving the primary path (FR-21)
**And** if the spike instead demonstrates the primary path cannot reach the server outside a
session, that finding is recorded as a blocking spike result and Story 1.3's fallback becomes
the shipped default for V1 (spike-first per the PRD's risk mitigation; this AC accepts either
verified outcome, not just success)
**And** `McpTransport` returns only sanitized `claude.ai/design/...` URLs to callers — any raw
`serve_url` in a tool response is stripped before it crosses the adapter boundary (NFR-04)

### Story 1.3: Fallback transport adapter

As an operator,
I want a working fallback transport when the primary MCP client path is unavailable,
So that the bridge still functions using the bmad-loop-proven headless substrate.

**Acceptance Criteria:**

**Given** `DesignTransport` from Story 1.2
**When** `AgentSdkTransport` is implemented as a headless Claude Code / Agent SDK wrapper with
a tool allowlist limited to the bridge's tool surface, reusing the same stored `/design-login`
credential (FR-22, NFR-05)
**Then** it satisfies the identical `DesignTransport` protocol — a caller can swap
`McpTransport` for `AgentSdkTransport` with zero code changes outside the transport-selection
point (AD-3)
**And** any harness process it runs internally exposes only the fixed deterministic tool calls
to `bridge-core` — no branch of `bridge-core`'s logic differs based on which adapter is active
(NFR-01, AD-4)
**And** it also strips raw `serve_url`s at the adapter boundary (NFR-04)

**And** — **HARD CONSTRAINT, added 2026-07-31 after two silent crashes** — the nested agent
process is **never actually spawned during development or in any test**. `AgentSdkTransport`
must take its process-launch seam as an injected dependency (a `ProcessRunner`-shaped callable
or equivalent), so every test drives it with a **stub**, and no test, fixture or exploratory
command in this story invokes a real `claude` binary.

> **Why this constraint exists.** This story's subject IS a nested Claude Code invocation, and
> it is being implemented BY a Claude Code session. Both prior dev attempts (run
> `20260730-192235-062b`, 2026-07-30) died mid-thinking with **no error text**, logs ending on
> a spinner frame, 36,261 weighted tokens total — and OOM, session timeout and environment
> fault were each ruled out by direct check. Attempt 2's log shows the session shelling out to
> a real `claude -p` that was still `Running…` at **6m22s under a `timeout 90`** which never
> fired. A nested agent invocation from inside an agent session is the one thing this story
> asks for and the one thing that reliably kills the session doing the asking.
>
> The transport is fully specifiable without ever launching one: the protocol conformance, the
> tool allowlist, the determinism boundary and the `serve_url` stripping are all assertions
> about what the adapter SENDS and RETURNS, not about a live subprocess. Injecting the launch
> seam is also the AD-4-shaped design — the impure edge belongs behind a port — so this makes
> the story both survivable and better-factored.
>
> This narrows the story's surface, which AD-27 permits a spec to do. Live verification against
> a real nested agent is deferred to an operator-run integration check, outside the loop.

### Story 1.4: Bridge-core skeleton — state, errors, determinism boundary

As an operator,
I want every bridge command to fail structurally and never silently, and to never depend on a
live model call to decide what happens,
So that I can trust the bridge's behavior is predictable and debuggable.

**Acceptance Criteria:**

**Given** `state.py` (reads/writes `.herald/bridge-state.json`, keyed by slug: linked project
id, per-artifact last-seen etag, last-pull timestamp — AD-5) and `errors.py` (the `HeraldError`
hierarchy: `SeedConflictError`, `PullConflictError`, `ExportConflictError`,
`TransportUnreachableError`, `AuthError` — AD-6)
**When** `bridge-core` is exercised with a transport double that raises each error type in turn
**Then** each error is caught exactly once at the CLI boundary and mapped to a fixed,
documented exit code with a structured stderr message — never a silent no-op (NFR-02)
**And** a static/code-level check (or an explicit test asserting no `bridge-core` module
imports an LLM/inference client) proves the control-flow decision path contains zero calls
into either transport adapter's harness internals — only the fixed protocol methods (NFR-01,
FR-23)
**And** `state.py`'s read/write round-trips a `DeckState` record without data loss, verified
by a write-then-read test

### Story 1.5: Registry module — README § Design project

As an operator,
I want the deck README's Design-project registry kept in one canonical format,
So that a human reading any deck's README always finds the same link/id/name shape Herald
itself relies on.

**Acceptance Criteria:**

**Given** `registry.py` (AD-8) as the sole owner of a deck README's § *Design project* block
**When** `registry.register(slug, project_name, project_id, file_url)` is called against a
README with no existing § *Design project* section
**Then** the section is appended in the exact form `bridge-protocol.md`'s Conventions specify
(project name, id, file URL)
**And** calling `registry.read(slug)` against that README returns the same fields back,
round-tripping cleanly
**And** calling `register` again for the same slug updates the existing block in place rather
than duplicating it

### Story 1.6: `herald deck seed <slug>`

As an operator,
I want to run one command that turns my locally-authored, locally-proven prototype into a live
Design project,
So that I never have to hand-run the `bridge-protocol.md` tool sequence myself.

**Acceptance Criteria:**

**Given** a locally-authored `presentations/<slug>/project/<Deck>.dc.html` and a clean bridge
state for `<slug>` (no existing Design project linked)
**When** `herald deck seed <slug>` runs
**Then** it first proves the prototype locally via `deck_pipeline` (`npm run extract` yields
the expected slide count with no lost sections; `npm run build` succeeds) — a failing prove
aborts before any Design write (FR-02)
**And**, on a successful prove, it gates on `get_design_prompt`, then
`create_project`/`finalize_plan`/`create_support_js`/`copy_files`/`write_files` in the exact
`bridge-protocol.md` seed sequence, bound to the Modernist design system id
`fbc1d6c8-b35f-4df6-9044-a64d2675427b` (FR-01)
**And** it prints only the resulting `claude.ai/design/...` URL, registers the project via
`registry.register` (Story 1.5), and initializes `.herald/bridge-state.json` for the slug
(Story 1.4) (FR-04)
**And**, when Design-side edits already exist for `<slug>` (simulated by a non-`"0"` etag on a
prior write), `herald deck seed <slug>` raises `SeedConflictError` naming what it detected and
writes nothing to either surface — verified by a subsequent `state.py` read showing no state
change (FR-03, NFR-02)
**And** it never constructs or transfers anything beyond the runtime + prototype — no app-tree
mirroring (NFR-06)

---

## Epic 2: Pull Design edits back into the repo

An operator can pull whatever a human changed in Claude Design — the prototype, Marp sources,
or a Design-authored standalone bundle — straight into a green, re-derived repo state, or learn
cheaply that nothing changed. Builds on Epic 1's transport, state, and bridge-core.

### Story 2.1: `herald deck pull <slug>` — prototype pull with etag short-circuit

As an operator,
I want to pull a Design-side prototype edit into the repo with one command, and pay nothing
when there's no edit,
So that I can ship whatever a human changed without a manual download.

**Acceptance Criteria:**

**Given** a deck seeded via Story 1.6, with the last-seen prototype etag stored in
`.herald/bridge-state.json`
**When** `herald deck pull <slug>` runs and the Design-side etag is unchanged
**Then** it prints "unchanged", exits 0, and transfers zero bytes of file body — verified by
asserting the transport's `read_file` call was made `if_none_match`-guarded and the response
was `{unchanged: true}` (FR-05, NFR-08)
**When** instead the etag has changed
**Then** it decodes the entity-escaped body (`&amp; &lt; &gt;` → `& < >`), writes
`presentations/<slug>/project/<Deck>.dc.html`, and runs
`extract` → `build` → `deck-export` in sequence via `deck_pipeline`, surfacing which stage
failed if any does (FR-06, NFR-02)
**And** on success, the new etag is stored in `.herald/bridge-state.json` before the command
exits (FR-10)

### Story 2.2: `--commit` opt-in

As an operator,
I want to optionally have Herald commit a pull's result automatically,
So that routine pulls don't require a manual commit step when I trust the result.

**Acceptance Criteria:**

**Given** Story 2.1's pull logic
**When** `herald deck pull <slug> --commit` runs and the pull changed files
**Then** Herald stages and commits exactly the files the pull + re-derive touched, with a
terse, non-interactive commit subject
**When** `herald deck pull <slug>` runs without `--commit`
**Then** no commit is made — the operator's working tree carries the changes, uncommitted
(FR-09)

### Story 2.3: Marp-source pull

As an operator,
I want Design-authored Marp sources pulled into the repo the same way the prototype is,
So that exec-summary and infographic sources stay in sync with what was authored in Design.

**Acceptance Criteria:**

**Given** a Design project holding Marp sources (deck, executive summary, infographic — per
the warden pilot evidence)
**When** `herald deck pull <slug>` runs
**Then** each Marp source is pulled via the same etag/decode loop as the prototype, landing at
`presentations/<slug>/src/marp/<slug>-{deck,executive-summary,infographic}-<date>.md` (FR-07)
**And** no `extract`/`build` step runs for Marp sources — `deck-export` regenerates the
derived set instead, per `bridge-protocol.md`'s authored-source-pull section
**And** an unchanged Marp source (matching etag) is skipped individually — a changed prototype
and an unchanged Marp source in the same pull invocation still short-circuit the Marp side

### Story 2.4: Standalone bundle pull

As an operator,
I want a Design-authored standalone infographic bundle pulled and preferred over a marp-rendered
fallback,
So that the richer, hand-designed poster ships instead of a plainer regenerated one.

**Acceptance Criteria:**

**Given** a Design project holding a standalone bundle (e.g. an "Infographic standalone" page)
**When** `herald deck pull <slug>` runs and the bundle exists in Design
**Then** it is pulled to its export path (`src/marp/<slug>-infographic-standalone-<date>.html`),
superseding any `marp --html` render for that artifact (FR-08)
**When** no Design-authored bundle exists for the slug
**Then** the pull leaves the existing marp-rendered fallback untouched — Herald does not force
a regeneration it has no bundle to justify

---

## Epic 3: See the bridge's state at a glance

An operator can ask, for any deck or all of them, whether it's linked, in sync, conflicted, or
sitting on a stale hand-mirror — without touching either surface. Builds on Epic 1's state file
and Epic 2's per-artifact etag tracking, but is independently complete: an operator gets full
status value without ever running `watch` or export push-back.

### Story 3.1: `herald deck status [<slug>]`

As an operator,
I want to see every watched or seeded deck's bridge state in one machine-readable report,
So that I know what's linked, in sync, or conflicted without manually comparing etags.

**Acceptance Criteria:**

**Given** `.herald/bridge-state.json` holding state for one or more decks (some seeded, some
not)
**When** `herald deck status` runs with no slug argument
**Then** it reports, per known deck, linked/unlinked, unchanged/changed/conflict (via a fresh
etag comparison against Design), and the last-pull timestamp, in a machine-readable format
(FR-11)
**When** `herald deck status <slug>` runs with a specific slug
**Then** it reports only that deck's state, in the same shape
**And** across both invocations, no file is written on either surface — verified by asserting
zero calls to any transport `write_files`/`create_project`/`finalize_plan` method and zero
writes to `.herald/bridge-state.json` (FR-13, NFR-08)

### Story 3.2: Stale hand-mirror detection

As an operator,
I want Herald to flag a Design project that's secretly a hand-mirrored repo copy,
So that I can identify and eventually retire the pattern the bridge was built to replace.

**Acceptance Criteria:**

**Given** a planted fixture Design project matching the "Local recipes repository connection"
pattern (a project holding many files mirroring a repo app-tree structure, rather than a single
prototype + a few authored sources)
**When** `herald deck status` runs and encounters that project
**Then** it flags it distinctly from the normal linked/unlinked/changed states — e.g. a
`stale_mirror: true` field or equivalent — so it stands out in the report (FR-12)
**And** a normal, correctly-shaped bridge project (single prototype + authored sources) is
never flagged as a stale mirror — the heuristic has a verified negative case, not just the
positive fixture

---

## Epic 4: Stay in sync automatically

An operator can leave Herald watching a set of decks and trust that a Design-side edit lands in
the repo on its own. Builds on Epic 2's pull logic (watch is a scheduled caller of `pull`), but
is independently complete: an operator gets continuous sync without ever using export
push-back.

### Story 4.1: Poll loop with quiescence debounce

As an operator,
I want Herald to poll for Design-side changes and pull only once an edit has settled,
So that I don't get a pull mid-edit on a half-saved prototype.

**Acceptance Criteria:**

**Given** one or more decks passed to `herald deck watch`
**When** the watch loop runs with the default 60 s poll interval
**Then** each poll is an etag-only `read_file` call per watched deck — no body transferred
unless a pull is triggered (FR-14, NFR-08)
**And** a detected etag change is not pulled immediately — it is pulled only after the etag has
remained stable across one full subsequent poll interval (FR-15)
**And** consecutive unchanged polls across the whole loop perform zero writes on either surface
— verified over N consecutive simulated unchanged polls
**And** a caller requesting a poll interval below 30 s has it clamped to the 30 s hard floor
(NFR-09)

### Story 4.2: Idle backoff

As an operator,
I want the watch loop to poll less often when nothing is changing,
So that long-idle decks don't burn API calls or rate-limit budget for no reason.

**Acceptance Criteria:**

**Given** Story 4.1's poll loop
**When** a watched deck accumulates ~10 consecutive unchanged polls
**Then** its poll interval doubles, up to a 10-minute cap (FR-16)
**When** a change is subsequently detected for that deck
**Then** its poll interval resets to the 60 s default on the next cycle

### Story 4.3: Halt on auth error

As an operator,
I want the watch loop to stop cleanly on an authentication failure rather than retry forever,
So that I notice the credential problem instead of watching silent retries burn cycles.

**Acceptance Criteria:**

**Given** Story 4.1's poll loop
**When** a poll raises `AuthError` (a transport 401-equivalent)
**Then** the watch loop halts entirely — for all watched decks, not just the one that failed —
and reports the failure structurally on stderr with a non-zero exit (FR-17, NFR-03)
**And** the loop does not attempt a retry of the failed poll before halting

---

## Epic 5: Keep Design current with the shipped exports

After `deck-export` regenerates a deck's derived artifacts, Design ends up holding the same
complete set. Builds on Epic 2's deck-export integration; independently complete — an operator
gets export push-back without needing watch mode running.

### Story 5.1: Push regenerated exports with etag guard

As an operator,
I want the derived export set pushed back into Design after a pull + `deck-export` cycle,
So that Design holds the same complete artifact set the repo does.

**Acceptance Criteria:**

**Given** a deck whose derived exports were just regenerated (post `deck-export`, per Epic 2)
**When** the export push-back runs
**Then** it declares the export filenames via `finalize_plan` and writes each via
`write_files`, using each file's last-known etag (`"0"` for a first push) (FR-18)
**And** a file whose local hash matches its last-pushed etag record is skipped — no
`write_files` call is made for it (FR-19, NFR-08)

### Story 5.2: Conflict refusal on export push

As an operator,
I want a Design-side conflict on any export file to stop the push cleanly,
So that I never silently clobber a change made directly in the Design project.

**Acceptance Criteria:**

**Given** Story 5.1's push logic and an export file whose Design-side etag has changed since
Herald's last-pushed record (simulated conflict)
**When** the export push-back runs
**Then** that file's write is refused structurally (`ExportConflictError`), reported clearly,
and the rest of the push set — files with no conflict — still completes; no partial clobber of
either the conflicted file or an inconsistent partial-success state (FR-20, NFR-02)

---

## Deferred / Roadmap (explicitly out of V1 — no epics/stories here)

Per the PRD's explicit instruction, the following are **not** decomposed in this document —
they require their own `bmad-spec` pass before any future epic/story breakdown:

- **`herald updates compile`** — weekly release notables from pyforge's own structured
  telemetry.
- **`herald broadcast`** — omnichannel delivery of compiled updates.
- **`herald deck generate`** — Dream→deck rendering from a raw prompt.
- **`herald bmad init`** — BMAD monorepo/multi-project integration (Marshal's, not Herald's).

## Validation Summary (Step 4)

- **FR coverage:** all 26 FRs (FR-01–FR-26) appear in exactly one epic's coverage list and at
  least one story's acceptance criteria; none are orphaned.
- **NFR coverage:** NFR-01–NFR-09 are each exercised by at least one explicit AC (NFR-01/AD-4 →
  1.3/1.4; NFR-02 → 1.4/1.6/2.1/5.2; NFR-03 → 4.3; NFR-04 → 1.2/1.3; NFR-05 → 1.2/1.3; NFR-06 →
  1.6; NFR-07 → every story's Given/When/Then is exit-code/file-state based by construction;
  NFR-08 → 2.1/3.1/4.1/5.1; NFR-09 → 4.1).
- **No starter template applies** — Story 1.1 is a from-scratch scaffold, mirroring the
  `pyforge-warden`/`pyforge-atlas` precedent rather than cloning a template.
- **Epic independence:** Epic 2 does not require Epic 3, 4, or 5 to function; Epic 3 does not
  require Epic 4 or 5; Epic 4 does not require Epic 5. Each stands alone atop Epic 1's
  foundation.
- **No forward story dependencies:** within every epic, story N.M cites only stories N.1..N.(M-1)
  or earlier epics — verified by re-reading each story's "Given" clause above.
- **File-churn check:** Epics 2 and 5 both touch `deck_pipeline.py`'s deck-export integration,
  and Epics 1/2/3 all touch `state.py` — assessed as incidental sharing (each epic adds a
  distinct capability facet, not repeated churn on the same behavior), consistent with the
  `pyforge-warden` precedent's own multi-epic touches to `verdict.py`/`report.py`; no
  consolidation warranted.
