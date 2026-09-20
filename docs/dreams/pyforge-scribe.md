---
title: Scribe — the inward voice
type: dream
owner: scribe
status: specified
---

> **One chain** (2026-09-17). This is the station Dream. 16 satellite Dreams archived in place; CAPs live on `spec-pyforge-scribe`.

# Scribe — capture the decision, keep the graph, answer from memory

## The Dream

The Chronicler's dream: **what the team knows, every agent and every session
knows.** Where Herald tells the world, Scribe tells the team — every decision,
rejected tradeoff, and 3am runbook captured as it happens, curated so it stays
true, compiled into a knowledge graph, and answerable on demand. Adopted
2026-07-23 when the ownership audit found the knowledge station unowned — the
exact disease [[sentinel]] diagnosed in 2026-04: *knowledge is lossy; the
graph is there; nobody writes it down.*

## What it owns

- **Team memory** — the shared, version-controlled `.claude/memory/` layer and
  the `scribe capture` / `scribe capture --promote` workflow that fills it.
  [[team-memory]]'s own Dream (its Spec: MEM-1 committed-not-personal, MEM-2
  scoped recall, MEM-3 entries-carry-provenance) and the legacy 10-story
  `claude-team-memory` spec it pointed to are both fully folded into this
  Dream and `spec-pyforge-scribe` — there is no separate team-memory scope
  left to track outside this file.
- **[[sentinel]]'s unbuilt core** — the team knowledge graph, compiled nightly
  from the tools the team already uses (git history, memlogs, retros,
  CHANGELOGs, `docs/dreams/`) and queryable via `scribe recall`. This is Wave
  2 and has not started.
- Curation surfaces Scribe is scoped to grow into once the graph exists: the
  Dreams index, doc/ADR hygiene, wikis (the atlas Wave-H Karpathy wiki +
  agno crews are Scribe-station machinery), the library catalog's freshness.

## What it looks like when real

- `scribe capture` records a decision the moment it happens, straight into
  `.claude/memory/`; `scribe capture --promote` scans a contributor's
  personal auto-memory, proposes which entries are team-relevant ("would a
  day-1 contributor benefit from this rule?"), rewrites them in team voice,
  and never silently promotes — every promotion is proposed, then confirmed.
- Recall is scoped, not a dump: a session asks `scribe recall "why did we
  drop Kùzu?"` and gets one grounded, cited answer, not the whole store — the
  same answer for any operator or concurrent agent worktree, since the
  compiled graph is the single shared source, never per-session state.
- Nothing is fabricated: every `recall` response carries a citation
  resolvable to a real file or commit, or an explicit "no grounded answer
  found." A superseding capture invalidates a prior record rather than
  deleting it, so history survives — every graph node traces back to the
  source file or commit that produced it, and a stale entry stays visibly,
  not silently, stale.
- Air-gapped by construction: capture, compile, and recall make zero
  outbound network calls by default.

## What is real

*Corrected 2026-09-09 (fleet readiness pass). The superseded 2026-07-25 reading
was: "Epic 1 … is three of five stories done … Epic 2 (Knowledge Graph — Compile &
Recall) … is untouched: all four stories backlog. **Three of nine stories complete
overall.**" Every clause of it is false — the station shipped 19/19 stories
across seven epics while that paragraph stood.*

Shipped at `src/shared/packages/pyforge-scribe/` (CLI `scribe`, module
`pyforge.scribe`, ~3,700 lines across 17 modules). All seven epics are `done`
— 19 of 19 stories:

- **Epic 1 — team memory.** `scribe capture` writes `.claude/memory/<type>/*.md`;
  `--promote` runs the proposal-then-confirm flow with team-voice rewrite and
  pointer-stub write-back. Live in this repo: team entries across `feedback/`,
  `project/` and `reference/`, indexed by `MEMORY.md` and `@import`-ed from
  root `CLAUDE.md`.
- **Epic 2 — the knowledge graph.** `GraphStore` is a real `typing.Protocol`
  port (`graph_store.py:59`) with a flat-file v1 adapter, bi-temporal
  supersession (`invalidate_edge`, never deletion), and `scribe recall`
  returning cited answers or an explicit "no grounded answer found".
- **Epic 3 — the transcript surface.** `transcripts.py` (506 lines) mines a
  user's own raw `.jsonl` sessions for un-curated decisions and feeds them to
  the same promote gate; the same scan joins compile as a sixth named surface.
  See [[scribe-mines-raw-session-transcripts]].
- **Epic 4 — plugin registration.** `GraphStore` is a `pyforge.core.hooks`
  CAP-18 plugin; three drivers now sit behind the one port (flat-file/`scribe`,
  PostgreSQL+pgvector/`steward`, query-plane/`atlas`).
- **Epics 5-7** — the SKF skill + persona, the first portal slice (`recall`),
  the graphify and cocoindex ingest extras, a graph-node staleness flag, and
  three scribe-wielded docs skills.

Spec: `spec-pyforge-scribe` (CAP-1..CAP-4, AD-1..AD-9). `.claude/memory/` is
live in this repo — `feedback/`, `project/`, `reference/` subdirectories, a
`MEMORY.md` index, a `README.md` documenting the schema.

**Not yet true:** nothing runs the compile on a schedule. `graph compile
--nightly` is unattended-safe, but the documented trigger is "an opt-in
operator crontab entry" (`cli.py:290-291`, `docs/cli-runbooks.md:89-103`) that
is not installed — `.claude/data/pyforge-scribe/graph.json` was last written
2026-08-27. And `--semantic` recall (`cli.py:316-320`) is opt-in, off by
default, and ranks over a 7-entry synonym map; that is carried as steward
Story 49.7 (Unifying CAP-14), not re-minted here.

## Realization log

- **2026-07-23** — Seeded when the crew grew 6 → 8 (Scribe + Steward adopted; `3a50eebfc9`).
- **2026-07-25** — `spec-pyforge-scribe` derived under pyforge-scribe (`83ee5527c0`); it now reads
  `shipped`. The legacy `docs/specs/claude-team-memory.md` intake was superseded into this chain the
  same day.
- **2026-08-08** — Status flipped to `realized` in the stale-status hygiene pass (`bfa9fd688d`); the
  station's planning chain is complete — read `sprint-status-ledger.yaml` under pyforge-scribe or
  `fleet-picture` for what, if anything, is left.
- **2026-09-09 (fleet readiness pass — body re-grounded, status held)** — § *What is real* was
  frozen at the 2026-07-25 chain derivation ("three of nine stories complete overall", "Epic 2 …
  untouched") while the station shipped 19/19 stories across seven epics; rewritten above with
  the superseded wording quoted. **Status held at `realized`** — capture, compile, recall and
  the transcript scan all execute, and `.claude/data/pyforge-scribe/` holds a real 1.67 MB
  `graph.json` plus a real transcript-scan cache. Two honest gaps recorded rather than papered
  over: (1) **no scheduled compile is installed anywhere** — the "nightly" trigger is a
  hand-installed crontab line and the graph is 13 days stale, so the Spec's own signal ("nightly
  compile completes unattended across at least 4 consecutive scheduled runs") is unverifiable;
  vessel is scribe **Epic 8**, minted this date (fleet-readiness decision batch 2026-09-09, row
  C6). (2) "Semantic recall" is a 32-dim SHA-256 hash embedding over a 7-entry hardcoded synonym
  map, opt-in and off by default (`embeddings.py:14,24-32`; `recall.py:94`) — carried as steward
  Story 49.7 (Unifying CAP-14) under the Charter's outcome/mechanism rule, not re-minted as a
  scribe capability. Also closed this date on `spec-pyforge-scribe`'s memlog: the ADR-numbering
  question (kept Scribe's own vocabulary; the read-a-target-repo's-`docs/adr/` half split off as
  deferred work), and the two remaining body questions, both answered in code.
- **2026-09-20 — Claude Code reads `AGENTS.md` natively now; the surface must be version-aware,
  not version-dependent.** Operator ask 09:35Z after Claude Code 2.1.277 (2026-09-18) shipped
  a built-in `agents-md` mod (research: the mod's README and source in `anthropics/claude-code
  mods/agents-md`, and the strings in our own installed 2.1.278 binary). Facts that matter: four
  modes via the `instructionFiles` option (`/config` → "Project instructions"); the default
  `claude-md-or-agents-md` *stays out of any project that has a `CLAUDE.md`* — so in this repo the
  mod does nothing today and `AGENTS.md` still arrives only through `CLAUDE.md`'s bare
  `@AGENTS.md` import; `claude-md-and-agents-md` loads every `AGENTS.md` beside `CLAUDE.md`,
  deduped by path then content (an `@`-imported file is never loaded twice) and attaches *nested*
  `AGENTS.md` files on `Read` — which is the only way the atlas child
  `src/shared/packages/pyforge-atlas/AGENTS.md` ever reaches Claude Code; the option lives in
  user settings / `--settings` / managed settings, never the project's `.claude/settings.json`;
  unavailable on Bedrock / Vertex / Foundry. So: keep the import as the floor (older versions
  and the enterprise runtimes), pin the mode for the Claude runtimes we drive (operators' user
  settings; marshal's dispatch launch — that half is marshal's, Story 46.11), state the
  version/mode in the harness table, collapse the one duplication the parity test missed
  (`CLAUDE.md` "Behavioral Guidelines" vs `AGENTS.md` "Behavioural guidelines" — same five
  principles, different spelling), and give the operator a currency signal when the runtime is
  below 2.1.277 or the mode is not the pinned one. → CAP-29 / Story 19.3 (Epic 19 stays `done`;
  the story sits beneath it — a done key never moves).
- **2026-09-19 — Scribe serves every harness (seeded at the review of PR #1513, a parallel
  session's AGENTS.md / GEMINI.md governance PR).** "What the team knows, every agent and every
  session knows" was true for one harness: Claude Code imports `.claude/memory/MEMORY.md`, and
  nothing else did. The research that decided the shape —
  `planning-artifacts/research/multi-harness-instruction-surface-2026-09-19.md` (every harness's
  live docs checked that day: Claude Code, Cursor, Gemini CLI / Antigravity, Copilot cloud agent +
  CLI, Devin, Codex, BMAD-METHOD) — found: (1) **Claude Code never loads `AGENTS.md` here** — a
  `CLAUDE.md` exists and does not import it, so the verified `bmad:context` block bound every
  harness except the one doing most of the work (four PRs that day carry the attribution trailers
  it forbids); BMAD's own `bmad-project-context` prescribes the one-line `@AGENTS.md` import.
  (2) Copilot's coding agent and Devin's Knowledge ingest `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`
  and every `.mdc` at once, so **copying a manual into each tool file multiplies and contradicts**;
  Cursor / Codex / Jules / Devin / Copilot read `AGENTS.md` natively, Gemini needs
  `.gemini/settings.json` `context.fileName`, VS Code chat needs `chat.useAgentsMdFile`. (3) The
  PR pointed every harness at five memory files that exist only in one operator's Claude auto-memory
  (`~/.claude/projects/…`), not in `.claude/memory/` — the promotion path is `scribe capture`.
  Decomposed the same day as **`spec-pyforge-scribe` CAP-27 / Epic 19 / Story 19.1** (operator
  rulings: point, don't copy; import + no trailers; direct-capture the team-relevant notes; full
  chain). Seeded, not decomposed — each a later `bmad-spec` pass: (4) the root `AGENTS.md` (402
  lines) and `CLAUDE.md` (357) shrink to the < 200-line / "expensive to rediscover" bar with a
  nested `AGENTS.md` per station package (atlas is the exemplar) and path-scoped rules; (5) the
  skill tree (`.claude/skills/`, 76 BMAD + 7 SKF) is exposed on the Agent Skills neutral path so
  Cursor, Codex, Gemini, Copilot and Antigravity discover the same skills; (6) the transcript scanner
  (CAP-17/18) ingests Cursor / Gemini / Copilot / Devin session logs, not only
  `~/.claude/projects/**`; (7) `scribe recall` is reachable from the Guild env or the station MCP
  so a 59-minute Copilot session or a Cursor Cloud agent can ask it (PRD FR-13 "any session, any
  operator" → "any harness") — *the Guild-env half decomposed the same day as CAP-28 / Story 19.2 on
  the operator's ruling ("shouldn't we fix this"); the MCP half stays seeded*; (8) the pointer files join `governance-currency`'s governed documents
  (marshal-owned script); (9) a per-spec surface-baseline file so parallel lanes stop colliding on
  `scripts/.spec-surface-baseline.json` (doctor/marshal-owned). (10) Devin Playbooks / MultiDevin and
  Copilot custom agents (`.github/agents/*.agent.md`) are first-class analogues of marshal dispatch
  and the SKF personas the estate does not use yet — an opportunity for Herald/Marshal, recorded here
  because Scribe owns the instruction surface they would read. Devin's own docs (checked 2026-09-19):
  it reads `AGENTS.md` before coding and its Knowledge ingests `AGENTS.md`, `CLAUDE.md`, `.mdc` rules
  and `.claude/skills/**/SKILL.md`; Playbooks and Repo Setup (the `pixi install -e pyforge-guild`
  snapshot) are **app-side, not repo files** — an operator with a Devin seat must create them; no
  Devin session was available to verify any of this live. Microsoft Copilot (M365 / Copilot Studio)
  reads no repo files at all — BMAD reaches it only through a declarative agent with a knowledge
  source (the *Run-BMad-in-Microsoft-Copilot* intake gist); out of scope for file discovery.
  **Live-verified today: Claude Code only** (a fresh `claude -p` in the PR worktree quoted the
  verified block through `@AGENTS.md`; the same prompt on `main` answered NOT LOADED).
  (11) **The operator inbox is a machine-tracked surface, not a chat message.** The same day's
  closeout found six asks that existed only in one agent's auto-memory and the conversation
  (stale loop runs to retire, a stash/worktree purge, a live sync proof, cross-harness
  verification, a quota cap, a token) plus four older leftovers nobody had written down (a
  poisoned story key, a dead MCP path, an unanchored `.gitignore` rule, seventeen merged
  worktrees). Today `deferred_work_intake.py` ingests only a story spec's `deferred:` list, and
  `fleet-picture` surfaces only what a detector can compute. Target: (a) story specs and
  session hand-offs carry a `needs_operator:` list that the same intake turns into DW rows
  with `status: awaiting-operator` (owner: marshal — the intake script); (b) a doctor source
  `operator-inbox` lists every `awaiting-operator` row and every team-memory
  `operator-inbox-*` entry with its age in `fleet-picture` ATTENTION, never silently ageing out
  (owner: doctor); (c) the session contract in `AGENTS.md` says a session that leaves an
  operator-only ask writes it with `scribe capture --type project` before it ends, and the
  `.claude/memory/project/operator-inbox-*` entry is the human-readable twin of the DW rows
  (owner: scribe — this item). Seeded here; `bmad-spec` mints the CAPs on the next pass.
