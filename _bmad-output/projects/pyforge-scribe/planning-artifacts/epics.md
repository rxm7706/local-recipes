---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/prds/prd-pyforge-scribe-2026-07-25/prd.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/prds/prd-pyforge-scribe-2026-07-25/addendum.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/architecture/architecture-pyforge-scribe-2026-07-25/ARCHITECTURE-SPINE.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/briefs/brief-pyforge-scribe-2026-07-25/brief.md
  - docs/specs/claude-team-memory.md
mode: headless-express — no interactive elicitation; epic/story structure drafted directly from the PRD's Wave 1/Wave 2 split and the architecture spine's module breakdown
---

# pyforge-scribe - Epic Breakdown

## Overview

Complete epic and story breakdown for **pyforge-scribe** (Scribe) — a real, installable package (dist `pyforge-scribe`, module `pyforge.scribe`, CLI `scribe`) that captures decisions as they happen, compiles them nightly into a knowledge graph built from the tools the team already uses, and answers from that memory so every session starts already knowing what the team knows. Decomposed from the completed PRD (**FR-1–FR-15**, 4 features) and the completed architecture spine (9 ADs, event-sourced-capture/CQRS-lite paradigm, `pyforge-warden`-precedent packaging). **No UX design contract** — Scribe is a non-interactive CLI product (like its shipped sibling `pyforge-warden`); human-facing affordances (grounded citations, proposal-then-confirm review) are owned as FRs, not UX artifacts. Epics are **vertical slices that ship end-to-end value**, matching the PRD's own Wave 1/Wave 2 split exactly — Wave 1 (team memory) is complete and useful standalone; Wave 2 (graph compile + recall) builds on it but is independently the product's other half of value.

## Requirements Inventory

### Functional Requirements

**A. Capture & Promotion (Wave 1 — the team memory layer)** — FR-1 frontmatter schema parity with user-local auto-memory · FR-2 `MEMORY.md` index stays under 200 lines (convention-only) · FR-3 proposal-then-confirm promotion (no auto-commit) · FR-4 team-voice rewrite required (no verbatim copy) · FR-5 pointer stub left in user-local memory after promotion (never deleted) · FR-6 idempotent detection of already-promoted entries (`promoted: true`) · FR-7 write-boundary discipline (Scribe never writes outside `.claude/memory/`, its own package/graph-store paths, and the one pointer-stub exception) · FR-8 type taxonomy match (`feedback`/`project`/`reference`).

**B. Graph Compile (Wave 2 — the unbuilt core)** — FR-9 nightly compile reads named tool surfaces (`.claude/memory/`, `.memlog.md` files, git history, retros, CHANGELOGs, `docs/dreams/`) · FR-10 fact supersession, never deletion, when a capture supersedes a prior record · FR-11 compile is unattended and idempotent.

**C. Recall (Wave 2 — the answer surface)** — FR-12 recall returns a grounded, cited answer (or an explicit "no grounded answer found") · FR-13 recall is queryable identically by any session/operator/agent worktree (the graph is shared, not per-session state).

**D. Package & CLI Surface (cross-cutting, both waves)** — FR-14 the CLI (`scribe capture` / `scribe graph compile --nightly` / `scribe recall`) is the sole public contract · FR-15 pixi workspace membership, matching the shipped `pyforge-warden` packaging precedent.

### NonFunctional Requirements

- **Air-gap posture (cross-cutting; PRD SM-5, architecture AD-6):** zero required network reachability by default for `scribe capture`, `scribe graph compile`, or `scribe recall`. Any future network-touching capability is opt-in, off by default, explicitly flagged.
- **Manual-only invocation (Wave 1/2; PRD §4.1 feature NFR, inherited legacy FR-9):** no `Stop`/`SessionEnd`/`PreCompact` hook triggers capture — every invocation is deliberate.
- **No recall-accuracy benchmark claim (Wave 2; PRD §4.3 feature NFR):** `scribe recall` does not claim LoCoMo/LongMemEval parity with Mem0/Zep; differentiation is groundedness + citation, not raw retrieval score.
- **Versioning (cross-cutting; PRD §4.4 feature NFR):** semver; CLI subcommand additions are MINOR, breaking flag/output-format changes are MAJOR.

### Additional Requirements

*From the architecture spine (§ Invariants & Rules, § Structural Seed) — these shape the epic/story design:*

- **Greenfield scaffold does not yet exist.** Unlike `pyforge-warden` (which had a pre-existing stub), Epic 1 Story 1 creates `src/shared/packages/pyforge-scribe/` from scratch, following the `pyforge-warden` precedent exactly (hatchling backend, `pixi-build-python` member, `src/pyforge/scribe/` namespace package, `[project.scripts] scribe = "pyforge.scribe.cli:main"`).
- **The `GraphStore` port (AD-5) is established once, in Wave 2's first story**, not re-derived per story — `compile.py` and `recall.py` both depend on it. The concrete v1 adapter is the flat-file/index model extending `.claude/memory/MEMORY.md`'s existing pattern (lowest-risk default per the architecture's Deferred section — the embedded-graph-engine question stays genuinely open past this story breakdown; a later story may swap the adapter without touching `compile.py`/`recall.py` callers, by AD-5's own rule).
- **Cross-cutting acceptance gates applied to every story** (not a single "do security/air-gap" story): **AD-1** (append-only capture is the only mutation path — no story may hand-edit a compiled graph or a `.claude/memory/` entry outside `capture.py`/`promote.py`) · **AD-2** (write-boundary — a story touching anything outside its own FR's declared write path is out of scope) · **AD-6** (air-gap — any new code path that could reach the network is opt-in and gated, checked in each story's ACs where relevant) · **AD-8** (recall never fabricates a citation — binding on every Epic 2 recall-facing story).
- **Wave boundary discipline (AD-9):** Epic 2 stories read Epic 1's `.claude/memory/` frontmatter as a stable input contract; no Epic 2 story may require reformatting Epic 1's already-shipped entries.

### UX Design Requirements

**N/A** — non-interactive CLI, matching the `pyforge-warden` precedent. `scribe capture --promote`'s proposal-then-confirm review is a CLI/terminal interaction owned by FR-3, not a UX artifact.

### FR Coverage Map

`FR-1, FR-2, FR-3, FR-4, FR-5, FR-6, FR-7, FR-8, FR-14, FR-15` → **Epic 1** (Team Memory: Capture & Promotion) · `FR-9, FR-10, FR-11, FR-12, FR-13` → **Epic 2** (Knowledge Graph: Compile & Recall). All 15 FRs covered. FR-14/FR-15 (CLI contract, pixi membership) are established in Epic 1 Story 1.1 as the walking-skeleton scaffold — matching the `pyforge-warden` precedent of establishing the shared spine inside the first vertical slice rather than as a separate "infrastructure" epic (which the epic-design principles explicitly forbid).

## Epic List

*Two vertical-slice epics, matching the PRD's own Wave 1/Wave 2 split exactly — each is standalone and independently valuable; Epic 2 builds on Epic 1's `.claude/memory/` tree as one input (AD-9) but does not require any future epic.*

### Epic 1: Team Memory — Capture & Promotion
A developer (human or agent) captures a decision once, at the moment it's made, and it becomes visible to every teammate and every agent session from then on — fixing the concrete, dated pain (the `d43899c1cb` duplication incident) without waiting for the graph to exist. Establishes the `pyforge-scribe` package/CLI scaffold as part of delivering this slice, not as separate infrastructure work.
**FRs covered:** FR-1, FR-2, FR-3, FR-4, FR-5, FR-6, FR-7, FR-8, FR-14, FR-15

### Epic 2: Knowledge Graph — Compile & Recall
A developer or agent, in any session, asks "why did we do X" and gets a grounded, cited answer — compiled nightly from the team's real tools (team memory, git history, memlogs, retros), not reconstructed from code archaeology or guessed by an LLM. This is Sentinel's previously-unbuilt core, finally shipped.
**FRs covered:** FR-9, FR-10, FR-11, FR-12, FR-13

**Recommended build order:** `1.1 → 1.2 → 1.3 → 1.4 → 1.5 → 2.1 → 2.2 → 2.3 → 2.4`. Epic 1 delivers standalone value at 1.2 (capture + visibility) and completes its promotion loop at 1.5 (seed-promotion proof, matching the legacy spec's Story 6 requirement that the seed promotion be performed *by invoking the tool*, not by hand). Epic 2 cannot start meaningfully before Epic 1 ships, since 2.2's compile step reads `.claude/memory/` as one of its named tool surfaces (AD-9).

---

## Epic 1: Team Memory — Capture & Promotion

A developer (human or agent) captures a decision once, at the moment it's made, and it becomes visible to every teammate and every agent session from then on. Realizes UJ-1, UJ-4. Absorbs the legacy `claude-team-memory` spec's full 10-story scope (Waves A/B/C), reshaped per the architecture's AD-1/AD-2/AD-3.

### Story 1.1: Package scaffold + direct capture into team memory

As a developer working in this repo,
I want a `scribe` CLI that scaffolds the `pyforge-scribe` package and lets me capture a decision directly into `.claude/memory/`,
So that I can record a decision the moment I make it, without a separate app or context switch.

**Acceptance Criteria:**

**Given** the repo has no `src/shared/packages/pyforge-scribe/` directory yet
**When** the package is scaffolded per the architecture's Structural Seed
**Then** `src/shared/packages/pyforge-scribe/pyproject.toml` exists with a hatchling backend and `[project.scripts] scribe = "pyforge.scribe.cli:main"`, `src/pyforge/scribe/` contains `cli.py` (typer app with three stub/real subcommands matching FR-14), and the root `pixi.toml` gains a `[feature.pyforge-scribe.dependencies]` + at least one test task, mirroring the `pyforge-warden` precedent exactly (AD-7, FR-15).

**Given** `.claude/memory/` does not yet exist in the repo
**When** Story 1.1 lands
**Then** `.claude/memory/` is scaffolded with `feedback/`, `project/`, `reference/` subdirectories (each committed, e.g. via `.gitkeep`), a starter `MEMORY.md` index (empty sections, header documenting the 200-line convention per FR-2), and a `README.md` documenting the schema and the team-relevance test — matching the legacy spec's Story 1/Story 8 acceptance criteria.

**Given** a developer runs `scribe capture --type decision --text "ADR-005b: in-house gateway replaces LiteLLM"`
**When** the command completes
**Then** a new file lands under `.claude/memory/feedback/` (or the type-matching subdirectory per FR-8) with frontmatter matching the user-local auto-memory schema exactly (`name`, `description`, `type` — FR-1), and `MEMORY.md` gains a one-line index entry for it.

**And** no file outside `.claude/memory/` and the Scribe package's own source tree is written by this command (FR-7, AD-2).

### Story 1.2: `CLAUDE.md` wiring — team memory loads automatically

As every developer working in this repo,
I want `CLAUDE.md` to import `.claude/memory/MEMORY.md`,
So that captured team-memory entries are visible in every session without extra setup.

**Acceptance Criteria:**

**Given** Story 1.1 has scaffolded `.claude/memory/MEMORY.md`
**When** a short `## Team Memory` section with `@.claude/memory/MEMORY.md` is added near the end of root `CLAUDE.md` (human-edited, per FR-7's boundary — Scribe's own CLI does not perform this edit)
**Then** a fresh Claude Code session in the repo has the index content in context, verifiable by asking Claude to "list every entry currently in team memory."

**Given** the legacy `claude-team-memory.md` spec's Q3 (de-duplication of the `## BMAD ↔ conda-forge-expert integration` section) defaulted to "remove — single source of truth in `.claude/memory/`"
**When** this story lands and Epic 1's seed promotion (Story 1.5) has populated the two BMAD↔CFE entries
**Then** the CLAUDE.md section is either removed in favor of the `@import`, or reduced to a one-line pointer, per the PRD's `[NOTE FOR PM]` — the specific resolution is a human review decision made in this story, not automated.

### Story 1.3: Promotion workflow — proposal-then-confirm, team-voice rewrite

As a developer,
I want `scribe capture --promote` to scan my user-local auto-memory, propose which entries are team-relevant, and rewrite them in team voice,
So that team-relevant rules move into version control deliberately, with review, never silently.

**Acceptance Criteria:**

**Given** a developer runs `scribe capture --promote`
**When** the command reads `~/.claude/projects/<encoded-path>/memory/` and classifies each entry as team-relevant / personal / already-promoted / stale (per the legacy spec's team-relevance test — "would a day-1 contributor benefit from this rule?")
**Then** it produces a structured proposal (files to write, full content, updated `MEMORY.md`) and halts — no file under `.claude/memory/` changes on disk until explicit confirmation (FR-3).

**Given** a user-local entry is classified team-relevant
**When** the proposal drafts its promoted form
**Then** the drafted content strips first-person phrasing, drops "user prefers" framing, drops incident-specific anecdotes, and preserves file paths/commands/identifiers verbatim (FR-4) — never a byte-identical copy of the source entry.

**And** a clearly personal entry (e.g., a terseness/tone preference) is classified `personal` and excluded from the proposal, not silently promoted.

### Story 1.4: Pointer-stub write-back + idempotent re-invocation

As a developer,
I want a promoted user-local entry replaced with a pointer stub, and re-running the promotion command to skip already-promoted entries,
So that promotion is traceable and safe to re-invoke without duplicating work.

**Acceptance Criteria:**

**Given** a promotion proposal from Story 1.3 has been confirmed
**When** the confirmed writes execute
**Then** each promoted user-local entry is rewritten to the pointer-stub format (`promoted: true` frontmatter + a redirect body naming the promoted file's path and an ISO `YYYY-MM-DD` date) — the original body content is not preserved in user-local memory after promotion (FR-5).

**Given** `scribe capture --promote` is re-invoked after a successful promotion
**When** it re-scans user-local memory
**Then** entries carrying `promoted: true` are classified `already-promoted` and skipped — no re-proposal, no re-write (FR-6).

**And** nothing outside `.claude/memory/` and the specific promoted user-local entry's pointer-stub rewrite is touched by this command (FR-7).

### Story 1.5: Seed promotion — the end-to-end proof

As the repo owner,
I want the two existing BMAD↔CFE feedback rules promoted as Epic 1's seed content, performed by invoking `scribe capture --promote` itself,
So that Epic 1's promotion loop is proven against real entries, not synthetic ones.

**Acceptance Criteria:**

**Given** Stories 1.1–1.4 are complete
**When** `scribe capture --promote` is invoked against the real user-local entries `feedback_bmad_uses_cfe_skill.md` and `feedback_bmad_runs_cfe_retro.md`
**Then** both are classified team-relevant, proposed, confirmed, and written to `.claude/memory/feedback/` in team voice, `MEMORY.md` lists both with one-line hooks, and both source user-local entries become pointer stubs — matching the legacy spec's Story 6/AC-4/AC-5 exactly.

**And** the promotion is performed by the tool, not authored by hand — the story is complete only when the CLI workflow itself produces the diff that gets committed (legacy spec Story 6's binding requirement, carried forward unchanged).

---

## Epic 2: Knowledge Graph — Compile & Recall

A developer or agent asks "why did we do X" and gets a grounded, cited answer, compiled nightly from the tools the team already uses. Realizes UJ-2, UJ-3. This is the previously-unbuilt core the Sentinel Dream diagnosed in 2026-04 and nobody owned until Scribe.

### Story 2.1: `GraphStore` port + flat-file v1 adapter

As the Scribe package,
I want a `GraphStore` protocol with a flat-file/index concrete adapter,
So that `compile.py` and `recall.py` have a stable seam to build against, without committing to an embedded graph-database engine before it's justified.

**Acceptance Criteria:**

**Given** no graph storage exists yet
**When** `graph_store.py` is implemented per the architecture's AD-5
**Then** a `GraphStore` protocol defines write operations (an upsert-node-shaped call, an invalidate-edge-shaped call for supersession) and read operations (query-by-citation-path), and a concrete flat-file/index adapter (extending `.claude/memory/MEMORY.md`'s existing pattern, per the architecture's Deferred note) implements it — no other module imports a specific storage engine's client library directly (AD-5).

**Given** the air-gap NFR (AD-6)
**When** the flat-file adapter performs any read/write
**Then** zero network calls occur — verified by a dedicated offline-conformance test (e.g., run under a network-blocked/`unshare -n`-style harness, matching this repo's `deckcraft` precedent) that is part of this story's deliverable, not deferred to a later story.

### Story 2.2: Nightly compile from named tool surfaces

As a developer or agent,
I want `scribe graph compile --nightly` to read `.claude/memory/`, `.memlog.md` files, git history, retros, and CHANGELOGs, and rebuild the graph unattended,
So that the graph reflects reality without anyone hand-maintaining a wiki.

**Acceptance Criteria:**

**Given** entries exist in `.claude/memory/`, at least one `.memlog.md` file, and recent git commit history
**When** `scribe graph compile --nightly` runs
**Then** graph nodes are produced, each traceable to its source file/commit, via the `GraphStore` port from Story 2.1 (FR-9).

**Given** the compile step is re-run with no new source activity since the last run
**When** it completes
**Then** the resulting graph state is unchanged — no duplicate nodes, no spurious edges (FR-11, idempotency).

**Given** the compile step runs on a schedule (cron/CI/manual) with no interactive input available
**When** it executes
**Then** it completes without prompting and without requiring a human present (FR-11, unattended).

**And** the compile step performs zero required network calls in its default configuration (AD-6).

### Story 2.3: Fact supersession in the compiled graph

As a developer or agent querying the graph later,
I want a decision that supersedes a prior one to invalidate — not delete — the prior record,
So that historical accuracy survives and nothing is silently lost when a decision changes.

**Acceptance Criteria:**

**Given** a capture explicitly names a prior record as superseded (e.g., a new decision replacing an earlier one)
**When** `scribe graph compile` processes it
**Then** the prior record's node remains present in the graph, marked with ended validity, rather than removed (FR-10) — conceptually the Graphiti-derived bi-temporal pattern the domain research flagged, implemented storage-engine-agnostically per AD-5.

**And** a query against the graph for the superseded record still resolves it (traceable), distinguishing it from the current/active record.

### Story 2.4: `scribe recall` — grounded, cited answers

As a developer or agent starting a new session,
I want `scribe recall "<query>"` to answer from the compiled graph with a citation to the record it's grounded in,
So that I start already knowing what the team knows, instead of guessing or re-deriving it.

**Acceptance Criteria:**

**Given** the graph (from Stories 2.1–2.3) contains a record answering a query
**When** `scribe recall "why did we drop Kùzu?"` (or an equivalent real query) is run
**Then** the response includes at least one citation resolvable to a real file/record in the repo (FR-12) — no response is returned without a resolvable citation (AD-8).

**Given** a query has no relevant graph coverage
**When** `scribe recall` is run
**Then** it returns an explicit "no grounded answer found" result rather than a fabricated or generic answer (FR-12).

**Given** two different operators, or two different concurrent agent worktrees, run the identical `scribe recall` query against the same repo state
**When** both complete
**Then** both receive the identical grounded answer — the compiled graph is the single shared source, not per-session state (FR-13).

**And** `scribe recall`'s default configuration performs zero required network calls to produce a grounded answer (AD-6, PRD Open Question 3's "no-LLM-required" v1 default).

---

## Final Validation

- **All 15 FRs covered:** FR-1 (1.1), FR-2 (1.1), FR-3 (1.3), FR-4 (1.3), FR-5 (1.4), FR-6 (1.4), FR-7 (1.1/1.3/1.4, cross-cutting), FR-8 (1.1), FR-9 (2.2), FR-10 (2.3), FR-11 (2.2), FR-12 (2.4), FR-13 (2.4), FR-14 (1.1), FR-15 (1.1).
- **No story depends on a future story within its own epic** — 1.1 → 1.2 → 1.3 → 1.4 → 1.5 and 2.1 → 2.2 → 2.3 → 2.4 are each strictly backward-dependent.
- **Epic 2 depends only on Epic 1's `.claude/memory/` tree existing** (AD-9), not on any Epic 2 story from Epic 1.
- **All 9 stories are sized for single-dev-agent completion**, matching the architecture's module breakdown (`cli.py`+scaffold, `capture.py`, `promote.py` ×2, seed-data proof, `graph_store.py`+harness, `compile.py`, supersession logic, `recall.py`).
- **UX Design Requirements:** N/A, confirmed above — no story introduces a UX gap.
- **No epic organized by technical layer** — Epic 1 and Epic 2 each deliver complete, independently-valuable user capability (capture+promotion; compile+recall), matching the PRD's own Wave framing.
