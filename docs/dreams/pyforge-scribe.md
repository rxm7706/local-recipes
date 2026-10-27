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

## 2026-09-25 — The local Postgres cluster starts from any worktree

Found while landing PR #1605 from `local-recipes-wt-unifying-strategy-dream-seeds-2026-09-25`:
`pixi run -e pyforge-scribe-pg scribe-pg-up` initialised the cluster, then PostgreSQL refused to
start — "could not create any Unix-domain sockets" — because `scripts/scribe_pg.py` passes
`-k <checkout>/var/scribe-pg` and that socket path exceeds the ~107-byte limit. Every long-named
worktree hits it; the 18 durable-GraphStore tests then fail loudly, by design, and `pr-preflight`
is red for a reason that has nothing to do with the change. The workaround was to start the
primary checkout's cluster and let the tests reach it over TCP.

The Dream: the socket directory is short and per-user (`SCRIBE_PG_SOCKET_DIR`, else
`$XDG_RUNTIME_DIR/scribe-pg`, else `/tmp/scribe-pg-<uid>`), the data directory stays under the
checkout's gitignored `var/scribe-pg/`, and `scribe-pg-up` succeeds from any checkout the estate
creates. Port 5433, the DSN the tests hard-code, and the no-container rule do not change.
`bmad-spec` mints **CAP-31**; Epic 22 / Story 22.1.

## 2026-09-26 — The instruction surface loads once, and says what runs it

Found landing Story 21.1 (PR #1621). Claude Code runs with
`instructionFiles=claude-md-and-agents-md`, so `AGENTS.md` and `CLAUDE.md` both load every
session, and `skf-export-skill` writes its 54-line managed block into both: `_bmad/skf/config.yaml`
lists `ides: [claude-code, other]`, and `claude-code` maps to `CLAUDE.md`. Every session pays for
the block twice. The same pass wrote a false line into `AGENTS.md`: that neither `detectors-ci`
nor `pr-preflight` runs `governance-currency`. Both run it, because `scripts/detectors.py`
discovers `scripts/governance_currency_check.py` by its `*_check.py` glob as `scope=repo`.

The Dream: the SKF block lives in `AGENTS.md` only (`ides: [other]`; snippet paths stay
`.claude/skills/` through `snippet_skill_root_override`), and `CLAUDE.md` carries no SKF markers,
so the next export finds no orphan to ask about. `AGENTS.md` says where `governance-currency`
runs. Both sit under **CAP-27** (one file carries the contract); no new CAP. Story 21.2 corrects
the line; Epic 23 / Story 23.1 moves the block.

## 2026-09-29 — Every session knows the BMAD estate it stands on

Found by the 2026-09-12 research pass (`_bmad-output/projects/pyforge-steward/planning-artifacts/research/technical-bmad-suite-lifecycle-agent-knowledge-surface-research-2026-09-12.md`)
and re-verified at `bd1a03dc` on 2026-09-29. The estate already writes down almost everything
about the BMAD Method it runs on: the installed core and modules (`_bmad/_config/manifest.yaml`),
the 127-directory skill catalog with a `description:` on every `SKILL.md`, the phase and sequence
table BMAD ships (`_bmad/_config/bmad-help.csv`), the 13 bmad-suite members and their install
classes (`recipes/bmad-suite/suite-members.yaml`, steward's adoption register), the release
cadence, and the Marshal↔bmad-loop harness contract. What a session actually gets is one pointer
line to the adoption register and, under pitfalls, the shim and config traps. Nothing agent-facing
states the installed core version; the suite verbs (`steward suite pipeline-truth` / `advance`,
`provision --module`, `upgrade bmad-core`), the cadence and the metapackage appear in no
instruction file; upstream stopped publishing `llms-full.txt` at 6.12.0, so the only
machine-readable upstream snapshot in the tree is the 6.11-era file; and the same version numbers
disagree across the register, a Spec header and `pixi.toml` because they are hand-carried in
four places. The 2026-09-26 fold (CAP-27) closed the load-path half of the gap — `CLAUDE.md`
now imports `AGENTS.md` — and left the knowledge half open.

The Dream: **one derived picture of the BMAD estate, never hand-written.** A generated
`docs/reference/bmad-estate-llms-full.md` — the shape `library-llms-full.md` already proved,
with its own drift detector — rendered from the sources above, so an agent opening this repo
reads the installed core, every skill by family, the suite roster with wielder and provisioning
path, the cadence and the harness range from one file that a detector keeps current. Each
instruction file points at it once. The library catalog's freshness is already this station's
curation surface (§ *What it owns*), so the estate catalog is Scribe's too; Steward stays the
owner of the facts (the register, `pipeline-truth`), Doctor of any ambient verdict on them.
`bmad-spec` mints the CAP on this station's Spec; Epic 24 carries the three stories.

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
- **2026-09-20 (evening) — The managed instruction block carries no aspiration.** Found at the
  bmad-project-context refresh closing the fleet consistency pass: two `TODO:` lines had stood in
  `AGENTS.md`'s `bmad:context` block since 2026-09-04 (a commit-msg hook; repo-level ruff/mypy tasks),
  never minted as a Story, so nothing ever scheduled them — exactly the "aspirational state" the
  skill's own best-practices exclude ("describe what is; intent belongs in specs"). Steward now owns
  the two capabilities (CAP-153 / CAP-154, Epic 66); scribe owns the guard: the instruction-surface
  parity meta-test (CAP-27) reds a `TODO:` / `FIXME:` / "not yet landed" inside the managed block, so a
  decision that has no Story cannot hide as a line agents pay for every session. Kinships:
  `spec-pyforge-scribe` CAP-30 → Epic 20; steward CAP-154 retires the two lines it guards.
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
- **2026-09-25** — Dated section *The local Postgres cluster starts from any worktree* seeded (socket-path limit found landing PR #1605); `spec-pyforge-scribe` CAP-31 minted; Epic 22 / Story 22.1 `backlog` with a tracked spec.
- **2026-09-29** — Dated section *Every session knows the BMAD estate it stands on* seeded from the 2026-09-12 research pass (`spec-bmad-suite-lifecycle` research, steward tree); `spec-pyforge-scribe` CAP-32 minted; Epic 24 / Stories 24.1–24.3 `backlog` with tracked specs.
- **2026-09-30** — A defect in CAP-32's realization, found during the wave-1 landings: the estate catalog reads every directory under `.claude/skills/` on disk, not the in-tree sources CAP-32 names. On a checkout where marshal's token-economy kit has deployed the gitignored `caveman` skill (the primary and every dispatch worktree), and where retired skills left `__pycache__`-only directories behind (`cfe-recipe-generation`, `cfe-recipe-lifecycle`), `bmad-estate-check` reds locally while CI, which has neither, stays green. No new CAP: CAP-32 already says in-tree. A new Epic 25 / Story 25.1 (`backlog`, tracked spec) makes the catalog count only the skill directories git does not ignore.
- **2026-10-03 (Phase 4+5)** — **Ruled: scribe's open medium and low deferrals close in one fix story.** The operator ruled on 2026-10-03 that the deferral burn-down's Phase 4 (open medium rows) and Phase 5 (open low rows) run together on the idle station lanes, then, the same day, that each station takes exactly one story. Scribe carries 2 open medium and 12 open low rows (measured with a parser over its `deferred-work-ledger.md`). **What it looks like when fixed:** recall breaks an overlap tie by recency, so a reversed statement no longer outranks its reversal; transcript node ids stay unique across subdirectories; the freshness check's period is tested against the timer; `governance-currency` reads the per-tool pointer files; the Epic 3 surface is reconciled; four recommended follow-up reviews have run. **Constraints:** a `fix` story, no CAP, no flag; a row closes only with a `resolution:` and a cited `verified:` line. Five rows cannot close through a fix and stay open: DW-FU-19-1-3 (a live session per harness needs a seat) and DW-8-1-2 (four nights of the installed timer) need the operator; DW-FU-19-2 (recall over the station MCP) and DW-FU-19-1-2 (a shorter `AGENTS.md`) are new capability, which enters here and through `bmad-spec`; DW-SCRIBE-2026-09-09-ADR-INTEROP's own `close_when` asks for an operator ruling. Owner `spec-pyforge-scribe`. → Epic 26 / Story 26.1, specced 2026-10-03.
- **2026-10-26 (every requirement derives from a capability) — Found:** the rule the Guild amended on 2026-10-26 (a requirement cites one or more defined capabilities and nothing else; `spec-one-chain-per-station` CAP-5, CHAIN-STANDARD § 12) and the multi-station-PR shape #2240 and #2319 set reach a harness only through the surface scribe owns, and none of it was there: AGENTS.md's Pre-PR checklist said nothing about arrows or several stations in one PR, the managed block did not point at CHAIN-STANDARD, no pitfall recorded the shared scribe Postgres (`127.0.0.1:5433`) that failed #2319's parallel preflight, and team memory held neither the rule nor the ruling. **Asked** (2026-10-26, operator): encode the rule so agents stay aligned. **For scribe:** two pointer bullets in items 6 and 7 (outside the block; point, never copy, CAP-27/CAP-29), the pointer and the pitfall inside the block through `bmad-project-context` (record, provenance re-verified against `92fa3edbbd`), the incident in `docs/reference/agent-instruction-notes.md`, and two `scribe capture` entries. Epic 27 / Story 27.1, built in the one-PR effort with the other seven stations; no scribe CAP minted, no code.
- **2026-10-26 (every pre-rule runtime capability sits behind a kill switch) — Found:** the flag inventory (doctor Story 34.4, regenerated on the fixed join) reads 1 scribe capabilities minted before the rule date as reachable at runtime with no flag; the operator ruled on 2026-09-28 that every capability ships behind a flag, with one retrofit flag per capability defaulting ON (Q6), and no station had minted its retrofit. **Ruled** (2026-10-26, operator: the CAP-7 retrofit sheet approved as recommended, R1–R8 — flag the unflagged runtime rows only, one key per CAP, an invariant's switch makes the dependent verb refuse, the 90-day clock stands and each station mints its retirement story now). **For scribe:** 1 keys `pyforge.scribe.<capability>` ON in dev, staging and production with their clocks from 2026-10-26, each read through `pyforge.core.flags` at its verb or behaviour site with one two-state test; a flag-off verb stays listed and refuses with the usage code 2 (Q3); no exit code changes. Epic 29 / Stories 29.1–29.1, built in the one-PR retrofit effort; Story 29.2 (the retirement, due 2027-01-24) minted backlog; no scribe CAP minted.

## 2026-10-26 — Dream — PyForge Scribe: Team Memory Management (folded from pyforge-scribe-team-memory)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 28.1). The body below is `docs/dreams/pyforge-scribe-team-memory.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/pyforge-scribe-team-memory.md`.*

> **Superseded.** This Dream proposes a team-memory system for Scribe — structured
> frontmatter entries, `/remember` capture, promotion review, automatic context loading,
> a compact `MEMORY.md` index. [`docs/dreams/pyforge-scribe.md`](pyforge-scribe.md)
> (status: specified) already owns this exact scope via `spec-pyforge-scribe` and the
> pre-existing `spec-team-memory` it absorbed 2026-07-25. Scribe's `epics.md` already
> carries the stories this dream would duplicate — Epic 1 "Team Memory — Capture &
> Promotion" (Story 1.1 `scribe capture` + frontmatter schema parity, Story 1.2 `CLAUDE.md`
> wiring so "every session starts already knowing what the team knows", Story 1.3
> proposal-then-confirm promotion using the team-relevance test "would a day-1 contributor
> benefit from this rule?") and Epic 2 "Knowledge Graph — Compile & Recall" (the
> pattern-discovery capability this dream's Problem section calls for). Created 2026-08-02
> in a bulk commit later found to contain fabricated content elsewhere in the same commit;
> retired same day rather than spec'd as new work. See `spec-pyforge-scribe-team-memory`
> for the retirement record.

## PyForge Scribe — Team Memory Management

### Vision

**Scribe** manages team memory and shared knowledge — capturing decisions, project context, team feedback, and reference material in structured, reviewable prose that every contributor (human or agent) can learn from.

**The ask**: Build a memory system that makes every decision auditable, every lesson carried forward, and every contributor's context shareable without losing nuance to automation.

### Problem

- **Knowledge evaporates.** A contributor solves a hard problem; the solution lives in a closed Slack thread. Next contributor reinvents the wheel.
- **Context is scattered.** Project state in PRs, decisions in issues, feedback in code reviews, lessons in wikis. No single source of truth.
- **AI agents have amnesia.** Claude Code can solve a problem brilliantly today; tomorrow a new session starts with no context. Valuable patterns are lost.
- **Onboarding is slow.** New team members drown in Slack history. No structured narrative of "here's what we've learned."
- **Feedback is reactive.** Issues are caught in code review repeatedly. The feedback is written three times; the pattern is never named or systematized.

### Realization

**Scribe** delivers:

1. **Structured Memory** — YAML frontmatter + prose body. Type (user/project/feedback/reference), tags, related memories, and dates. Queryable, versionable, git-tracked.

2. **Automatic Capture** — When a contributor finds a gotcha or a solution, they use `/remember [type]` inline. Scribe scaffolds the entry; they fill in the reasoning.

3. **Team Layers** — User memory (auto-memory per Claude Code session) → team memory (promoted after review). Only team-relevant entries live in the tracked tier.

4. **Memory Promotion** — Stories with team relevance go through editorial review. "Is this a pattern, or just today's frustration?" Team review decides.

5. **Context Loading** — Agents load all team memory automatically. Claude Code starts a session already knowing the team's feedback, the project's patterns, the shared gotchas.

6. **Memory Index** — Concise index (MEMORY.md) with links to full entries. 200-line compact view; detail lives in linked files.

### Success Criteria

- ✅ **Capture**: Every session surfaces 3+ memory candidates automatically
- ✅ **Promotion**: Team feedback loop works; entries get promoted after review
- ✅ **Context**: Agents load team memory on startup; context shapes their behavior
- ✅ **Searchability**: Memories indexed and queryable; pattern discovery takes <1 min
- ✅ **Governance**: Memory is git-tracked, auditable, and reviewed like code
- ✅ **Narrative**: New contributor reads MEMORY.md and can orient themselves in 10 min

### Acceptance

Scribe is done when:
1. All 8 PyForge stations have team memory directories with 20+ entries each
2. Memory promotion workflow proven: 10+ entries promoted through review
3. Agents load memory on startup and reference it in decisions
4. Pattern detection working: queries surface related memories for similar problems
5. Onboarding time cut by 50%: new contributor oriented in 10 min via MEMORY.md
6. Retention proven: memories prevent 80%+ of repeated gotchas in future sessions

## 2026-10-26 — One owner for “where is this symbol?” (folded from scribe-code-navigation-owner)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 28.1). The body below is `docs/dreams/scribe-code-navigation-owner.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/scribe-code-navigation-owner.md`.*

## One owner for “where is this symbol?”

### The Dream

Agents ask structure questions and get two answers: Scribe `code:`
AST nodes and Marshal `codegraph.db`. That split wastes tokens and
will copy into python-foundry if we move the tree first.

The Dream is **one navigation owner**. Marshal codegraph answers
symbols. Graphify `code:` stays a derived extra for `index report`,
`--mode code`, and the foundry move-list.

### What it looks like when real

- Session instructions say: symbols → codegraph, not
  `scribe recall --mode code`.
- Default recall still omits `code:`.
- Graphify is not deleted.
- Unifying CAP-14 (pgvector / semantic) is a different decision.

### Constraints / Non-goals

- Do not run `codegraph install --target claude` (fights Marshal
  `mcp_servers`).
- Do not nightly-graphify `recipes/` or the repo root.
- Do not flip Epic 44 `blocked` from this Dream.

### Kinships

[[pyforge-scribe]] · [[scribe-knowledge-layers]] ·
[[marshal-token-economy]] · `intelligence-before-foundry`

### Realization log

- **2026-09-13** — Operator accepted the CAP-14 (later-caps) ruling.
  Spec `spec-scribe-code-navigation-owner`; Epic 17 Story 17.1.
  Reminted in worktree `hub-scribe-17-mint` (primary untracked drafts
  were not the source of record).

## 2026-10-26 — The nightly graph still knows the code (folded from scribe-graphify-nightly-currency)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 28.1). The body below is `docs/dreams/scribe-graphify-nightly-currency.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/scribe-graphify-nightly-currency.md`.*

## The nightly graph still knows the code

### The Dream

The knowledge graph this repo already compiles every night should still contain
the code surface in the morning. Today it does not. `scribe graph compile` is a
full rebuild. The graphify ingest that writes `code:` nodes is an opt-in extra.
The 02:30 trigger runs the lean compile, so every scheduled night throws away
whatever `scribe index build` wrote the day before.

Worse, the extra cannot run against the graphifyy this estate actually
installs. After `collect_files` loads `graphify.extract` the package attribute
is the **submodule**, and `graphify.extract(...)` raises `TypeError`. The
official `scribe index build` verb in the `pyforge-scribe` env exits 2 for
missing `graphifyy`; even when that package is on `PYTHONPATH`, the call dies
on the submodule shadow.

The Dream is one scheduled rebuild that keeps memory, memlogs, git, retros,
transcripts, **and** the station-package AST graph in the same store — without
turning every interactive `scribe graph compile` into a 60-second ingest, and
without a second graph product.

### What it looks like when real

- `scribe index build` against `src/shared/packages/` completes through the
  GraphStore persist port on the real `graphify` package.
- The 02:30 trigger's compile keeps `code:` nodes. A morning `graph.json` is
  not smaller than last night's by thirty thousand nodes.
- An interactive compile with `SCRIBE_GRAPHIFY_EXTRA` unset still skips the
  extra (air-gap default). An operator can still force the extra off on the
  trigger with an explicit `0`.

### Constraints / Non-goals

- No parallel store. Code nodes write through `open_graph_store`, same as
  Story 6.1.
- No foundry-root `graphify-out/`.
- Not a GitHub Actions workflow (Epic 8 HARD boundary).
- Not a new GraphStore engine.

### Kinships

[[pyforge-scribe]] (owner; CAP-2 already names the optional seventh graphify
surface) · [[scribe-mines-raw-session-transcripts]] (the last compile-surface
currency gap) · [[pyforge-unifying-strategy]] (realization gate: built is not
in effect) · [[deck-family-currency]] (Herald owns `facts.yaml` derivation;
Scribe compiles those ledgers as `doc` nodes — never the presentations/ export
tree)

### Realization log

- **2026-09-13** — Dream captured and specified the same morning. Spec
  `spec-scribe-graphify-nightly-currency` (`ready`, CAP-1/CAP-2) lives under
  pyforge-scribe. Decomposed as Epic 8 Story 8.2; durable story spec
  `spec-8-2-the-nightly-compile-keeps-the-graphify-code-surface.md`. Sprint
  tracking regenerated via `sprint_plan.py generate`; ledger key
  `8-2-the-nightly-compile-keeps-the-graphify-code-surface` is `done`.
- **2026-09-13** — Operator: fact ledgers should be added. CAP-3 + Story 8.3
  (`spec-8-3-herald-fact-ledgers-join-the-compile.md`); compile reads
  `presentations/<slug>/facts.yaml` as `doc` nodes. Kinship
  `deck-family-currency`.

## 2026-10-26 — The code map covers the host and factory scripts, not the recipe warehouse (folded from scribe-graphify-target-list)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 28.1). The body below is `docs/dreams/scribe-graphify-target-list.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/scribe-graphify-target-list.md`.*

## The code map covers the host and factory scripts, not the recipe warehouse

### The Dream

Nightly extra-on compile already keeps `code:` nodes for
`src/shared/packages/`. Agents asking about the Django host or a pixi
helper still miss, because those trees were never on the list. Widening
the default to the repo root — or to `recipes/` — recreates the cost
bound Story 3.3 / 8.2 exist to hold.

The Dream is an **explicit target list**: station packages, the platform
host, and `scripts/`. Missing optional dirs are silent. `recipes/` and
`.` stay off the list.

### What it looks like when real

- Extra-on compile ingest walks `src/shared/packages/`, `src/platform/`,
  and `scripts/` when those directories exist.
- A fixture with `recipes/` present still produces no `code:` citation
  under `recipes/`.
- `scribe index build` with no `--target` uses the same list.
- An explicit `--target` stays one path.
- Extra-off compile is unchanged (zero `code:` nodes).

### Constraints / Non-goals

- Do not add `recipes/` or the repo root to the default list.
- Do not turn the extra on by default.
- Do not decide CAP-14 (graphify `code:` vs `codegraph.db`).

### Kinships

[[pyforge-scribe]] · [[scribe-knowledge-layers]] ·
[[scribe-graphify-nightly-currency]]

### Realization log

- **2026-09-13** — Hoisted parked CAP-8. Spec
  `spec-scribe-graphify-target-list`; Epic 15 Story 15.1.

## 2026-10-26 — The story you are on is in the graph; the ones you finished are not (folded from scribe-in-flight-story-specs)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 28.1). The body below is `docs/dreams/scribe-in-flight-story-specs.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/scribe-in-flight-story-specs.md`.*

## The story you are on is in the graph; the ones you finished are not

### The Dream

Folder `SPEC.md` files already compile when they are `ready` or
`in-progress`. Per-story specs — the atomic SM→dev handoff — do not.
An agent mid-story asking “what does 10.1 actually bind?” gets silence,
or would get every historical `spec-2-1-…` if we globbed the folder.

The Dream is **in-flight only**. A story spec joins the compile as `doc`
when that project's tracked sprint ledger says the story is
`ready-for-dev`, `in-progress`, or `review`. Frontmatter on those files
is stale (`ready-for-dev` on stories that have been `done` for months).
The ledger is the filter. Done and backlog stay out.

### What it looks like when real

- A ledger row `10-1-…: in-progress` plus
  `planning-artifacts/specs/spec-10-1-….md` becomes one `doc:` node.
- The same file with ledger `done` produces no node, even if frontmatter
  still says `ready-for-dev`.
- A project with no ledger, or every story `done`, compiles zero
  story-spec nodes and no warning.

### Constraints / Non-goals

- Do not ingest the historical corpus. Do not use frontmatter as the
  in-flight oracle.
- Do not compile folder `SPEC.md` here (already CAP-3).
- Do not compile `prd.md` / `epics.md` bodies (CAP-7, parked).

### Kinships

[[pyforge-scribe]] · [[scribe-knowledge-layers]]

### Realization log

- **2026-09-13** — Hoisted parked CAP-6. Spec
  `spec-scribe-in-flight-story-specs`; Epic 10 Story 10.1.
- **2026-09-13** — CAP-1 realized in Story 10.1: ledger-filtered compile.

## 2026-10-26 — The graph is layered knowledge, not one bag (folded from scribe-knowledge-layers)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 28.1). The body below is `docs/dreams/scribe-knowledge-layers.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/scribe-knowledge-layers.md`.*

## The graph is layered knowledge, not one bag

### The Dream

The estate already compiles a knowledge graph every night. Agents still do not
know what to ask, and the one consumer that works (Marshal planning-graph)
never sees most of what the compile writes. Thirty-seven thousand AST nodes
sit in the same candidate list as seven team-memory decisions. Retros are a
filename glob. Stale flags fire on a compile that just read the file. Dreams
and five-field SPECs — the contract this repo claims to run on — are absent.

The Dream is **layered knowledge**: policy stays in `AGENTS.md` and skills;
decisions stay in team memory; contracts (active Dreams, ready SPECs, Herald
fact ledgers) compile as `doc`; planning memlogs stay the Marshal slice;
code stays in the store for navigation extras and `scribe recall --kind code`,
never as the default answer. Marshal `codegraph` owns structure-graph
navigation. Archive, test fixtures, and implementation-artifacts are not
fleet truth.

### What it looks like when real

- A full rebuild does not mark just-read sources stale.
- `scribe recall "why…"` cites memory, a Dream, a SPEC, a fact ledger, or a
  memlog — not a graphify label.
- Marshal `context retrieve --scope` still grounds on that project's
  planning tree.
- Nightly still keeps `code:` nodes; default recall does not serve them.
- An agent session knows to run `scribe recall` for decisions and not to
  treat the AST dump as policy.

### Constraints / Non-goals

- No second GraphStore. Code still writes through `open_graph_store`.
- No `docs/**` dump, no `recipes/`, no presentations export tree.
- Cocoindex stays on `scribe index refresh`, not `compile_graph`.
- Do not replace Marshal `codegraph.db` with graphify recall.

### Kinships

[[pyforge-scribe]] · [[scribe-graphify-nightly-currency]] ·
[[deck-family-currency]] · [[marshal-token-economy]] ·
[[pyforge-unifying-strategy]]

### Realization log

- **2026-09-13** — Operator accepted the layered-knowledge recommendation
  (hygiene, named surfaces, kind-filtered recall, session path). Spec
  `spec-scribe-knowledge-layers` under pyforge-scribe; Epic 8 Stories 8.4–8.6
  (8.3 fact ledgers already minted on the currency Dream).
- **2026-09-13** — Parked later CAPs recorded in
  `planning-artifacts/specs/spec-scribe-knowledge-layers/later-caps.md`
  (CAP-6–CAP-14). Not in the five-field contract; do not implement until
  hoisted + Story-minted.
- **2026-09-13** — CAP-4/CAP-5 realized in Stories 8.5–8.6: default recall
  omits `code:`; `AGENTS.md` session path (outside `bmad:context`).
- **2026-09-13** — Parked CAP-10 hoisted to Dream
  `scribe-marshal-fact-visibility` / Spec
  `spec-scribe-marshal-fact-visibility` (Story 9.1).
- **2026-09-13** — Parked CAP-6 hoisted to Dream
  `scribe-in-flight-story-specs` / Spec
  `spec-scribe-in-flight-story-specs` (Story 10.1).
- **2026-09-13** — Parked CAP-9 hoisted to Dream
  `scribe-recall-stale-between-nightlies` / Spec
  `spec-scribe-recall-stale-between-nightlies` (Story 11.1).
- **2026-09-13** — Parked CAP-12 hoisted to Dream
  `scribe-portal-recall-defaults` / Spec
  `spec-scribe-portal-recall-defaults` (Story 12.1).
- **2026-09-13** — Parked CAP-7 hoisted to Dream
  `scribe-planning-pointers` / Spec
  `spec-scribe-planning-pointers` (Story 13.1).
- **2026-09-13** — Parked CAP-13 hoisted to Dream
  `scribe-named-docs` / Spec
  `spec-scribe-named-docs` (Story 14.1).
- **2026-09-13** — Parked CAP-8 hoisted to Dream
  `scribe-graphify-target-list` / Spec
  `spec-scribe-graphify-target-list` (Story 15.1).
- **2026-09-13** — Parked CAP-11 hoisted to Dream
  `scribe-recall-modes` / Spec
  `spec-scribe-recall-modes` (Story 16.1).

## 2026-10-26 — Dispatch cites the same numbers the poster already shows (folded from scribe-marshal-fact-visibility)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 28.1). The body below is `docs/dreams/scribe-marshal-fact-visibility.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/scribe-marshal-fact-visibility.md`.*

## Dispatch cites the same numbers the poster already shows

### The Dream

Herald already derives `presentations/<slug>/facts.yaml`. Scribe already
compiles each ledger as a `doc:` node. An unscoped `scribe recall` can hit
those citations. Marshal planning-graph retrieve cannot: `--scope <slug>`
admits only `_bmad-output/projects/<slug>/`, so the fact ledger sits
outside the candidate list.

The Dream is **identity visibility**. When retrieve asks for
`pyforge-scribe`, that project's own `presentations/pyforge-scribe/facts.yaml`
is a legal citation — not every deck, not the export tree, not a second
`--facts` flag that Marshal would have to learn.

> A number the poster already shows should be recallable under the same
> slug the loop is scoped to.

### What it looks like when real

- `scribe recall "…" --scope pyforge-scribe` can cite
  `presentations/pyforge-scribe/facts.yaml`.
- `--scope pyforge-scribe` still excludes `presentations/pyforge-warden/facts.yaml`
  and every path that is not that project's planning tree or that one ledger.
- Marshal `context retrieve` keeps passing `--scope` only. No new argv.

### Constraints / Non-goals

- Identity slug only. No alias table (`pyforge-unifying-strategy` /
  `pyforge-genesis` stay unscoped-only until a later mapping CAP).
- Do not widen `--scope` to `presentations/` or the export tree.
- Do not change compile. Do not replace Herald as the ledger owner.

### Kinships

[[pyforge-scribe]] · [[scribe-knowledge-layers]] ·
[[deck-family-currency]] · [[marshal-token-economy]]

### Realization log

- **2026-09-13** — Hoisted parked CAP-10 from
  `spec-scribe-knowledge-layers/later-caps.md`. Spec
  `spec-scribe-marshal-fact-visibility`; Epic 9 Story 9.1.
- **2026-09-13** — CAP-1 realized in Story 9.1: identity citation rule in
  `recall.py`.

## 2026-10-26 — Scribe reaches past curated memory into the raw session transcripts underneath it (folded from scribe-mines-raw-session-transcripts)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 28.1). The body below is `docs/dreams/scribe-mines-raw-session-transcripts.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/scribe-mines-raw-session-transcripts.md`.*

## Scribe reaches past curated memory into the raw session transcripts underneath it

### The Dream

Scribe already promotes personal memory into the team's shared knowledge: `scribe capture
--promote` (Story 1.3, shipped) scans a contributor's **curated** personal auto-memory
(`~/.claude/projects/<repo>/memory/*.md`) and proposes team-relevant entries for
`.claude/memory/`. That closes one gap. It leaves a deeper one open: curated memory is
itself a filter — only what an agent judged worth writing down, in the moment, survives
into it. Everything discussed in a session but never promoted even to *personal* memory —
an idea floated and dropped, a design considered and rejected, a fact mentioned once in
passing — exists only in that session's raw transcript, and nothing scans those.

Confirmed live, 2026-08-15: this repo's own personal-memory directory holds 22 raw session
transcripts (`.jsonl`, 161MB total) alongside its curated `.md` files. Every one of those
transcripts is a superset of whatever got curated from it. Scribe's own planned Epic 2
knowledge-graph compile sources (per this Dream's own text: "git history, memlogs, retros,
CHANGELOGs, `docs/dreams/`") don't currently name these transcripts either — so even the
NEXT layer of Scribe, once built, would still miss this. The mechanism to recover from them
already exists as precedent, just not as a systematized capability: CLAUDE.md's own "Story
specs are durable" recovery-source hierarchy names Claude Code session transcripts as the
highest-fidelity recovery source, and it is how pyforge-warden's 13 lost story specs were
actually recovered verbatim on 2026-07-25 — proof the raw signal is real and recoverable,
done once by hand, never generalized.

### Whose job this is

Squarely Scribe's, by its own already-written charter — no investigation needed the way
[[bmad-method-core-upgrade]] needed one. Scribe's Dream states outright: "what the team
knows, every agent and every session knows... knowledge is lossy; the graph is there;
nobody writes it down." A raw session transcript IS exactly the un-written-down knowledge
that Dream already claims as its territory; this is a depth extension of `scribe capture
--promote`'s already-shipped mechanism (mine one layer deeper) and a new named source for
the not-yet-built Epic 2 compile step, not a new station or a new charter.

### What it looks like when real

- `scribe capture --promote` (or a sibling verb) gains a mode that scans raw session
  transcripts, not just curated personal memory — proposing candidate team-relevant facts
  it finds THERE that never made it into a curated entry, with the same proposal-then-
  confirm discipline the existing promote path already uses (never silently promotes).
- Epic 2's compile step, when built, lists session transcripts as a named source alongside
  git history/memlogs/retros/CHANGELOGs — so `scribe recall` can eventually answer "what did
  we discuss about X" even when X was never curated by any agent in the moment.
- A contributor (human or agent) can ask "did we already talk about this" and get a real
  answer grounded in what was actually said, not just what someone remembered to write down
  — closing the exact loss mode [[sentinel]] originally diagnosed, at the layer underneath
  where Scribe currently stops.

### What is real

**Built and exercised** — *corrected 2026-09-09 (fleet readiness pass); the superseded
2026-08-15 reading was "Nothing yet. `scribe capture --promote` (Story 1.3) is real but scoped
to curated personal memory only. Epic 2 (the knowledge graph this would extend) is entirely
backlog — 4 of 4 stories, untouched."*

`transcripts.py` (506 lines) mines raw `.jsonl` sessions for un-curated decisions and routes
every candidate through `promote.py`'s proposal-then-confirm gate; `compile.py` carries the same
scan as a named sixth surface (`compile.py:114-117`, `:174-196`), with `transcript:` provenance
citations. Epic 2 is `done` (4/4) and Epic 3 is `done` (3/3). Proof of a real run:
`.claude/data/pyforge-scribe/transcript-scan-cache.json`, alongside a 1.67 MB `graph.json`.

The live surface has outgrown this Dream's own measurement — **27 files / 631 MB** as recorded
for DW-FU-3-2-2, not the "22 files / 161 MB" quoted above and in § *The Dream* — which is
exactly why Story 3.3 added a file-count cap, a total-byte budget (newest files first) and a
per-file timeout before putting the scan on the unattended nightly path.

### Constraints

- Air-gapped by construction, same as the rest of Scribe — no outbound calls, matching the
  existing capture/compile/recall discipline.
- Must not raw-dump transcript content into team memory — 161MB of tool-call noise across
  22 sessions needs the SAME curation discipline the existing `--promote` path already has
  (propose, don't silently promote; team-voice rewrite; provenance citation), not a bigger,
  noisier version of the same problem it's trying to solve.
- Provenance matters more here, not less — a fact recovered from a raw transcript needs to
  cite which session/turn it came from, the same way the existing mechanism's "every graph
  node traces back to the source file or commit" already requires for committed sources.

### Non-goals

- Not re-scoping Epic 1/2's own already-planned sequencing — this is a new source for the
  SAME planned compile step, not a reason to reorder Scribe's existing backlog.
- Not a real-time/live transcript-watching capability — mining PAST transcripts (a sweep,
  or an on-demand `--promote`-style scan), not live capture during an active session (that's
  what `scribe capture` already does, from the agent's own in-session judgment).

### Kinships

[[pyforge-scribe]] (owner, the charter this Dream extends) · [[pyforge-scribe-team-memory]]
· [[sentinel]] (the original knowledge-loss diagnosis this closes one more layer of) ·
[[dashboard-velocity-captures-hand-driven-work]] / [[bmad-method-core-upgrade]] (captured
the same session this gap itself was noticed, from the same underlying observation: things
discussed but not carried forward).

### Realization log

- **2026-08-15** — Dream captured. Surfaced when the user asked how to scan across all
  prior Claude session memory for pyforge-related content, noting conversational ideas get
  lost when not explicitly saved. Investigation confirmed raw transcripts exist and are
  greppable (22 files, 161MB, this repo's own personal-memory directory) but nothing scans
  them systematically — `scribe capture --promote` only reaches curated personal memory, one
  layer up from where this gap actually lives. Folded into Scribe's own territory per the
  user's explicit direction, rather than treated as a one-off sweep.
- **2026-09-09 (fleet readiness pass — REALIZED)** — `specified → realized`. Epic 3 closed 3/3
  and the criterion is *exercised*, not merely built: the scanner has actually run against this
  machine's transcript store, and `.claude/data/pyforge-scribe/transcript-scan-cache.json`
  (10 KB, 2026-08-27) is the artifact only a real scan produces. The Spec's one open question —
  "incremental by transcript mtime **vs** full sweeps" — was answered as **both**: an
  mtime+size-keyed cache for the incremental half and a triple bound (file-count cap, byte
  budget selecting newest-first, per-file timeout) for the sweep half, sized against the live
  27-file / 631 MB surface rather than this Dream's stale 22-file / 161 MB figure
  (`transcripts.py:25-43`). `spec-scribe-mines-raw-session-transcripts` moves `ready → shipped`
  in the same pass. **One contract collision surfaced and is proposed for amendment upstream:**
  `spec-pyforge-scribe`'s Non-goal — "Scribe never passively mines chat logs, Slack, **or
  session transcripts** for decisions … permanently" — reads as a blanket prohibition this
  Dream's shipped work contradicts; the distinction that actually holds is *ambient* vs
  *deliberate-and-human-gated*, and the Non-goal should be re-worded to say so rather than left
  to be read as a live veto. Recorded on that Spec's memlog this date. **Residual:** the scan is
  invoked by hand — the unattended path exists but no schedule is installed, so "routine
  promotion sweeps" in the Success signal is still aspirational; vessel is scribe **Epic 8**
  (fleet-readiness decision batch 2026-09-09, row C6).

## 2026-10-26 — How-tos and the library catalog are in the graph; the rest of docs/ is not (folded from scribe-named-docs)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 28.1). The body below is `docs/dreams/scribe-named-docs.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/scribe-named-docs.md`.*

## How-tos and the library catalog are in the graph; the rest of docs/ is not

### The Dream

Active Dreams already compile. Agents still ask “which pixi task?” and
“is this library in the catalog?” Those answers live in named Diátaxis
how-tos and in `library-llms-full.md`. Opening `docs/**` would drown
recall in dreams, legacy specs, governance, intake, and explanation
novels.

The Dream is **named extras only**. How-to guides join as ordinary
`doc` nodes. The library catalog joins as a heading extract — the 73k
file stays SoT on disk.

### What it looks like when real

- `docs/how-to/pixi-tasks.md` compiles as one `doc:` node with its
  body (each how-to is small).
- `docs/how-to/README.md` does not.
- `docs/reference/library-llms-full.md` compiles as a pointer whose
  text lists the `##` sections and does not contain a unique sentence
  from the catalog body.
- `docs/explanation/`, `docs/tutorials/`, `docs/specs/`,
  `docs/governance/` stay out.
- A missing `docs/how-to/` or missing catalog file is zero extra nodes
  and no warning.

### Constraints / Non-goals

- Never `docs/**`. Dreams stay on the existing CAP-3 surface.
- Do not ingest the wholesale library catalog body.
- Do not add cocoindex to compile. Do not open CAP-8 graphify targets.

### Kinships

[[pyforge-scribe]] · [[scribe-knowledge-layers]] ·
[[scribe-planning-pointers]]

### Realization log

- **2026-09-13** — Hoisted parked CAP-13. Spec
  `spec-scribe-named-docs`; Epic 14 Story 14.1.

## 2026-10-26 — Where is the PRD?" is a pointer, not forty-six thousand tokens (folded from scribe-planning-pointers)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 28.1). The body below is `docs/dreams/scribe-planning-pointers.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/scribe-planning-pointers.md`.*

## "Where is the PRD?" is a pointer, not forty-six thousand tokens

### The Dream

Folder SPECs and in-flight story specs already compile. The planning
novels — Brief, PRD, Architecture spine, `epics.md` — do not. An agent
asking where the PRD lives should get a path, a status, and the FR/AD
list. Serving the wholesale body recreates the token failure Marshal
already forbids (`*prd*` / `*epic*` loads).

The Dream is **pointer or extract**. One `doc` node per named artifact.
Title, path, status. FR / AD / epic-and-story headings when they are
there. Never the prose.

### What it looks like when real

- `planning-artifacts/prds/<chain>/prd.md` compiles as a pointer whose
  text names `FR-1` … and never contains a unique sentence from the
  body.
- Canonical `epics.md` compiles the same way (Epic / Story headings
  only). `epics-<chain>.md` stays out.
- Architecture is the spine (`ARCHITECTURE-SPINE.md` or a root
  `architecture.md`), not the adjacent novels.
- A missing planning tree is zero nodes and no warning.

### Constraints / Non-goals

- Do not ingest wholesale PRD / epics / architecture bodies.
- Do not compile research, addenda, test-architecture, or folder
  `SPEC.md` here (already CAP-3 / CAP-6).
- Do not add cocoindex to compile. Do not open `docs/**`.

### Kinships

[[pyforge-scribe]] · [[scribe-knowledge-layers]] ·
[[scribe-in-flight-story-specs]] · [[marshal-token-economy]]

### Realization log

- **2026-09-13** — Hoisted parked CAP-7. Spec
  `spec-scribe-planning-pointers`; Epic 13 Story 13.1.

## 2026-10-26 — Every recall door uses the same default bag (folded from scribe-portal-recall-defaults)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 28.1). The body below is `docs/dreams/scribe-portal-recall-defaults.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/scribe-portal-recall-defaults.md`.*

## Every recall door uses the same default bag

### The Dream

`AGENTS.md` already tells a session to run `scribe recall` without
`--kind`. The portal job and Marshal planning-graph already shell that
CLI. Nothing locks them to inherit CAP-4. A future argv tweak could
pass `--kind code` and put graphify back in the default bag. Cursor
only has the Dream-tier rule; it does not name recall.

The Dream is **one default at every door**. Portal `scribe/recall` and
Marshal `scribe recall` do not pass `--kind`. Cursor has a thin always-on
rule that points at the AGENTS session path. No portal redesign.

### What it looks like when real

- `_grammar_recall` argv is `scribe recall <query>` (or `pyforge scribe
  recall <query>`), never `--kind`.
- `render_scribe_recall_argv` may add `--scope` only.
- `.cursor/rules/scribe-recall.mdc` points at `AGENTS.md` § Scribe recall.

### Constraints / Non-goals

- Do not redesign django-scribe UI. Do not invent recall modes (CAP-11).
- Do not import `pyforge.scribe` from the portal.

### Kinships

[[pyforge-scribe]] · [[scribe-knowledge-layers]]

### Realization log

- **2026-09-13** — Hoisted parked CAP-12. Spec
  `spec-scribe-portal-recall-defaults`; Epic 12 Story 12.1.
- **2026-09-13** — CAP-1 realized in Story 12.1.

## 2026-10-26 — Planning retrieve names --mode planning (folded from scribe-recall-mode-wiring)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 28.1). The body below is `docs/dreams/scribe-recall-mode-wiring.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/scribe-recall-mode-wiring.md`.*

## Planning retrieve names --mode planning

### The Dream

`--mode planning|memory|code` exists on the CLI. Marshal retrieve and
session agents still inherit the default bag, so planning questions
compete with memory and commits. Portal Story 12.1 locked “no
`--kind`” and left modes out on purpose.

The Dream is **wired modes**. Marshal planning-graph retrieve always
passes `--mode planning`. Session agents use `--mode planning` for
decisions. Portal may pass `--mode` from the payload; it does not
invent `--kind`.

### What it looks like when real

- `render_scribe_recall_argv` includes `--mode planning`.
- It still never includes `--kind`.
- It never defaults to `--mode code`.
- `AGENTS.md` session path shows `--mode planning` on the decision
  command.

### Constraints / Non-goals

- Do not change internal `answer(..., mode=)` lexical/semantic.
- Do not make semantic ranking the default.
- Portal stays optional-mode, not forced planning.

### Kinships

[[pyforge-scribe]] · [[scribe-recall-modes]] ·
[[scribe-portal-recall-defaults]]

### Realization log

- **2026-09-13** — Specified as `spec-scribe-recall-mode-wiring`. Story
  18.1 wires Marshal retrieve and the session decision command.

## 2026-10-26 — Ask for planning, memory, or code without inventing --kind bags (folded from scribe-recall-modes)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 28.1). The body below is `docs/dreams/scribe-recall-modes.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/scribe-recall-modes.md`.*

## Ask for planning, memory, or code without inventing --kind bags

### The Dream

`--kind` is enough for CAP-4 (default omits `code:`). Agents and the
portal still invent argv when they want “just the planning tree” or
“just team memory.” Three named modes — `planning`, `memory`, `code` —
are the PyForge wiring shape.

Internal ranking stays `lexical` / `--semantic`. Those are not these
modes.

### What it looks like when real

- `scribe recall "…" --mode planning` only scores `doc` and `memlog`.
- `--mode memory` only scores `memory`.
- `--mode code` only scores `code`.
- No `--mode` and no `--kind` is still the CAP-4 default bag.
- `--mode` and `--kind` together exit 2.
- Unknown `--mode` exits 2.

### Constraints / Non-goals

- Do not change portal argv in this story (CAP-12 already locks no
  `--kind`).
- Do not replace Marshal `codegraph.db` (CAP-14).
- Do not make semantic ranking the default.

### Kinships

[[pyforge-scribe]] · [[scribe-knowledge-layers]] ·
[[scribe-portal-recall-defaults]]

### Realization log

- **2026-09-13** — Hoisted parked CAP-11. Spec
  `spec-scribe-recall-modes`; Epic 16 Story 16.1.

## 2026-10-26 — Yesterday's graph withholds today's commit (folded from scribe-recall-stale-between-nightlies)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 28.1). The body below is `docs/dreams/scribe-recall-stale-between-nightlies.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/scribe-recall-stale-between-nightlies.md`.*

## Yesterday's graph withholds today's commit

### The Dream

A full rebuild flags stale only when the source commit is newer than
that compile's clock. After 02:30 the stored `stale` bit stays false.
Someone lands a decision at noon. Recall still serves last night's
node as current until the next nightly.

The Dream is **recall-time stale**. The store remembers `compiled_at`.
Recall withholds a current node whose source file has a git commit
authored after that stamp. The next nightly rewrite resets the stamp.

### What it looks like when real

- `graph.json` carries `compiled_at`.
- After a post-compile commit to a cited file, `scribe recall` does
  not return that node until the graph is compiled again.
- Commit and transcript nodes stay exempt (no git-trackable file).
- A store without `compiled_at` (older file, PG/plane) keeps today's
  compile-time bit only.

### Constraints / Non-goals

- Do not re-run a full compile on every recall.
- Do not git-log every node up front — check candidates at selection.
- Do not change compile-time CAP-1.

### Kinships

[[pyforge-scribe]] · [[scribe-knowledge-layers]]

### Realization log

- **2026-09-13** — Hoisted parked CAP-9. Spec
  `spec-scribe-recall-stale-between-nightlies`; Epic 11 Story 11.1.
- **2026-09-13** — CAP-1 realized in Story 11.1.

## 2026-10-26 — Sentinel — the AI Software Factory (the ancestor) (folded from sentinel)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 28.1). The body below is `docs/dreams/sentinel.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/sentinel.md`.*

## Sentinel — the graph is the product

### The Dream

The ancestor dream (2026-04-18/19, predating the PyForge model): **Sentinel,
the AI Software Factory.** Its diagnosis — an engineer touches six tools in the
first hour; the knowledge the team runs on (the *why* of code X, rejected
tradeoffs, the 3am runbook) is scattered and lossy; AI without the graph
hallucinates; knowledge-base products sell a better editor when the bottleneck
is the round-trip. Its thesis, four properties:

1. **The graph is the product** — every artifact a node, every reference an
   edge, compiled nightly from the tools the team already uses.
2. **The floor is agentic** — five specialist agents (Analyst, Architect,
   Developer, QA, PO), each owning one shift.
3. **The audit is the contract** — every LLM call an OTel GenAI span, every
   data move an OpenLineage event, every story closed with cited evidence.
4. An **all-local / WASM / air-gapped branch** — the factory where the internet
   isn't.

### What exists (stranded in Design, to be repatriated)

Design project *"LLM Knowledge Bases"* (`fca0375d-…`): Build-Spec **v2.1**
(764 lines, BMAD-METHOD v6.3.x, "Ready for Implementation", Apache-2.0 license
bar), engineering + stakeholder decks, five airgap/WASM audits, the LLM
Knowledge Bases deck (origin: a 2026-04-18 essay on LLM-powered personal
knowledge bases), and an **unshipped `COMMIT_MSG.txt` + `PR_BODY.md`** — the
effort was ready and never landed. Repatriation via the bridge is the first
realization step.

### Lineage — what the descendants took

- Five agents → the six-persona **[[pyforge-charter]]**.
- §19 Kedro · §20 Dagster · §27 BSL · §24 OTel/OpenLineage · §26 La Suite →
  **[[pyforge-atlas]]**'s shipped stack, to the letter.
- Audit-as-contract → **[[pyforge-warden]]** + [[pyforge-marshal]]'s gates.
- §40 Airgap Bundle · license bar · WASM branch → **[[enterprise-airgap]]**.
- The knowledge problem, first organ → **[[team-memory]]**.
- Its design-tokens pipeline (Figma↔JSON↔POTX) → **[[pyforge-herald|modernist-identity]]** /
  **[[pyforge-herald|deckcraft]]**.

**The unbuilt core**: the team knowledge graph compiled nightly from real tools.
That remains this Dream's open claim — **owned, as of 2026-07-23, by the Scribe**
([[pyforge-scribe]]), the persona the crew adopted to carry it.

### Realization log

- **2026-07-25** — **ARCHIVED (absorbed).** The persona's charter passed to
  [[pyforge-scribe]] (*"the graph is the product"*), and the unbuilt
  knowledge-graph core lives on as `src/sentinel/**`, allowlisted in
  `spec_surface_check` until Scribe absorbs it. Archived here rather than left
  in Backlog: it was appearing in **both** places at once — a live `dreamt`
  Dream *and* a hardcoded Archived entry.

- **2026-04-18/19** — essay → decks → Build-Spec v2.1; never landed in a repo.
- **2026-07-23** — rediscovered during the Design-workspace audit; Dream seeded;
  descendants credited.
- **2026-07-23 — evidence repatriated** via the bridge: the never-shipped
  `COMMIT_MSG.txt` (full 39-ADR ledger) + `PR_BODY.md` land in
  `docs/intake/sentinel/` with a provenance README recording etags for every
  deferred artifact (the 764-line Build-Spec pulls byte-exact on activation;
  decks stay Design-native; tokens pipeline lands with deckcraft's intake).
- **2026-07-23 (gist audit)** — the origin essay surfaced: `docs/intake/gists/llm-powered-knowledge-bases-by-andrej-karpathy/` (the Karpathy piece the 2026-04-18 deck was built from).

## 2026-10-26 — Team memory — what the team knows, the agents know (folded from team-memory)

*Folded 2026-10-26 under spec-one-chain-per-station CAP-11 (Story 28.1). The body below is `docs/dreams/team-memory.md`, verbatim, with its headings demoted one level and its 2026-09-17 fold banner left out; the file moved to `archive/docs/dreams/team-memory.md`.*

> **Superseded.** This Dream carried Scribe's shared, version-controlled
> memory layer as a standalone contract — MEM-1 (memory is committed, not
> personal), MEM-2 (recall is scoped, not a dump), MEM-3 (entries carry
> provenance, so a stale one is visibly stale) — inherited from [[sentinel]]'s
> knowledge-graph core when that Dream was absorbed 2026-07-25.
> [`docs/dreams/pyforge-scribe.md`](pyforge-scribe.md) (status: specified)
> now carries this scope directly: MEM-1 is `spec-pyforge-scribe`'s CAP-1
> (`scribe capture` / `--promote` into `.claude/memory/`) plus AD-1
> (append-only, git-committed); MEM-2 is CAP-3's grounded, cited `scribe
> recall <query>`; MEM-3 is CAP-2's per-node source/commit traceability plus
> the Non-goals' compile-time staleness signal. The legacy 10-story
> `docs/specs/claude-team-memory.md` spec this Dream pointed to was already
> absorbed as Scribe's Wave 1 foundation on 2026-07-25; Epic 1 is now 3 of 5
> stories shipped (1.1 package scaffold + capture, 1.2 `CLAUDE.md` wiring,
> 1.3 promotion workflow) and `.claude/memory/` is live in this repo today.
> Consolidated into one Dream 2026-08-02 rather than left as a second live
> contract for the same surface. See `spec-team-memory` for the retirement
> record.

## Team memory — memory that belongs to the team, not one session

**Owning station: the Scribe** ([[pyforge-scribe]], adopted 2026-07-23).

### The Dream

Today's memory is personal: each operator's auto-memory lives outside the repo,
invisible to teammates and to other agents. The dream is a **shared,
version-controlled memory layer** — `.claude/memory/` in the repo itself — where
corrections, conventions, and hard-won context accumulate as team property: any
agent, any operator, any session starts already knowing what the team knows.

### What it looks like when real

- A `.claude/memory/` tree + a `team-memory` skill governing recall, writes,
  dedup, and hygiene (10 waved stories in the spec).
- Clean division: personal memory for personal preference; team memory for team
  truth; Dreams ([[pyforge-charter]]) for aspirations; specs for contracts.
- The distillation pipeline (retros, CHANGELOG, memories) feeding one shared
  brain instead of per-operator silos — the practical antidote to the
  "knowledge is lossy" problem [[sentinel]] diagnosed.

### What is real

- Spec ready: `docs/specs/claude-team-memory.md` (10 waved stories, unstarted).
- The *personal* pipeline it generalizes is mature: 30+ auto-memory entries,
  MEMORY.md indexing, retro discipline.

### Realization log

- **2026-07** — spec authored (ready).
- **2026-07-23** — Dream retro-seeded. Kinship: [[sentinel]] dreamed the team
  knowledge graph at product scale; team-memory is the pragmatic first organ.
