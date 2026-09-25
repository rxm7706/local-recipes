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
updated: "2026-09-25"   # RE-STAMPED 2026-09-25: chain-currency cascade (arch -> epics); Epic 21 minted (21.1, spec-python-foundry-cutover fnd:CAP-15). Prior 2026-09-20
currency_review: "Reviewed 2026-09-17 (one-chain scribe fold) — INV-A window cites spec-pyforge-scribe CAP-1..26; epic numbers unchanged. No blocked keys flipped."
# The single canonical story source for this station: every `### Story` heading
# here maps 1:1 to a sprint-status-ledger.yaml story key. Exactly one per station (marshal:AD-72).
epics_role: canonical
---

# pyforge-scribe - Epic Breakdown

## Fold provenance (2026-09-17)

Station Spec spec-pyforge-scribe reminted absorbed capabilities as CAP-1..26. Historical stories keep their sequential epic numbers (already 1..N with no gaps). This heading is the INV-A citation window: `spec-pyforge-scribe` CAP-1..26.

**2026-09-17 arch→epics validation.** Re-read ARCHITECTURE-SPINE.md after the 2026-09-17 prd→arch cascade. No AD added or changed. Story headings still map 1:1 to `sprint-status-ledger.yaml` keys. No blocked ledger keys flipped.


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

## Epic 3: Scribe reaches the raw transcripts

**Spec binding.** Decomposes `spec-scribe-mines-raw-session-transcripts` CAP-1..2
(2026-08-22; the fleet's proven highest-fidelity recovery source, systematized).

### Story 3.1: The scanner surfaces what sessions said but memory missed
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** spec-scribe-mines-raw-session-transcripts CAP-1
**Given** the repo's raw `.jsonl` transcripts (22/161MB live) **Then** promotion
CANDIDATES — discussed-never-curated decisions/facts — surface with transcript+position
provenance into the existing `capture --promote` review flow, never auto-promoted;
curated-covered content stays quiet; the scan-economics question (incremental-by-mtime vs
full) resolves here.

### Story 3.2: Transcripts join the compile sources
**Type:** feature • **Effort:** S • **Deps:** S-3.1 • **FR/AD:** spec-scribe-mines-raw-session-transcripts CAP-2
**Given** Epic 2's knowledge-graph compile source list **Then** raw transcripts register
alongside git history/memlogs/retros/CHANGELOGs/dreams with the same provenance
discipline — the next Scribe layer cannot re-miss them.

### Story 3.3: The nightly compile gets a schedule and a cost ceiling
**Type:** feature • **Effort:** M • **Deps:** S-3.2 • **FR/AD:** PRD SM-4 / FR-11 • RISK-2 (2026-08-08 technical report) • DW-FU-3-2-2 • scribe AD-6

*Minted 2026-08-27 from the SM-4 gap: the nightly compile existed as a verb but nothing
scheduled it, and the Epic 3 transcript surface made an unattended run cost-unbounded.
Scoping follows the herald Story-13.5 pattern — the CLI verb is the schedulable unit; an
opt-in, operator-installed local `crontab` entry is the trigger. GitHub Actions is
disqualified: the transcript root (`~/.claude/projects/<encoded-cwd>/`), `.claude/memory/`,
and the `.claude/data/` graph store are all operator-local, so a GH-hosted runner would
compile an empty machine every night (the same reasoning `herald/scheduler.py` and
pyforge-herald's `docs/cli-runbooks.md` record for `.herald/herald.db`) — mirror the
pattern, do NOT couple into `herald scheduler run`.*

**Acceptance Criteria:**

**Given** a transcript root of any size
**When** `scribe graph compile` (any mode) reaches the transcript surface
**Then** the scan is bounded as a precondition of unattended scheduling: a file-count cap
and a total-byte budget (newest files first) select what is read, a per-file timeout
abandons a pathological file with a warning instead of hanging the run, and an
mtime+size-keyed scan cache under the graph store's own directory makes a re-run over an
unchanged surface skip re-reading unchanged files — all bounds defaulting high enough to
cover the live 27-file/631MB surface without dropping data (closes DW-FU-3-2-2).

**Given** an operator who wants the compile nightly
**When** they follow `src/shared/packages/pyforge-scribe/docs/cli-runbooks.md` (herald
`docs/cli-runbooks.md` format)
**Then** a documented, opt-in `crontab -e` entry — path-parameterized per checkout, `cd`
to the repo root, `flock -n`-wrapped, appending to a stated log destination
(`~/.cache/scribe-nightly-compile.log`) — is the trigger; no GitHub Actions workflow is
added.

**Given** a `scribe graph compile` already running against the same graph store
**When** a second invocation starts (an overlapping cron firing, or an operator running
it by hand)
**Then** the second run skips cleanly — a non-blocking lock keyed to the store path
(mirroring `capture.py::_locked`'s stdlib flock pattern) makes it exit 0 with a
"skipped" message, never a corrupted double-write and never a red cron mail — and
FR-11's byte-identical idempotent rerun still holds with the scan cache in play.

**Given** the runbook and the bounded, guarded verb exist
**When** this story completes
**Then** PRD SM-4 flips to met with the runbook as evidence (dated notes in §7 and
§ Currency reconciliation), and the deferred-work ledger's DW-FU-3-2-2 is closed with
the same date.

## Canopy obligations (2026-08-24)

Phase 5 correct-course (`sprint-change-proposal-2026-08-24-canopy.md`, **approved**). canopy:CAP-14 graph
backend and semantic recall stay **steward Epic 28** — not a scribe-local graph epic.
**Epic 4** (later 2026-08-24) is CAP-18 `GraphStore` plugin *registration* only.

| Obligation | Owner | Notes |
|---|---|---|
| **canopy:CAP-14 / FR-35** — durable PostgreSQL/pgvector graph driver behind the existing `GraphStore` port, with the local flat-file path retained | **steward Epic 28** (S-28.1) | Scribe cooperates only: keep `compile.py` / `recall.py` caller-agnostic (scribe AD-5); schema isolation is **parent AD-1** / **parent AD-5** (`scribe_schema`). **Do not** add SQLite-over-RWX. Today's shipped backend is **`FlatFileGraphStore`** only — the unifying-strategy Dream's "already dual-driver" premise was false. |
| **canopy:CAP-14 / FR-36** — semantic recall (meaning, not only lexical overlap) | **steward Epic 28** (S-28.2) | Additive to shipped lexical recall; not a scribe-local epic. |
| **Five-tier symmetry** — portal `/stations/scribe/`, MCP service face, SKF domain skill, station persona | **steward Epics 19, 21, 29** | CLI tier exists (`scribe`; unified `pyforge scribe` via steward Epic 22). No second chrome, no extra port. |
| Scribe tracker | *This section only* | Thin cooperation note — implementation stories live in steward planning artifacts, not here. |

## Operating-model obligations (2026-08-24)

Estate-wide bind from Unifying Strategy Grounding (hooks/plugins principle + Q1–Q8)
and steward `sprint-change-proposal-2026-08-24-operating-model.md` (**§6 revisited**).
**Hooks and plugins (canopy:AD-21):** as far as possible every layer is replaceable —
the process owns hook specifications; a plugin implements or replaces a layer without
a fork. Kedro
[architecture overview](https://docs.kedro.org/en/stable/getting-started/architecture_overview/)
*names* the split; it does not require this station to be a Kedro project. Warden owns
PR-gate hook specs (Q8). This station owns its process hooks.

**Always / Never (every station):**
- Five-tier completeness is the **03** shape. 01/02 stay spec+script or spec+skill.
- Guildhall / switcher must not tile `work_class` 01 or 02 as a station.
- Golden Path: humans, CI, and agents invoke the same Pixi task names.
- CloudEvents: `spec_id` + git sha + SBOM purl; Jira optional; never fail for a missing key.
- Path B = Agent Canopy + this station's persona. Tachyon = production LLM provider adapter.
- Lane 2 = HTMX; station compute = FastAPI. No station-local DRF JSON:API on the portal.
- Design station processes as hook specs + plugins (canopy:AD-21). Do not fork a process to swap a vendor.
- **Never** a competing PR quality-gate verdict. Quality scanners register as **Warden plugins**.
- Scorecard measures are unpublished (human + agent + team; draft later). Do not optimize to invented metrics.

**Scribe-local:** Graph-store / recall-backend plugins are station hooks (Story **4.1**). Memory completeness is not a PR quality gate. canopy:CAP-14 backing-store work remains steward Epic 28.

**Pointers:** `change-history/sprint-change-proposal-2026-08-24-operating-model.md`;
`change-history/sprint-change-proposal-2026-08-24-hook-specs.md`;
steward `sprint-change-proposal-2026-08-24-hook-specs.md`; `DW-OM-2026-08-24`.

## Epic 4: GraphStore on the shared plugin contract

**FR-45.** Deps: steward S-32.1. Cooperates with steward Epic 28; does not re-own PG/pgvector.

### Story 4.1: Register GraphStore as CAP-18 plugins

As a scribe operator,
I want `FlatFileGraphStore` (and the Epic 28 PG driver) as plugins on the shared contract,
So that swapping a recall store does not fork scribe.

**Type:** feature • **Effort:** M • **Deps:** steward S-32.1 • **FR/AD:** FR-45 • canopy:AD-21
**Given** the existing `GraphStore` port **When** this story completes **Then** today's flat-file backend is the default plugin
**And** the durable PG driver (steward S-28.1) registers as a second plugin, not a fork
**And** recall completeness is not published as a PR quality-gate verdict

## Epic 5: Scribe owns remaining skill/persona and one portal job

Steward 29.1 compiled the SKF *shape* from scribe. This epic **owns** any remaining skill/persona gaps and the first portal job. Does **not** copy Canopy 18–30. canopy:CAP-14 PG driver stays steward Epic 28.

### Story 5.1: SKF skill ownership and BMAD persona for scribe

As an autonomous agent,
I want scribe's domain skill and a `bmad-agent-scribe` persona owned in this station,
So that Path B is not steward-only leftover from Epic 29.

**Type:** feature • **Effort:** M • **Deps:** S-4.1 • **FR/AD:** canopy FR-37, FR-38 • canopy:AD-17
**Given** steward 29.1 may already have compiled `pyforge-scribe` **When** this story completes **Then** the skill exists under `.claude/skills/` with scribe provenance (skip recompile if identical)
**And** the persona uses only `pyforge scribe …` and `POST /stations/scribe/mcp`

### Story 5.2: First portal slice — one recall query

As a scribe operator,
I want `/stations/scribe/` to submit one recall query and show cited results,
So that Lane 2 does a real job in HTMX.

**Type:** feature • **Effort:** M • **Deps:** S-5.1 • **FR/AD:** canopy FR-10 • canopy:AD-7
**Given** an authenticated scribe-role session **When** the operator submits a query **Then** results render via PortalClient only
**And** no raw HTTP, no `pyforge.*` under `src/platform/`, no chrome copy

## Epic 6: The compile_surface extras — graphify and cocoindex behind the ports

Binds the two "bind now" estate pins (`spec-pyforge-unifying-strategy/stack.md` § *Estate
leverage*; Dream Grounding 2026-08-30: Scribe's three CAP-18 ports are `graph_store` /
`compile_surface` / `recall_ranker`, and "behind GraphStore" means ingest writes GraphNodes
*through* the persist port) as optional `compile_surface` ingest extras on Story 4.1's
shipped plugin contract. Extras are **off by default** (air-gap). Two consumers are already
waiting: the foundry-cutover move-list (`docs/dreams/pyforge-unifying-strategy.md` § One working tree / phases 0–6) and
marshal Epic 28's token-economy Layers 3–4 (marshal Stories 28.8/28.9 consume by scribe
grammar only). **Never, epic-wide:** a second graph/vector store or store-of-record; a
`cocoindex.serve` MCP product; `@coco.fn` as the lineage religion (OpenLineage rides canopy:CAP-8);
a foundry-root `graphify-out/` product dir; `mem0.add` / `mem0 init --agent` in place of
`scribe capture` — the `recall_ranker` mem0 extra is deliberately **not** in this epic.

### Story 6.1: The graphify ingest extra and its move-list verbs

As a scribe operator,
I want graphifyy bound as an optional `compile_surface` extra with report verbs,
So that code-structure ingest writes through the persist port and the cutover move-list is a derived artifact, not a second graph product.

**Type:** feature • **Effort:** L • **Deps:** S-4.1 • **FR/AD:** unifying-strategy CAP-18 (Grounding 2026-08-30) • stack.md § Estate leverage
**Given** the extra absent or off (the air-gap default) **When** a compile runs **Then** behavior is identical to today's six builtins
**And** with the extra on, folder ingest writes GraphNodes through `graph_store` (`open_graph_store`) — never a parallel store
**And** the report verbs emit a GRAPH_REPORT-style summary (incl. God-node findings) and a move list (host `import pyforge.*` sites, `sys.path` inserts, `five_tier` roots, CFE callers) as derived, gitignored artifacts — like `graph.json`
**And** no foundry-root `graphify-out/` product dir is created and graphifyy is imported only inside the extra adapter

### Story 6.2: The cocoindex incremental ingest extra

As a scribe operator,
I want cocoindex bound as an optional `compile_surface` extra that recomputes only what changed,
So that derived artifacts (the move list, marshal's epic-context distills) stay fresh per commit without full recomputation.

**Type:** feature • **Effort:** L • **Deps:** S-6.1 • **FR/AD:** unifying-strategy CAP-18 (Grounding 2026-08-30) • stack.md § Estate leverage
**Given** the extra off (default) **When** a compile runs **Then** behavior is unchanged
**And** with the extra on, unchanged sources across two consecutive runs yield zero recompute, and one changed source yields exactly one refresh touching only the affected derived rows
**And** outputs write through the persist port or land as derived gitignored artifacts — cocoindex is the freshness engine, never a GraphStore engine and never a store of record
**And** no `cocoindex.serve` MCP product and no `@coco.fn` lineage surface is introduced (OpenLineage rides canopy:CAP-8)

### Story 6.3: The graph-node staleness flag

As a scribe operator,
I want compile_graph to flag a node `stale: true` when its source has moved since compile with no declared supersession,
So that consumers like marshal's planning-graph retrieval (Story 28.9) never silently serve outdated planning context as if it were current.

**Type:** feature • **Effort:** M • **Deps:** S-2.3 • **FR/AD:** spec-marshal-token-economy token-economy:CAP-13
**Given** a node whose source file's latest git commit postdates the node's own `valid_from` and no `supersedes:` edge points at it **When** compile runs **Then** the node is flagged `stale: true`
**And** given an unchanged source, or a node with a declared `supersedes:` edge pointing at it **When** compile runs **Then** the node is never flagged stale
**And** given a retrieval that resolves to a stale-flagged node **When** the answer is served **Then** the consumer falls back to its non-graph path rather than serving the stale node silently
**And** the check is a git-timestamp comparison only — no LLM call, no new external dependency, and Story 2.3's existing `supersedes:` mechanism is unchanged

## Epic 7: Scribe keeps the docs with three utility skills

**Spec binding.** The scribe-side relay of `spec-bmad-suite-lifecycle` (Dream
`docs/dreams/bmad-suite-lifecycle.md`, 2026-09-06): `bmad-os-diataxis`, `bmad-os-audit-file-refs`,
`bmad-os-editorial-review-translation` (CAP-3). **HARD boundaries:** one wielding station per skill,
routing in the persona + AGENTS block, never CLAUDE.md (lifecycle spine AD-2); steward 46.2
installs first; recall stays grounded (`spec-pyforge-scribe`).

### Story 7.1: Three docs skills are scribe-wielded
**Type:** docs • **Effort:** XS • **Deps:** — (after steward 46.2 — cross-station: ledger `blocked`, suite:AD-10) • **FR/AD:** spec-bmad-suite-lifecycle CAP-3 • AD-2
**Surface:** `.claude/skills/bmad-agent-scribe/SKILL.md` (routing lines), the register § 2 row (AGENTS.md carries one pointer line to the register, placed once by `bmad-project-context` — never per-skill lines, AD-2/suite:AD-11), `adoption-register.md` § 2 rows
**Given** the three skills installed **When** the scribe persona routes doc structure to `bmad-os-diataxis`, stale-reference sweeps to `bmad-os-audit-file-refs`, and translated prose review to `bmad-os-editorial-review-translation` **Then** one `audit-file-refs` pass runs against `docs/reference/` and its findings land as a scribe capture, the register names scribe as sole wielder for all three, and CLAUDE.md is untouched

## Currency validation — 2026-08-26

Validated against the reconciled architecture spine (updated 2026-08-26) and the as-built code through commit `2d264c7f5c`. All 14 stories (1.1–5.2) are `done` per the tracked `sprint-status-ledger.yaml`; no heading or status was changed by this pass. Spot-checks: Story 4.1's ACs are satisfied as built — `graph_store_plugins.py::open_graph_store` selects drivers by owner on the CAP-18 hook contract with `FlatFileGraphStorePlugin` as the default, and the steward PG driver registers as a second plugin (`graph_store_pg.py`), not a fork. Story 5.2's PortalClient-only rule is enforced by `tests/meta/test_first_portal_slice.py`. The Canopy-obligations table's line "today's shipped backend is `FlatFileGraphStore` only" is now dated: since 2026-08-25/26 the PG (steward 28.1) and plane (steward 34.5) drivers exist behind the same port — governed by the **2026-08-26 dual-write operator decision** (plane primary satisfying FR-36; `scribe_schema` pgvector written as safety net; strategy SPEC § Open Questions, `query-plane-scribe-cutover`), which stays steward-owned and mints **no new scribe epic or story**. Epic 3's transcript scope is reconciled in the PRD (§5 amendment note) — this breakdown required no structural change. Residual work is tracked in `deferred-work-ledger.md` (DW-FU-3-2 family) and the 2026-08-08 technical report (RISK-1 promote.py review, RISK-2 unscheduled nightly), not as new stories here. *(Addendum 2026-08-27: the RISK-2 residual and DW-FU-3-2-2 named above are now owned by Story 3.3 — minted that date under Epic 3.)*


## Epic 8: Scribe in effect — the compile runs on a schedule the estate owns

**Spec binding.** The scribe satellite of the **realization gate** — a capability is in effect
when its named success criterion is exercised in the running estate, not when its story merges
(`spec-pyforge-unifying-strategy`; fleet-readiness decision batch 2026-09-09, row **C6**).
Scribe is the healthiest station in that pass — 19/19 stories `done` and the code behind them
real — and it has exactly one capability that is built and not in effect: **nothing triggers the
compile.** `.claude/data/pyforge-scribe/graph.json` was last written 2026-08-27, `graph compile
--nightly` is unattended-safe and `flock -n`-safe, and the documented trigger is an opt-in
operator `crontab` line nobody installed. `spec-pyforge-scribe`'s own success signal asks for
"nightly compile completes unattended across at least 4 consecutive scheduled runs" — today that
is unverifiable, because there are no scheduled runs. Steward **Epic 49** carries one index row
pointing here. **HARD boundaries:** no new capability is built — Story 3.3 already shipped the
bounds, the lock and the unattended mode; **never a GitHub Actions workflow** (the runbook's
standing reason holds: a GitHub-hosted runner has none of the three surfaces — this checkout's
`.claude/memory/`, the per-user `~/.claude/projects/<encoded-repo>/*.jsonl` transcripts, and the
gitignored graph store — so a scheduled workflow would faithfully compile an empty machine every
night and prove nothing); the graph stays a derived artifact, never a source of record.

### Story 8.1: The nightly compile gets a trigger the estate owns, and a freshness signal that proves it fired
**Type:** feature • **Effort:** M • **Deps:** S-3.3 • **FR/AD:** FR-9 • FR-11 • `spec-pyforge-scribe` CAP-2 success signal ("4 consecutive scheduled runs") • batch row C6
**Surface:** a checked-in trigger definition (a `pixi.toml` task plus the estate-side hook that invokes it — a marshal dispatch hook, or a versioned systemd-user/`launchd` unit the bootstrap installs; **not** `.github/workflows/`), `src/shared/packages/pyforge-scribe/docs/cli-runbooks.md` § *Installing the nightly trigger*, a freshness/staleness check reachable from the detector set, `.claude/data/pyforge-scribe/graph.json` (read only — still gitignored, still derived)
**Given** `scribe graph compile --nightly` is prompt-free, `flock -n`-safe and exits 0 on an overlapping firing (`cli.py:285-299`), and the only documented trigger is "an opt-in operator crontab entry" (`cli.py:290-291`, `docs/cli-runbooks.md` § *Installing the nightly trigger*) that is not installed — the store's last write is 2026-08-27 — **When** the trigger is defined in the repo and installed by a documented, repeatable act rather than a hand-typed `crontab -e` **Then** the compile fires on schedule on the machine that holds the three surfaces, four consecutive scheduled runs are recorded (run log or graph mtime series), and the trigger's definition is reviewable in git
**And** a freshness signal exists and is checkable: the age of `.claude/data/pyforge-scribe/graph.json` is reportable, and a store older than the schedule's own period surfaces as an **advisory** finding — never a PR gate and never a second verdict
**And** the boundary is honoured explicitly: the story records **why** this is not a GitHub Actions workflow (runbook § *Scope note*), so the next pass does not re-propose one
**And** the durable-driver path is not silently required — the default `FlatFileGraphStore` needs no service; if a scheduled run is ever pointed at the PostgreSQL driver it needs the local cluster up (`scribe-pg-up`), which the trigger must either start or refuse cleanly, never fail red on a machine without it

### Story 8.2: The nightly compile keeps the graphify code surface
**Type:** feature • **Effort:** S • **Deps:** S-6.1 • S-8.1 • **FR/AD:** `spec-scribe-graphify-nightly-currency` CAP-1 • CAP-2 • AD-6
**Surface:** `src/shared/packages/pyforge-scribe/src/pyforge/scribe/extras/graphify.py`, `scripts/scribe_nightly_trigger.py`, `pixi.toml` `[feature.pyforge-scribe.dependencies]`
**Given** live graphifyy exposes `extract` as a package submodule after `collect_files` **When** `scribe index build` or a compile with the extra on calls `ingest_repo` **Then** ingest uses the callable (`graphify.extract.extract` when the attribute is a module) and writes `code:` nodes through `open_graph_store`
**And** the nightly trigger sets `SCRIBE_GRAPHIFY_EXTRA=1` when the operator has not set the variable, so the 02:30 full rebuild keeps those nodes; an explicit `0` stays off
**And** the `pyforge-scribe` pixi feature declares `graphifyy` so that env can import `graphify` (lazy, adapter-only); a missing or failing extra still degrades on compile and never fails the scheduled run red
**And** an interactive `scribe graph compile` with the extra unset is unchanged — zero code nodes from graphify

### Story 8.3: Herald fact ledgers join the compile
**Type:** feature • **Effort:** S • **Deps:** S-2.2 • S-8.2 • **FR/AD:** `spec-scribe-graphify-nightly-currency` CAP-3 • `spec-deck-family-currency` CAP-2
**Surface:** `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py`
**Given** `presentations/<slug>/facts.yaml` files exist (Herald's derived fact ledgers) **When** `scribe graph compile` runs **Then** each file is one `kind=doc` `GraphNode` written through `open_graph_store`, citation `presentations/<slug>/facts.yaml`
**And** a repo with no `presentations/` directory compiles with zero fact-ledger nodes and no warning
**And** `project/*.dc.html`, `src/slides/fragments/`, dated Marp sources, and copied `src/deck/` engines are not compile sources
**And** the ingest is the existing text-file `doc` path (`_node_from_text_file`), not the graphify extra

### Story 8.4: The compile keeps knowledge layers honest
**Type:** feature • **Effort:** M • **Deps:** S-6.3 • S-8.3 • **FR/AD:** `spec-scribe-knowledge-layers` CAP-1 • CAP-2 • CAP-3
**Surface:** `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py`
**Given** a full rebuild **When** a source file's working-tree mtime is older than its latest git commit **Then** that node is not flagged stale; stale requires the commit author date after this compile's `compiled_at`
**And** memlog/changelog/retro walks skip `archive/`, `implementation-artifacts/`, and any `tests/` path segment
**And** retros are only `_bmad-output/projects/*/planning-artifacts/retros/*.md`
**And** `docs/dreams/*.md` with status `dreamt`|`pitched`|`specified`, folder `SPEC.md` with status `ready`|`in-progress`, and `presentations/*/facts.yaml` each become one `kind=doc` node

### Story 8.5: Default recall omits the code surface
**Type:** feature • **Effort:** S • **Deps:** S-2.4 • S-8.4 • **FR/AD:** `spec-scribe-knowledge-layers` CAP-4
**Surface:** `src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py`, `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py`
**Given** an unscoped `scribe recall` **When** the only token overlap is a `kind=code` node **Then** the result is `no grounded answer found`
**And** `scribe recall --kind code` (or `answer(..., kinds={"code"})`) may return that node
**And** Marshal `--scope` behavior is unchanged

### Story 8.6: Session path names scribe recall
**Type:** docs • **Effort:** XS • **Deps:** S-8.5 • **FR/AD:** `spec-scribe-knowledge-layers` CAP-5
**Surface:** `AGENTS.md` (outside `bmad:context`)
**Given** any coding agent reading `AGENTS.md` **When** it needs a team decision or contract fact **Then** it is instructed to run `scribe recall` (default omits `code:`)
**And** graphify AST and Marshal `codegraph` are named as different products, not the default recall bag

## Epic 9: Scoped retrieve can cite the poster’s numbers

**Spec binding.** `spec-scribe-marshal-fact-visibility` CAP-1 (hoisted
parked later-caps:CAP-10). Compile already writes `presentations/<slug>/facts.yaml`
(`Story 8.3`). Marshal planning-graph retrieve already passes `--scope`.
The gap is the citation rule in `recall.py`.

### Story 9.1: Scoped recall admits the project's own fact ledger
**Type:** feature • **Effort:** S • **Deps:** S-8.3 • S-8.5 • **FR/AD:** `spec-scribe-marshal-fact-visibility` CAP-1
**Surface:** `src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py`, `src/shared/packages/pyforge-scribe/src/pyforge/scribe/cli.py`
**Given** a compiled `doc:` node cited `presentations/pyforge-scribe/facts.yaml` **When** `answer(..., scope="pyforge-scribe")` runs **Then** that node is a legal candidate (same as that project's planning tree)
**And** `--scope pyforge-scribe` still excludes `presentations/pyforge-warden/facts.yaml`, nested `facts.yaml`, and the rest of `presentations/`
**And** unscoped recall is unchanged
**And** Marshal argv stays `--scope` only — no `--facts` flag

## Epic 10: The story you are on compiles; the ones you finished do not

**Spec binding.** `spec-scribe-in-flight-story-specs` CAP-1 (hoisted
parked later-caps:CAP-6). Folder `SPEC.md` already compiles (Story 8.4). Per-story
files must not join as a glob.

### Story 10.1: In-flight story specs join the compile
**Type:** feature • **Effort:** S • **Deps:** S-8.4 • **FR/AD:** `spec-scribe-in-flight-story-specs` CAP-1
**Surface:** `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py`
**Given** `spec-10-1-….md` and a ledger row `10-1-…: in-progress` **When** `scribe graph compile` runs **Then** that file is one `kind=doc` node
**And** the same file with ledger `done` is omitted even if frontmatter says `ready-for-dev`
**And** `backlog` rows, a missing ledger, and folder `SPEC.md` are not this surface
**And** a missing tree is zero nodes and no warning

## Epic 11: Recall withholds what landed after last night's compile

**Spec binding.** `spec-scribe-recall-stale-between-nightlies` CAP-1
(hoisted parked later-caps:CAP-9). Compile-time stale (Story 8.4) is unchanged.

### Story 11.1: Recall withholds sources committed after compile
**Type:** feature • **Effort:** S • **Deps:** S-8.4 • S-2.4 • **FR/AD:** `spec-scribe-recall-stale-between-nightlies` CAP-1
**Surface:** `src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store.py`, `compile.py`, `recall.py`
**Given** a compiled flat-file store **When** a cited source file is committed after `compiled_at` **Then** `answer()` skips that node
**And** reloading `graph.json` still exposes `compiled_at`
**And** commit/transcript nodes stay eligible
**And** a store with no `compiled_at` uses only the stored `stale` bit

## Epic 12: Every recall door uses the same default bag

**Spec binding.** `spec-scribe-portal-recall-defaults` CAP-1 (hoisted
parked later-caps:CAP-12). CAP-5 stays `AGENTS.md`.

### Story 12.1: Portal and Marshal inherit default recall
**Type:** feature • **Effort:** S • **Deps:** S-8.5 • S-8.6 • **FR/AD:** `spec-scribe-portal-recall-defaults` CAP-1
**Surface:** `django-pyforge` `_grammar_recall`, `planning_graph.render_scribe_recall_argv`, `.cursor/rules/scribe-recall.mdc`
**Given** the portal job or Marshal retrieve **When** they build `scribe recall` argv **Then** they do not pass `--kind`
**And** Marshal may still pass `--scope`
**And** `.cursor/rules/scribe-recall.mdc` names the AGENTS session path
**And** django-scribe is not redesigned and does not import `pyforge.scribe`

## Epic 13: Planning novels stay files; the graph holds pointers

**Spec binding.** `spec-scribe-planning-pointers` CAP-1 (hoisted
parked later-caps:CAP-7). Folder `SPEC.md` and in-flight story specs stay on
their own surfaces.

### Story 13.1: Planning pointers join the compile
**Type:** feature • **Effort:** S • **Deps:** S-8.4 • S-10.1 • **FR/AD:** `spec-scribe-planning-pointers` CAP-1
**Surface:** `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py`
**Given** named `brief.md` / `prd.md` / `ARCHITECTURE-SPINE.md` / `epics.md` **When** `scribe graph compile` runs **Then** each is one `kind=doc` pointer
**And** pointer text has title, path, status, and FR/AD or Epic/Story headings
**And** a unique sentence that exists only in the source body is absent from the node
**And** `epics-*.md`, architecture novels, addenda, research, and `specs/` are omitted
**And** a missing tree is zero nodes and no warning

## Epic 14: Named docs extras, never the docs tree

**Spec binding.** `spec-scribe-named-docs` CAP-1 (hoisted parked
later-caps:CAP-13). Dreams stay on the existing CAP-3 surface.

### Story 14.1: Named docs join the compile
**Type:** feature • **Effort:** S • **Deps:** S-8.4 • S-13.1 • **FR/AD:** `spec-scribe-named-docs` CAP-1
**Surface:** `src/shared/packages/pyforge-scribe/src/pyforge/scribe/compile.py`
**Given** `docs/how-to/<guide>.md` **When** `scribe graph compile` runs **Then** it is one ordinary `kind=doc` node
**And** `docs/reference/library-llms-full.md` is one heading-extract `doc` node
**And** `docs/how-to/README.md`, tutorials, and explanation files are omitted
**And** a unique sentence that exists only in the catalog body is absent from that node
**And** a missing how-to tree or missing catalog is zero extra nodes and no warning

## Epic 15: Graphify walks the named code trees, not the warehouse

**Spec binding.** `spec-scribe-graphify-target-list` CAP-1 (hoisted
parked later-caps:CAP-8). Extra remains off by default.

### Story 15.1: Graphify target list joins the compile
**Type:** feature • **Effort:** S • **Deps:** S-8.2 • **FR/AD:** `spec-scribe-graphify-target-list` CAP-1
**Surface:** `src/shared/packages/pyforge-scribe/src/pyforge/scribe/extras/graphify.py`
**Given** extra-on compile and no explicit target **When** `ingest_repo` runs **Then** it walks `src/shared/packages`, `src/platform`, and `scripts` when they exist
**And** a present `recipes/` tree is not ingested
**And** missing optional list entries produce no warning
**And** extra-off compile is unchanged
**And** an explicit `--target` stays one path

## Epic 16: Recall names the surface, not a kind bag

**Spec binding.** `spec-scribe-recall-modes` CAP-1 (hoisted parked
later-caps:CAP-11). Internal lexical/semantic ranking is unchanged.

### Story 16.1: Recall modes join the CLI
**Type:** feature • **Effort:** S • **Deps:** S-8.5 • **FR/AD:** `spec-scribe-recall-modes` CAP-1
**Surface:** `src/shared/packages/pyforge-scribe/src/pyforge/scribe/recall.py`, `cli.py`
**Given** `scribe recall` **When** `--mode planning` **Then** candidates are `doc` and `memlog` only
**And** `--mode memory` is `memory` only; `--mode code` is `code` only
**And** `--mode` with `--kind` exits 2
**And** neither flag keeps the CAP-4 default bag
**And** portal argv is unchanged

## Epic 17: One owner for “where is this symbol?”

**Spec binding.** `spec-scribe-code-navigation-owner` CAP-1 (hoisted parked
later-caps:CAP-14 from `spec-scribe-knowledge-layers/later-caps.md`). Reserved hole
between 16 and 18 — do not renumber Epic 18.

### Story 17.1: Marshal codegraph owns symbol navigation
**Type:** docs • **Effort:** S • **Deps:** S-8.6 • S-16.1 • **FR/AD:** `spec-scribe-code-navigation-owner` CAP-1
**Surface:** `AGENTS.md` (outside `bmad:context`), `src/shared/packages/pyforge-scribe/src/pyforge/scribe/extras/graphify.py`, `src/shared/packages/pyforge-scribe/tests/unit/test_navigation_owner.py`, `.cursor/rules/scribe-recall.mdc`
**Given** graphify `code:` and Marshal `codegraph.db` both answer “where is this symbol?”
**When** this story lands
**Then** `AGENTS.md` outside `bmad:context` names Marshal `codegraph.db` as symbol nav owner and forbids `scribe recall --mode code` for symbols
**And** the graphify extra module docstring says it is not the nav API
**And** a unit test fails if those AGENTS sentences are removed
**And** `.cursor/rules/scribe-recall.mdc` stays consistent (force-add if `.cursor/` is gitignored)
**And** default recall still omits `code:`; graphify is not deleted; `codegraph install --target claude` is not run; recipes/ and repo root are not nightly-graphified
**Status:** done

## Epic 18: Planning retrieve names the planning surface

**Spec binding.** `spec-scribe-recall-mode-wiring` CAP-1..3. Story 16.1
shipped `--mode`; this epic wires the callers.

### Story 18.1: Retrieve and sessions pass mode planning
**Type:** feature • **Effort:** S • **Deps:** S-16.1 • **FR/AD:** `spec-scribe-recall-mode-wiring` CAP-1, CAP-2, CAP-3
**difficulty:** easy
**Surface:** `src/shared/packages/pyforge-marshal/src/pyforge/marshal/core/planning_graph.py`, `src/shared/packages/django-pyforge/src/django_pyforge/assertion/client.py`, `AGENTS.md`, `.cursor/rules/scribe-recall.mdc`
**Given** Story 16.1 shipped `--mode` and Marshal retrieve still inherits the default bag
**When** this story lands
**Then** `render_scribe_recall_argv` appends `--mode planning`, may still append `--scope`, never appends `--kind`, and does not default to `--mode code`
**And** `recall_cli_argv` with no mode has neither `--mode` nor `--kind`; `mode=planning|memory|code` appends that `--mode`
**And** `AGENTS.md` session path and `.cursor/rules/scribe-recall.mdc` show `--mode planning` on the decision command

## Epic 19: The session contract reaches every harness

**Spec binding.** `spec-pyforge-scribe` CAP-27. Minted 2026-09-19 at the review of PR #1513 (a
parallel session's AGENTS.md / GEMINI.md governance PR) from the Dream entry "Scribe serves every
harness"; the research that fixed the shape is
`planning-artifacts/research/multi-harness-instruction-surface-2026-09-19.md`. Operator rulings the
same day: point, don't copy; `@AGENTS.md` import + no attribution trailers; direct-capture the
team-relevant notes; full chain. **HARD boundaries:** the `bmad:context` block is
`bmad-project-context`'s, never hand-edited; no instruction content that belongs in `AGENTS.md` is
authored into a per-tool file; Dream items (4)–(10) are seeded, not this epic's scope.

### Story 19.1: One AGENTS.md, reached natively or by a one-line pointer from every harness
**Type:** feature • **Effort:** M • **Deps:** — • **FR/AD:** `spec-pyforge-scribe` CAP-27
**difficulty:** medium
**Surface:** `AGENTS.md` (team-memory section with real `.claude/memory/` paths; behavioural guidelines; "how each harness loads this file"; pre-PR checklist items 9–12 corrected and folded), `CLAUDE.md` (`@AGENTS.md` import), `GEMINI.md` (thin Gemini addendum), `.gemini/settings.json` (new: `context.fileName` with `AGENTS.md` first), `.github/copilot-instructions.md` (thin addendum), `.vscode/settings.json` (`chat.useAgentsMdFile`), `.claude/memory/feedback/*.md` + `MEMORY.md` (three direct captures), `scripts/spec_surface_allowlist.txt` (GEMINI.md moves to the scribe surface), `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py` (new).
**Given** `CLAUDE.md` exists and never imports `AGENTS.md`, Gemini has no `context.fileName`, and PR #1513 pointed every harness at memory files that live in one operator's home directory
**When** this story lands
**Then** Claude Code loads the verified `bmad:context` block through `@AGENTS.md`; Gemini CLI / Antigravity load `AGENTS.md` first through the checked-in `.gemini/settings.json`; VS Code chat loads it through `chat.useAgentsMdFile`; Cursor, Codex, the Copilot cloud agent, Devin and Jules keep loading it natively
**And** `AGENTS.md` names `.claude/memory/MEMORY.md` as the session-boot read and `scribe capture` as the way in; every memory path it cites exists in the repo; the three lessons PR #1513 cited from auto-memory exist as team entries
**And** `GEMINI.md`, `.github/copilot-instructions.md` and the `.cursor/rules` pointers carry no section that also exists in `AGENTS.md`, and a scribe meta-test reds the import, the Gemini setting, the VS Code setting, any duplicated H2, a per-tool file over 60 lines, or a dangling memory path
**And** `governance-currency` stays green on `AGENTS.md` and `CLAUDE.md`; the pre-PR checklist's items 9–12 read as the repo's real invariants (the `dashboard/` extra boundary, `pr-preflight`'s known gaps) with no duplicates
**Status:** done
**Outcome (2026-09-19):** landed as PR #1513 after review + rebuild (three review layers over the parallel session's diff; the research doc; chain minted the same day); tracked spec `specs/spec-19-1-one-agents-md-reached-natively-or-by-a-one-line-pointer-from-every-harness.md` carries the triage log and Auto Run Result.

### Story 19.2: scribe capture and recall run from the session default environment
**Type:** feature • **Effort:** S • **Deps:** — • **FR/AD:** `spec-pyforge-scribe` CAP-28 (Dream item (7), pixi-env half)
**difficulty:** easy
**Surface:** `pixi.toml` (`[feature.pyforge-guild.dependencies]` + the `pyforge-scribe` path dep; comment at `feature.pyforge-guild`), `pixi.lock`, `AGENTS.md` / `CLAUDE.md` / `.cursor/rules/scribe-recall.mdc` (capture/recall invocations on `-e pyforge-guild`), `src/shared/packages/pyforge-scribe/tests/meta/test_guild_env_membership.py` (new).
**Given** `pyforge-guild` is the default environment for every harness but the scribe CLI lived only in `-e pyforge-scribe`, so a sandbox that installs the Guild default could neither capture nor recall
**When** this story lands
**Then** `pixi run -e pyforge-guild scribe --help` lists `capture` / `recall` / `graph`; the core package's run-deps (`typer`, `pydantic`, `pyforge-core`) are the only additions; `graphifyy`, `cocoindex` and `psycopg` stay in `-e pyforge-scribe`
**And** every governance doc routes `scribe capture` / `scribe recall` to `-e pyforge-guild`; `environment.yaml` is unchanged; `llms-full-check` is green; a scribe meta-test pins the membership and the doc routing
**Status:** done
**Outcome (2026-09-19):** landed with Story 19.1 in PR #1513 (operator: "shouldn't we fix this" — yes, one path dependency); tracked spec `specs/spec-19-2-scribe-capture-and-recall-run-from-the-session-default-environment.md`.

### Story 19.3: The instruction surface is version-aware — Claude Code's built-in agents-md mod

**Type:** feature • **Effort:** S • **Deps:** S-19.1 • **FR/AD:** `spec-pyforge-scribe` CAP-29 (operator ask 2026-09-20 09:35Z) • sits beneath the closed Epic 19 (the epic key stays `done` — `ledger-regression`)
**difficulty:** easy
**Surface:** `AGENTS.md` (§ How each harness loads this file — the Claude Code row: ≥2.1.277 built-in `agents-md` mod, pinned mode `claude-md-and-agents-md`, nested `AGENTS.md` honoured; below / Bedrock / Vertex / Foundry: the `@AGENTS.md` import), `CLAUDE.md` (the duplicated "Behavioral Guidelines" section collapses to a one-line pointer), `.claude/settings.json` (`customInstructions` → `AGENTS.md`), `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py` (H2s compared after spelling normalisation; the Claude Code row's facts asserted), `scripts/claude_instruction_mode_check.py` + `scripts/detectors.py` (runtime-scope currency warn: `claude --version` < 2.1.277 or `instructionFiles` ≠ the pinned mode; silent when `claude` is absent), `planning-artifacts/research/multi-harness-instruction-surface-2026-09-19.md` (dated addendum). Hand-driven 2026-09-20.
**Given** Claude Code 2.1.277 (2026-09-18) ships a built-in `agents-md` mod whose default mode stays out of any project with a `CLAUDE.md`, so `AGENTS.md` still reaches Claude Code only through the import and the atlas child `AGENTS.md` never does; the harness table says "only through that import" unconditionally; `CLAUDE.md` and `AGENTS.md` both carry the five guidelines under differently-spelled H2s
**When** the table states version + pinned mode, the duplicate collapses, the parity test normalises spelling, the operator's settings carry the mode and a runtime check reports drift
**Then** every parity meta-test passes; the check warns on a runtime below 2.1.277 or a non-pinned mode and is silent without `claude`; `governance-currency` is green on both files
**And** the import stays the floor — nothing here depends on the mod being present
**Status:** done
**Outcome (2026-09-20):** hand-driven in the fleet PR with marshal 46.11; see the tracked spec's Auto Run Result.

## Epic 20: The managed instruction block carries no aspiration (spec-pyforge-scribe CAP-30)

Minted 2026-09-20 (evening) from the Dream entry of the same name. Epic 19 is `done`, so the guard is a new epic (a fix on
a done epic gets a new epic). **HARD boundaries:** scope is the text between the `bmad:context` markers only; the
guard is a scribe meta-test, never a doctor detector or a PR gate of its own; it lands with steward Story 66.2,
which retires the two lines it would red today.

### Story 20.1: The parity meta-test reds a TODO inside the managed block

As the maintainer of the instruction surface,
I want `test_instruction_surface_parity.py` to fail on a `TODO:` / `FIXME:` / "not yet landed" line between the `bmad:context` markers,
So that a decision without a Story cannot sit in the block as a line every session pays for.

**Type:** feature • **Effort:** S • **Deps:** cross-project: steward 66.2 (the two lines standing on 2026-09-20) • **FR/AD:** spec-pyforge-scribe CAP-30 • Dream 2026-09-20 (evening)
**Surface:** `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py` (one test + a planted-fixture self-test), `AGENTS.md` (nothing — the block is read, not written).
**Given** two `TODO:` lines have stood in the managed block since 2026-09-04 with no Story behind them
**When** this story lands
**Then** a planted `TODO:` between the markers fails the meta-test naming the line; the live block passes; TODO text outside the markers is ignored
**And** `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` green

**Outcome (2026-09-20):** done, hand-driven in PR #1553 with steward 66.2 — see the tracked spec's Auto Run Result.

## Epic 21: The instruction surface names the estate first (spec-python-foundry-cutover fnd:CAP-15)

Minted 2026-09-25 from steward's `docs/dreams/pyforge-unifying-strategy.md` § *Consolidation —
2026-09-25* (Input 3, folded from PR #1563). A new epic because Epic 20 is `done`. The capability
is steward's (`spec-python-foundry-cutover` fnd:CAP-15); the surface is scribe's (CAP-27, the
instruction-surface parity contract), so the story lives here and steward carries index row 67.7.
**HARD boundaries:** PR #1563's hand-written `AGENTS.md` is reference only, never merged; the
managed `bmad:context` block changes only through `bmad-project-context`; nothing edits
`python-foundry`'s instruction surface (its PR #19 is B's under the writer lock).

### Story 21.1: `AGENTS.md` opens with what this repository is

As an agent in any harness opening this repository cold,
I want `AGENTS.md` to tell me first that this is A — the PyForge control plane and BMAD Agentic-SDLC host, with the recipe factory as one cell — and how A and B divide work, then a short behavioural core,
So that I place a task on the right root and in the right mode before I read a single incident note.

**Type:** docs • **Effort:** M • **Deps:** — • **FR/AD:** fnd:CAP-15 • spec-pyforge-scribe CAP-27 • cross-station: steward index 67.7 flips `done` when this closes; reference payload PR #1563 (branch `docs/agents-pyforge-bmad`)
**Surface:** `AGENTS.md` (managed block through `bmad-project-context`; sections outside it by hand), `CLAUDE.md` (pointer + Claude-only notes), the pointer targets each removed note moves to (`.claude/memory/`, `docs/reference/`), `src/shared/packages/pyforge-scribe/tests/meta/test_instruction_surface_parity.py` only if a parity rule must follow a moved section.
**Given** `AGENTS.md` opens with the recipe factory and carries ~500 lines of accumulated notes, while the estate is two roots under a writer lock
**When** this story lands
**Then** the file opens with A's identity, the A/B roles, the modes (never `move`) and the writer lock, stating that A is never archived; the behavioural core adds heal-the-tissue, state over action, read-only harness ledgers and implement / review separation, using the worker's real status vocabulary (`draft → ready-for-dev → in-progress → in-review → done`); every incident note removed from the file has a named pointer target that exists
**And** `pixi run --frozen -e pyforge-scribe pyforge-scribe-test` green; `governance-currency` (in `detectors-ci`) green; `CLAUDE.md` still imports `@AGENTS.md` bare
**Status:** backlog

## Platform floor addendum — 2026-09-07

Every story in this epic set builds and tests against **Python 3.14 only**.
`pyforge-scribe`'s `requires-python` was raised `>=3.12` -> `>=3.14` by marshal Story 32.2
(`spec-fleet-consistency-standard` CAP-5) to match the interpreter the workspace actually
installs. No story's acceptance criteria change; recorded here so a future story is not
written against a 3.12 assumption the estate cannot produce.

## Currency reconciliation — 2026-09-20 (fleet consistency pass)

*Operator ruling 2026-09-20: every station's PRD, spine and epics are re-stamped in the same pass,
grace period or not, so the whole chain reads current for the foundry cutover. Trigger: the
station Spec's `.memlog.md` gained a 2026-09-20 event — the fleet consistency pass reconciled every
tracked story spec's frontmatter against the sprint ledger, matched each "Ledger status" line,
reconstructed missing Auto Run Results from `main`'s landing commits, fixed invalid frontmatter,
and let `sprint-ledger-sync` roll the epic keys up (`spec→prd→arch→epics` cascade). Bookkeeping only:
no requirement, decision, story or AD changes in this epics. `updated:` bumped to record that the
check ran.*

## Currency reconciliation — 2026-09-25

`arch→epics` edge after the spine re-stamp of 2026-09-25. Epic 21 / Story 21.1 minted from
steward's 2026-09-25 consolidation (`spec-python-foundry-cutover` fnd:CAP-15 — `AGENTS.md` opens
with what this repository is; steward index row 67.7). Every Story heading still maps 1:1 to a
`sprint-status-ledger.yaml` key; the Tier-3 feed was repaired from the tracked twin first.
`updated:` bumped.
