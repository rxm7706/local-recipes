---
fr-derivation-from: "2026-09-17"
title: pyforge-scribe
created: 2026-07-25
updated: "2026-09-25"   # RE-STAMPED 2026-09-25: chain-currency (spec->prd) — spec-pyforge-scribe memlog moved 2026-09-24T20:28 (marshal 46.3 surface reconciles); no FR change. Prior 2026-09-20
status: final
currency_review: "Reviewed 2026-09-17 — one-chain scribe fold; FR-1..15 cite CAP-1..4; reminted station CAPs 1..26 live on spec-pyforge-scribe. FR delta: citations only."
---

# PRD: pyforge-scribe (Scribe)
*Working title confirmed against the ecosystem-crew Dream — dist `pyforge-scribe` / module `pyforge.scribe` / CLI `scribe`.*

## 0. Document Purpose

This PRD defines what Scribe builds, for the engineers and agents who implement it and the downstream BMAD workflows (`bmad-architecture`, `bmad-create-epics-and-stories`) that consume it. It builds directly on `planning-artifacts/briefs/brief-pyforge-scribe-2026-07-25/brief.md` (the product brief) and the two research reports in `planning-artifacts/research/` — it does not re-derive their findings, it cites and operationalizes them. Structure: a Glossary anchors vocabulary used verbatim throughout; Features group Functional Requirements (globally numbered FR-1 through FR-N) under coherent capability clusters; `[ASSUMPTION]` tags are inline and indexed in §12. This PRD also formally **absorbs** the legacy `docs/specs/claude-team-memory.md` spec (10 waved stories, unstarted) as Wave 1 scope — §9 records the supersession decision explicitly.

## 1. Vision

Scribe is the team's inward voice: a real, installable package that captures decisions as they happen, compiles them nightly into a knowledge graph built from the tools the team already uses, and answers from that memory so every session — human or agent — starts already knowing what the team knows. It exists because this codebase diagnosed the same disease twice: Sentinel's 2026-04 finding that "the knowledge the team runs on is scattered and lossy" and team-memory's 2026-07 finding that the concrete, present-day instance of that disease is Claude Code's per-machine auto-memory, invisible to teammates and other agent sessions.

Scribe is not a general-purpose enterprise knowledge platform and does not compete on that ground. Per the market research, no analogue (Mem0, Zep/Graphiti, Khoj, Glean) occupies the specific intersection Scribe targets: git-native (no required external service), compiled from the tools the team already runs (not a separate ingestion app), and captured at decision time (not mined from chat logs after the fact). Per the domain research, this intersection is not a lonely bet — ADR discipline is independently converging on "durable, agent-readable decision records," local-first tooling has normalized "no required cloud call," and the EU AI Act's August 2026 deadline is turning air-gap posture into a real enterprise requirement, not a preference.

Scribe ships in two waves that are each independently valuable: Wave 1 completes the fully-specified, unstarted `claude-team-memory` effort (capture and curate team-shared memory); Wave 2 builds the previously-unbuilt core (compile the graph, answer from it). Wave 1 alone already fixes the concrete pain (the `d43899c1cb` duplication incident); Wave 2 is what makes Scribe the thing Sentinel dreamed of five years — sorry, fifteen months — before anyone owned it.

## 2. Target User

### 2.1 Jobs To Be Done

- As a developer (human or agent) working in this repo, I want to record a decision once, at the moment I make it, and have it be visible to every teammate and every agent session from then on — not trapped in my personal machine's memory.
- As a new contributor (human or agent) on day one, I want to ask "why did we do X" and get a grounded, cited answer instead of silence or a plausible-sounding guess.
- As an operator running multiple concurrent BMAD projects and agent worktrees (per this repo's multi-project pattern), I want team knowledge to survive across parallel sessions, not just across human operators.
- As a maintainer of a regulated/air-gapped environment evaluating agent tooling, I want a team-memory system with zero required external service and zero runtime telemetry, so it is deployable inside a compliance boundary without an exception process.

### 2.2 Non-Users (v1)

- **Cross-repo knowledge workers.** Scribe's memory is per-repo by design (inherited from the legacy spec's NG5); a user wanting one graph spanning many repositories is out of scope for v1.
- **Non-technical stakeholders wanting a wiki UI.** Scribe's primary surface is a CLI + files in the repo; it is not a browser-based knowledge-base product (distinguishing it from Khoj/Glean's UI-first posture).
- **Teams wanting fully automated, hookless-free capture.** v1 (both waves) requires a deliberate `scribe capture` invocation — no passive conversation-log mining (this is a design choice, not a gap; see §5 Non-Goals).

### 2.3 Key User Journeys

*Lighter scope dial (developer/CLI product, single-operator-role-per-session) — JTBD-restated form per the template's scope dial.*

- **UJ-1. A developer captures a decision the moment it's made.** Mid-session, human or agent decides to replace LiteLTM with an in-house gateway. Runs `scribe capture --type decision --text "ADR-005b: in-house gateway replaces LiteLLM"`. The record lands immediately, git-diffable, reviewable in the next PR — no separate app, no context switch. Realizes FR-1, FR-4.
- **UJ-2. A different operator's session recalls it, cited.** A week later, a different teammate (or the same teammate in a fresh agent worktree) asks `scribe recall "why did we drop LiteLLM?"`. The answer surfaces, grounded in and citing ADR-005b — not reconstructed from code archaeology or an LLM guess. Realizes FR-13.
- **UJ-3. The nightly compile keeps the graph current without babysitting.** `scribe graph compile --nightly` runs unattended (cron, CI, or manual re-run) and idempotently re-reads `.claude/memory/`, `.memlog.md` files, git history, and retros — the graph reflects last night's state without anyone remembering to "update the wiki." Realizes FR-10, FR-11.
- **UJ-4. A user-local rule gets promoted to the team, deliberately, with review.** An operator notices a personal auto-memory entry ("BMAD must invoke conda-forge-expert...") is actually team-relevant. `scribe capture --promote` (or the equivalent invocation) proposes the promotion diff — rewritten in team voice — and stops for confirmation. The operator reviews and commits. Realizes FR-3, FR-4, FR-5.

## 3. Glossary

- **Capture** — the authored act of recording a decision, ADR, runbook, or rejected tradeoff into the team-shared record at the moment it happens, via `scribe capture`. Distinct from *promotion* (below).
- **Team memory** — the checked-in `.claude/memory/` directory tree: the repo-scoped, git-tracked layer of team-relevant entries, auto-loaded into every session via `CLAUDE.md`'s `@import`. Inherited 1:1 from the legacy spec.
- **User-local memory** — Claude Code's existing per-machine, per-user auto-memory at `~/.claude/projects/<encoded-path>/memory/`. Not owned by Scribe; Scribe reads from it (promotion source) but does not replace it.
- **Promotion** — the proposal-then-confirm workflow that moves a team-relevant entry from user-local memory into team memory, rewriting it into team voice and leaving a pointer stub behind. Inherited 1:1 from the legacy spec's Story 4/6/7.
- **Pointer stub** — the `promoted: true` frontmatter + short redirect body left in user-local memory after a successful promotion, per the format in §9's inherited decisions.
- **The graph** — the compiled knowledge structure produced by `scribe graph compile --nightly`: artifacts as nodes, references as edges, built from real repo tools (team memory, memlogs, git history, retros, CHANGELOGs). The Sentinel Dream's "unbuilt core."
- **Recall** — the answer surface (`scribe recall <query>`) that queries the compiled graph and returns a grounded, cited response.
- **Team-relevance test** — the day-1-contributor heuristic deciding whether an entry belongs in team memory: "would a brand-new contributor, on their first session, without ever having talked to the current owner, benefit from this rule?" Inherited verbatim from the legacy spec's G6/Story 3.
- **Air-gap posture** — per the domain research's precise bar: zero required runtime telemetry, zero required package-registry reachability, zero vendor cloud dependency — not merely "can be self-hosted."

## 4. Features

### 4.1 Capture & Promotion (Wave 1 — the team memory layer)

**Description:** The checked-in `.claude/memory/` directory, the promotion workflow that moves entries from user-local memory into it, and the wiring that makes team memory auto-load every session. This feature is the legacy `claude-team-memory` spec's full scope (its 10 stories, Waves A/B/C), migrated into Scribe as the foundation the graph compiles from. Realizes UJ-1, UJ-4. FR IDs below map 1:1 to the legacy spec's FR-1 through FR-9 (renumbered for this PRD's global sequence; intent unchanged unless noted).

#### FR-1: Frontmatter schema parity ← CAP-1
Entries in `.claude/memory/` use the same frontmatter fields as user-local auto-memory (`name`, `description`, `type` ∈ `{feedback, project, reference}`), so migration in either direction is mechanical. *(= legacy FR-1)*

**Consequences (testable):**
- A `.claude/memory/<type>/*.md` file with a missing or malformed `type` field fails a schema check.
- Promotion tooling reads and writes this exact schema without a translation step.

#### FR-2: MEMORY.md index size discipline ← CAP-1
`.claude/memory/MEMORY.md` stays under 200 lines (Claude Code truncates beyond that); enforced by convention (entries are one-line `- [Title](file.md) — hook`), no tooling gate in Wave 1. *(= legacy FR-2)*

#### FR-3: Proposal-then-confirm promotion ← CAP-1
`scribe capture --promote` (or equivalent) stops after producing the proposed diff and waits for explicit confirmation before writing. No auto-commit, no unreviewed multi-file write. *(= legacy FR-3)*

**Consequences (testable):**
- Running the promotion path against a set of user-local entries produces a structured proposal (files + full content + updated `MEMORY.md`) and halts before any write.
- Nothing under `.claude/memory/` changes on disk until confirmation is given.

#### FR-4: Team-voice rewrite required ← CAP-1
Promoted entries are rewritten per the team-voice rules (strip first-person, drop "user prefers" framing, drop incident-specific anecdotes, preserve **Why:**/**How to apply:** structure, preserve paths/commands/identifiers verbatim) — never a verbatim copy. *(= legacy FR-4)*

#### FR-5: Pointer stub after promotion ← CAP-1
After confirmation, the source user-local entry is replaced with the pointer-stub format (`promoted: true` + redirect body naming the promoted file's path and date) — not deleted, preserving traceability. *(= legacy FR-5)*

#### FR-6: Detect already-promoted entries (idempotency) ← CAP-1
The promotion workflow detects `promoted: true` frontmatter and skips re-classification/re-promotion. Repeated invocation is a no-op against already-promoted entries. *(= legacy FR-6)*

#### FR-7: Read-only outside `.claude/memory/` (and Scribe's own package/skill surface) ← CAP-1
Scribe's capture/promotion path never writes to `.claude/skills/` (other skills), `.claude/scripts/`, `.claude/agents/`, `.mcp.json`, `recipes/`, `_bmad/`, or `_bmad-output/` outside its own project. `CLAUDE.md` edits (wiring the `@import`) remain human-driven, not automated. *(= legacy FR-7, scope note updated: Scribe's own package files are now an explicit exception since Scribe itself is code under `.claude/skills/` or a `src/` package — see `addendum.md` for the exact write-boundary list.)*

#### FR-8: Type taxonomy match ← CAP-1
`.claude/memory/` subdirectories are `feedback/`, `project/`, `reference/` — matching user-local memory's taxonomy; promotion defaults to the source entry's `type` unless a human reclassifies during review. *(= legacy FR-8)*

**Feature-specific NFRs:**
- Manual-only invocation in Wave 1 (`scribe capture` is explicit, not hook-triggered) — inherited from legacy FR-9/D4; no `Stop`/`SessionEnd`/`PreCompact` hook registered by Wave 1 or Wave 2.

**Notes:** `[NOTE FOR PM]` — the legacy spec's Q3 (what happens to the `## BMAD ↔ conda-forge-expert integration` section currently duplicated in root `CLAUDE.md`) defaulted to "remove — single source of truth in `.claude/memory/`." This PRD carries that default forward but flags it as a human-reviewed edit at Wave 1 implementation time, not something Scribe's tooling does automatically (consistent with FR-7).

### 4.2 Graph Compile (Wave 2 — the unbuilt core)

**Description:** `scribe graph compile --nightly` reads the tools the team already uses and compiles them into a graph — artifacts as nodes, references as edges — on a cadence, without anyone hand-maintaining a separate app. This is Sentinel's core claim, finally given an owner. Realizes UJ-3.

#### FR-9: Nightly compile reads named tool surfaces ← CAP-2
`scribe graph compile --nightly` ingests, at minimum: `.claude/memory/` (team memory), `.memlog.md` files across BMAD projects, git commit/PR history, retro outputs, CHANGELOGs, and `docs/dreams/`. The exact v1 input list is confirmed at architecture/epics time (see Open Questions); this FR fixes the *shape* (multiple named, already-existing tool surfaces — not a new authored-content app) as binding.

**Consequences (testable):**
- Running the compile step against a repo state with entries in each named surface produces graph nodes traceable to their source file and line/commit.
- Running the compile step with no new source activity since the last run is idempotent (no duplicate nodes, no spurious edges).

#### FR-10: Fact supersession, not deletion ← CAP-2
When the compile step detects a new record that supersedes an older one (e.g., a new decision superseding a prior one per the ADR "never edit in place, link instead" convention), the graph invalidates the old fact's validity rather than deleting the node — conceptually borrowed from Graphiti's bi-temporal model per the domain research, without adopting its storage engine.

**Consequences (testable):**
- A capture that explicitly supersedes a prior record (naming it) results in the old record remaining queryable (marked superseded) rather than vanishing from the graph.

#### FR-11: Compile is unattended and idempotent ← CAP-2
The compile step runs without interactive input and produces the same graph state given the same source inputs, regardless of how many times it is re-run (subject to source-content changes).

**Feature-specific NFRs:**
- Storage engine is unspecified by this PRD (see §8 Open Questions and the domain research's KuzuDB-archival/LadybugDB-immaturity finding) — FR-9/10/11 are engine-agnostic capability contracts, not implementation mandates.
- Compile must complete without requiring network reachability beyond the local repo (air-gap NFR, §"Constraints and Guardrails").

### 4.3 Recall (Wave 2 — the answer surface)

**Description:** `scribe recall <query>` answers from the compiled graph so a session starts already knowing what the team knows, with every answer traceable to the record it's grounded in. Realizes UJ-2.

#### FR-12: Recall returns a grounded, cited answer ← CAP-3
`scribe recall "<natural-language query>"` returns an answer derived from the compiled graph, with an explicit citation (file path / capture ID / commit) to the specific record(s) the answer is grounded in.

**Consequences (testable):**
- Every `scribe recall` response includes at least one citation resolvable to a real file/record in the repo.
- A query with no relevant graph coverage returns an explicit "no grounded answer found" rather than a fabricated one.

#### FR-13: Recall is queryable by any session, any operator ← CAP-3
`scribe recall` works identically regardless of which human operator or which concurrent agent worktree invokes it — the compiled graph is the single shared source, not per-session state.

**Out of Scope:**
- Benchmark parity claims (LoCoMo/LongMemEval-style recall-accuracy scoring) against Mem0/Zep — explicitly not claimed per the brief's "What Makes This Different."

**Feature-specific NFRs:**
- No required external LLM API call for `scribe recall` to function in an air-gapped deployment — local-model or no-model (pure retrieval + citation) fallback must exist. *(See Open Questions — the "local LLM required?" question is unresolved at PRD time.)*

### 4.4 Package & CLI Surface

**Description:** Scribe ships as `pyforge-scribe` (dist name), `pyforge.scribe` (module), `scribe` (CLI entry point) — a pixi-workspace member package, installable and importable like any other package in this monorepo's dual-ecosystem model.

#### FR-14: CLI is the public contract ← CAP-4
`scribe capture`, `scribe graph compile --nightly`, and `scribe recall` are the three top-level commands; each is independently invocable and independently testable. Sub-flags (`--type`, `--text`, `--promote`, `--nightly`) extend without breaking the top-level contract.

#### FR-15: Pixi workspace membership ← CAP-4
Scribe is registered as a pixi workspace member (per this repo's dual-ecosystem, multi-package pattern), with its own `pyproject.toml`/`recipe.yaml` posture consistent with sibling pyforge-* packages (Warden, Herald) once they exist as precedent.

#### FR-16: The session contract reaches every harness from one file ← CAP-27
`AGENTS.md` is the only place the cross-tool contract is written; Claude Code reaches it through the
`CLAUDE.md` `@AGENTS.md` import, Gemini through `.gemini/settings.json` `context.fileName`, VS Code
chat through `chat.useAgentsMdFile`, and Cursor / Codex / the Copilot cloud agent / Devin / Jules
natively. Per-tool files are addenda; team memory is cited as `.claude/memory/` paths that exist and
filled with `scribe capture`. A scribe meta-test reds a missing pointer, a duplicated section, an
oversized per-tool file or a dangling memory path.

#### FR-17: `scribe capture` and `scribe recall` run from the session default environment ← CAP-28
The scribe core package is a member of the `pyforge-guild` feature (the default every harness's
sandbox installs); the compile extras stay in `-e pyforge-scribe`. FR-13's "any session, any
operator" now reads **any harness**.

**Feature-specific NFRs:**
- **Language/Runtime:** Python, matching this repo's existing pixi environments; no new language introduced.
- **Versioning:** semver; CLI subcommand additions are MINOR, breaking flag/output-format changes are MAJOR — consistent with this repo's existing skill/package versioning discipline (e.g., conda-forge-expert's CHANGELOG convention).

## 5. Non-Goals (Explicit)

- **No ambient/automatic capture.** Scribe does not passively mine chat logs, Slack, or session transcripts for decisions — capture is always a deliberate, authored action (`scribe capture`). This is a permanent design stance, not a Wave 1 limitation (distinguishes Scribe from Mem0's conversation-extraction model per the market research). *(Amended 2026-08-22 by `spec-scribe-mines-raw-session-transcripts` / Epic 3: raw session transcripts are now scanned to surface promotion **candidates** into the reviewed `capture --promote` flow — never auto-promoted — and join the compile sources with provenance. The review gate stands; the "never mines session transcripts" absolutism does not. See § Currency reconciliation.)*
- **No `Stop`/`SessionEnd`/`PreCompact` hook automation** in Wave 1 or Wave 2 — inherited from the legacy spec's D4/NG2. A future wave may revisit this; it is out of scope here.
- **No cross-repo synchronization.** Each repo's Scribe instance is self-contained (legacy spec NG5, reaffirmed).
- **No plugin/marketplace packaging** until a second consumer repo exists (legacy spec NG3/D5, reaffirmed).
- **No claimed recall-accuracy benchmark parity** with Mem0/Zep/Graphiti — Scribe has not been evaluated against LoCoMo/LongMemEval and does not claim to beat them; its differentiation is git-native/air-gap/capture-as-you-decide, not raw retrieval performance (per market research recommendation #3).
- **No commitment to a specific graph storage engine in this PRD** — genuinely deferred to the architecture phase per domain research (§8 Open Questions).
- **No general-purpose enterprise knowledge-search product.** Scribe does not attempt Glean's cross-SaaS-connector breadth; it is repo-scoped by design.
- **No TTL/decay/staleness auto-scoring on entries** (legacy spec NG7, reaffirmed) — humans prune; Scribe surfaces staleness signals (a compile-time flag) but does not auto-delete.

## 6. Scope & Execution Model

### 6.1 In Scope: Wave 1 + Wave 2

**Wave 1 — Team Memory (Capture & Promotion), FR-1 through FR-8:** the full migrated `claude-team-memory` scope — `.claude/memory/` scaffold, promotion workflow, `CLAUDE.md` wiring, seed promotion of the two existing BMAD↔CFE feedback rules as the end-to-end proof. This wave can ship largely as markdown + a thin skill/CLI wrapper, reusing the legacy spec's design near-verbatim (see §9 supersession note — the "no new Python scripts" constraint is relaxed only where the CLI package skeleton requires it, not for Wave 1's actual logic).

**Wave 2 — Graph Compile & Recall, FR-9 through FR-13:** the previously-unbuilt core. Requires an architecture-phase decision on the graph storage engine (§8) before story-level breakdown can be precise about "how," though the capability contract (FR-9–13) is fixed now.

**Cross-cutting — Package & CLI Surface, FR-14/15:** spans both waves; the CLI skeleton (three top-level commands) should exist from Wave 1's start even if Wave 2's commands are stubs initially, so the public contract doesn't change shape between waves.

### 6.2 Out of Scope for MVP

- Hook-based automatic capture triggers — deferred indefinitely pending Wave 1/2 proving the manual workflow (legacy spec's Q11).
- Plugin/marketplace packaging — deferred until a second consumer repo (legacy spec's Q12).
- `.claude/agents/*.md` / `.mcp.json` registration of unrelated tools — independent surface, out of scope (legacy spec's Q13, reaffirmed as not Scribe's concern).
- Two-way sync between user-local and team memory — promoted entries stay canonical in team memory; user-local pointer stubs are read-only after promotion (legacy spec Q17).
- A browser/web UI for recall — CLI-first for v1; a UI is a plausible future wave, not committed here.

## 7. Success Metrics

**Primary**
- **SM-1**: `scribe capture` used at ≥1 real decision point within the first month after Wave 1 ships (not retrofitted demo data). Validates FR-1, FR-3.
- **SM-2**: `scribe recall` returns a grounded, cited answer to a real "why did we..." question within the first month after Wave 2 ships. Validates FR-12.

**Secondary**
- **SM-3**: 100% of promoted team-memory entries carry the correct pointer-stub + `promoted: true` marker in user-local memory after promotion (idempotency spot-check). Validates FR-5, FR-6.
- **SM-4**: `scribe graph compile --nightly` completes unattended, with zero manual intervention, across at least 4 consecutive scheduled runs post-Wave-2. Validates FR-11. *(Met 2026-08-27 by Story 3.3: the verb is the schedulable unit per the herald Story-13.5 pattern; the documented, opt-in operator crontab entry in `src/shared/packages/pyforge-scribe/docs/cli-runbooks.md` is the trigger and the evidence — the transcript scan is bounded (caps/timeout/mtime-cache, DW-FU-3-2-2 closed), overlapping runs skip via a non-blocking store lock, and the live-repo compile was verified terminating (5.2s cold / 2.7s cache-served, byte-identical rerun). The 4-consecutive-runs count accrues on the operator machine's cron log.)*
- **SM-5**: Zero required network calls observed during a `scribe capture` / `scribe graph compile` / `scribe recall` invocation run with network access blocked (air-gap functional test). Validates the air-gap NFR.

**Counter-metrics (do not optimize)**
- **SM-C1**: Number of `.claude/memory/` entries promoted. A high count with low `scribe recall` usage indicates hoarding, not value — do not treat entry count alone as success. Counterbalances SM-1/SM-3.
- **SM-C2**: `scribe graph compile` runtime. Do not optimize compile speed at the expense of FR-10's supersession correctness (a fast but lossy compile is worse than a correct, slower one). Counterbalances SM-4.

## 8. Open Questions

*(All six were resolved or re-scoped post-ship — dated dispositions in § Currency reconciliation — 2026-08-26. Preserved below as written 2026-07-25.)*

1. **Graph storage engine** — embedded graph database (e.g., LadybugDB, successor to the now-archived KuzuDB) vs. a flat-file/index model extending `.claude/memory/MEMORY.md`'s existing pattern. Domain research flags this as genuinely undecided; resolve at architecture phase, ideally via an ADR captured through Scribe itself once `scribe capture` exists (dogfooding opportunity).
2. **Wave 2's exact v1 input surface for `scribe graph compile`** — FR-9 fixes the shape (git history, memlogs, retros, CHANGELOGs, team memory, `docs/dreams/`) but the precise file-glob/inclusion list is a PRD-to-epics scope decision, not resolved here.
3. **Does `scribe recall` require a local LLM, or can v1 ship as pure grounded retrieval (return the matching record + citation, no generative synthesis)?** Air-gap posture favors the latter as a safer v1 default; unresolved here, flagged for architecture.
4. **Naming/interop with the ADR convention** — should `scribe capture --type decision` formally adopt the `docs/adr/`-style numbering/format the domain research found as dominant practice, or keep its own vocabulary that happens to be ADR-shaped? Affects whether Scribe should also *read* any pre-existing `docs/adr/`-style files in a target repo. **ANSWERED 2026-09-09, folded in here 2026-09-14: NO ADR numbering — and it is a Non-goal, not a deferral.** `scribe capture --type` stays **closed at `{feedback, project, reference}`** because AD-3 requires byte-identical shape parity with Claude Code's user-local auto-memory schema (CAP-1's own success criterion), and a fourth `decision` type would break that parity for a naming convention Scribe can already express inside the three it has. **Consequence for this document, recorded not hidden: UJ-1 above writes `scribe capture --type decision`, which is not a valid invocation as shipped** — `CaptureType = Literal["feedback", "project", "reference"]` (`models.py:34`), verified live 2026-09-14. UJ-1's *substance* (capture a decision at the moment it is made, git-diffable, reviewable in the next PR) is fully delivered; only its literal command line is wrong, and it is left as written with this pointer rather than silently edited, because the journey is the historical record of what was asked for.
5. **`anthropics/claude-code#38536` (native team-shared memory)** — if Anthropic ships first-class team memory during Scribe's build, does `.claude/memory/`'s file-based layer get absorbed into the native surface, leaving Scribe's value entirely in graph-compile + recall? Watch-item, not a blocker.
6. **Legacy `CLAUDE.md` §"BMAD ↔ conda-forge-expert integration" de-duplication (Q3 from the legacy spec)** — defaults to "remove, single source of truth in `.claude/memory/`" but is a human-reviewed edit, not an automated one; confirm at Wave 1 implementation.

## 9. Decisions & Assumptions (unattended intake)

Recorded here because this PRD was produced headless, without interactive confirmation — each should be treated as a default the first human reviewer can override, not a settled fact.

- **D-1 (supersession).** The legacy `claude-team-memory` spec's D7/NG9 ("no new Python scripts; entire feature is markdown") is superseded for Wave 2 and for the CLI package skeleton in Wave 1 — Scribe's charter (`ecosystem-crew.md`, `pyforge-scribe.md`) is explicit that it ships as a real installable package with a CLI, not a markdown-only skill. Wave 1's actual promotion *logic* can still be minimal/markdown-first; the supersession is about the existence of a package/CLI surface, not a mandate to over-engineer Wave 1.
- **D-2.** `{project_name}` in this project's file/folder naming resolves to the project slug `pyforge-scribe`, not the host repo's global `local-recipes` project_name — consistent across the brief, this PRD, and (pending) the architecture/epics artifacts.
- **D-3.** The two existing BMAD↔CFE feedback rules (already named in the legacy spec's Story 6) remain the Wave 1 seed-promotion proof; no new seed content was invented for this PRD.
- **D-4.** Air-gap posture is elevated from an implicit property to an explicit, testable NFR (SM-5) because both research reports independently flagged it as Scribe's primary durable differentiator, not incidental.
- **[ASSUMPTION 9.1]** Wave 1 and Wave 2 are sequential (Wave 2 depends on Wave 1's `.claude/memory/` layer existing as one of its compile inputs), not parallel tracks — reflected in §6.1's ordering.
- **[ASSUMPTION 9.2]** `scribe recall`'s output format (plain text vs. structured JSON vs. both) is left unspecified at PRD level; treated as an architecture/API-contract decision, not a product decision, since no user-facing product requirement distinguishes them at this stage.

## 10. Why Now

Timing is load-bearing on three independent fronts, per the research reports:

1. **The pain is dated and specific, not hypothetical.** The `d43899c1cb` duplication incident is a real, recent motivating event, not a hypothetical scenario — team memory is needed now, not eventually.
2. **Domain practice is independently converging on the same thesis.** 2026 ADR guidance is reframing decision records as agent-context infrastructure ("AI coding agents will refactor away reasoning they can't see") — Scribe rides an existing current rather than pioneering an unproven one.
3. **The regulatory clock is real.** The EU AI Act's high-risk-system obligations become binding 2026-08-02; a proposed delay was floated but not enacted into law. If Scribe's air-gap posture is to be credible as an enterprise value proposition later, building it in from day one (not retrofitting) is cheaper now than after Wave 1/2 ship without it.

## 11. Risks & Mitigations

- **Risk: Wave 1 ships but capture never happens in practice (the tool exists, nobody uses it).** Mitigation: SM-1 is the primary success metric specifically because it tests real usage, not feature completeness; if it fails within the first month, Wave 2 should not proceed until Wave 1's adoption gap is understood.
- **Risk: graph-compile storage engine choice locks in prematurely on an immature or soon-abandoned dependency** (the KuzuDB archival is direct precedent). Mitigation: FR-9/10/11 are written as engine-agnostic capability contracts; the architecture phase should explicitly weigh a flat-file fallback, not default to the newest embedded-graph library by reflex.
- **Risk: "air-gap posture" is claimed but not actually met** (e.g., a dependency silently phones home). Mitigation: SM-5 is a testable functional check (network-blocked run), not a documentation claim.
- **Risk: recall answers are ungrounded/hallucinated**, undermining the entire trust premise. Mitigation: FR-12's citation requirement is binding, and the "no grounded answer found" fallback is an explicit consequence, not an edge case left to implementation discretion.
- **Risk: legacy-spec supersession (D-1) is read as scope creep by a future reviewer.** Mitigation: D-1 is recorded explicitly with rationale, not silently implied — a reviewer who disagrees has a specific decision to challenge, not an ambiguous drift to reverse-engineer.

## 12. Assumptions Index

- [ASSUMPTION 9.1] — Wave 1 → Wave 2 sequencing (§9).
- [ASSUMPTION 9.2] — `scribe recall` output format left to architecture (§9).
- Inline in §0/throughout — `{project_name}` resolved to the project slug `pyforge-scribe` rather than the repo-global config value, per D-2.

## 13. References

- `_bmad-output/projects/pyforge-scribe/planning-artifacts/briefs/brief-pyforge-scribe-2026-07-25/brief.md` — product brief this PRD builds on.
- `_bmad-output/projects/pyforge-scribe/planning-artifacts/research/market-agent-team-memory-research-2026-07-25.md` — competitor analysis (Mem0, Zep/Graphiti, Khoj, Glean).
- `_bmad-output/projects/pyforge-scribe/planning-artifacts/research/domain-team-knowledge-graph-domain-research-2026-07-25.md` — ADR practice, local-first architecture, embedded graph storage, air-gap regulatory findings.
- `docs/specs/claude-team-memory.md` — legacy Tier-1 spec, ADOPTED; scope migrated into §4.1/§6.1 Wave 1. Will be marked superseded at merge time (not edited by this PRD).
- `docs/dreams/pyforge-scribe.md`, `docs/dreams/team-memory.md`, `docs/dreams/sentinel.md`, `docs/dreams/ecosystem-crew.md` § 7 — founding Dream documents.
- `docs/intake/sentinel/` — repatriated Build-Spec v2.1 evidence (the ancestor Sentinel effort, unshipped).
- `docs/intake/gists/llm-powered-knowledge-bases-by-andrej-karpathy/` — origin essay for the graph-compile loop's shape.

## Currency reconciliation — 2026-08-26

This PRD was cut 2026-07-25 and last content-reviewed 2026-08-04, before Scribe shipped. It is now reconciled against the canonical `spec-pyforge-scribe/SPEC.md` (status **shipped**; re-stamped 2026-08-22), the 2026-08-08 research refreshes, the Unifying Strategy pack (`spec-pyforge-unifying-strategy`, updated 2026-08-26), and the as-built code through 2026-08-26. The FR-1..FR-15 contract itself required no correction — every FR shipped as written (15/15 covered per `epics.md` Final Validation; epics 1–2, PRs #296/#301). What moved is everything around it:

**§8 Open Questions — dated dispositions.**
1. *Graph storage engine* — **resolved in stages.** Flat-file won v1 (`FlatFileGraphStore`, Story 2.1); no comparative spike ran — the flat-file/index model was adopted directly as the architecture's lowest-risk default (SPEC-scribe's own open question about that spike is answered: settled choice, not provisional). The engine question then stopped being binary: CAP-18 plugin registration (Epic 4, Story 4.1, 2026-08-24) made the store a hook surface with flat-file as default plugin; steward Epic 28 added `PostgresGraphStore` (pgvector, `scribe_schema`); steward 34.5 added `PlaneGraphStore` on the CAP-19 query plane (`atlas.duckdb`, 2026-08-26). **Operator decision 2026-08-26** (`query-plane-scribe-cutover`, strategy SPEC § Open Questions): **dual-write** — the plane store-port driver is primary and satisfies canopy FR-36 (semantic recall); `scribe_schema` pgvector stays written as the safety net until the plane has operating history; lexical recall may stay local. Note the port is a `typing.Protocol` (structural), not a concrete base class — the strategy SPEC's "no `GraphStore` class exists" phrasing refers to exactly this.
2. *Compile input surface* — **resolved: five named surfaces** (`.claude/memory/`, `**/.memlog.md`, git history capped at 100 commits, `**/*retro*.md`, `**/CHANGELOG.md`); `docs/dreams/` was cut from v1 despite FR-9 naming it — an explicit scope cut (2026-08-08 domain refresh argues for restoring it). Raw session transcripts joined as a sixth surface via Epic 3 (Story 3.2, 2026-08-22).
3. *Local LLM for recall* — **resolved: no.** v1 recall is deterministic lexical token-overlap with citation resolution on the return path; semantic recall arrived later (2026-08-25/26) behind the same port using deterministic local embeddings — still zero network, the air-gap NFR (SM-5) holds.
4. *ADR-format interop* — **resolved: Scribe kept its own 3-type taxonomy** (`feedback`/`project`/`reference`), byte-compatible with Claude Code auto-memory rather than `docs/adr/` convention; defensible, unexamined since (2026-08-08 domain refresh).
5. *`anthropics/claude-code#38536`* — **re-ranked to threat #1** (2026-08-08 market refresh): a leaked unreleased native sync engine is server-synced and last-write-wins; the answer to "does `.claude/memory/` fold into it?" is **coexist** — Scribe's reviewed promotion gate is the tier above native osmosis, not a casualty of it.
6. *CLAUDE.md BMAD↔CFE de-duplication* — **not exercised.** As of 2026-08-26 root `CLAUDE.md` still carries the full `## BMAD ↔ conda-forge-expert integration` section *and* team memory carries the promoted rule; the "remove, single source of truth" default remains an unexercised human edit. Accepted duplication, on record.

**§5 Non-Goals — one amendment.** The "no session-transcript mining, permanent" stance was amended by Epic 3 (see the dated note in §5): transcripts are mined only as reviewed promotion candidates and as a compile source — ambient auto-capture and hook automation remain non-goals as written.

**§7 Success metrics — status.** SM-1 met (seed promotion performed by the tool, pointer stub live 2026-08-07); SM-2 met (grounded, cited recall shipped; determinism proven with two independent store instances); SM-3 holds for every promotion to date; SM-5 holds (offline-conformance tests; deterministic local embeddings). **SM-4 remains unmet — no scheduler invokes the nightly compile** (RISK-2, 2026-08-08 technical report; still true 2026-08-26). *(Resolved 2026-08-27: Story 3.3 shipped the herald-13.5 pattern — the CLI verb is the schedulable unit, an opt-in operator-local `crontab` entry is the trigger; GitHub Actions stays disqualified because every input worth compiling (transcripts, `.claude/memory/`, the `.claude/data/` store) is operator-local. The transcript surface is bounded as a precondition (file/byte caps, per-file timeout, mtime-incremental scan cache — DW-FU-3-2-2 closed), overlapping runs skip via a non-blocking store lock, and a live-repo review finding was fixed en route: the repo-wide memlog/CHANGELOG/retro globs traversed `.git`/`.pixi`/worktree homes and made the verb non-terminating (>9 min for one surface); pruning-at-walk brought the full compile to 5.2s cold / 2.7s cached, byte-identical on rerun. Runbook + cron entry: `src/shared/packages/pyforge-scribe/docs/cli-runbooks.md`. SM-C2 respected — supersession semantics untouched.)* One classifier deviation on record: Story 1.5 delivered 1 of 2 seed entries at first pass (`_find_missing_repo_path()` stale-veto), accepted as correct classify-then-confirm behavior.

**New requirements landed above this PRD's FR ceiling** (owned by their own specs, not retrofitted here): transcript scanner + compile source (spec-scribe-mines-raw-session-transcripts CAP-1..2, Epic 3); `GraphStore` as CAP-18 plugins (FR-45, Epic 4); SKF skill + persona ownership and the first portal slice (canopy FR-37/38, FR-10; Epic 5); durable PG driver + semantic recall (canopy FR-35/36, steward Epic 28); plane ranking (FR-50, steward 34.5). Scribe's five-tier station shape (CLI, portal, MCP face, skill, persona) was declared complete 2026-08-26 (strategy Epic 37.1, 40/40).

**Carried risk, unchanged:** `promote.py` (the only write path outside `.claude/memory/`) has still never received an adversarial review (RISK-1, open since the Story 1.3 dangling-commit recovery).

## Currency reconciliation — 2026-09-04

*Chain-currency sweep re-fired: `specs/spec-pyforge-scribe/`'s `.memlog` moved to
2026-09-03T20:35 while this PRD sat at 2026-08-27, past the runbook's 2-day grace window.
Reconciled against the two memlog entries since 2026-08-27, `epics.md` (updated
2026-08-31), and the as-built package (PR #1043).*

**What moved.** 2026-08-31: a surface reconcile recording the Epic 2–3 + Epic 6 delivery
and the cross-station integration already in the ledger — "No CAP text change".
2026-09-03: the fleet-hygiene surface restamp (post-#1038 `pixi lock`; "no new product
work"). Neither entry changes a CAP, so no FR-1..FR-15 text moves.

**Epic 6 (Stories 6.1–6.3, added to `epics.md` 2026-08-31) landed above this PRD's FR
ceiling** — the `compile_surface` extras (graphify + cocoindex behind the CAP-18 ports,
incremental refresh, the graph-node staleness flag). It binds the two "bind now" estate
pins in `spec-pyforge-unifying-strategy/stack.md` § *Estate leverage* and
`spec-marshal-token-economy` CAP-13 (its `epics.md` heading carries the binding); it joins
the 2026-08-26 list above of requirements owned by their own specs, not retrofitted here.

**No FR/content change required.** `updated:` bumped to record that the check ran.


## Platform floor — reconciled 2026-09-07

`pyforge-scribe` declares **`requires-python = ">=3.14"`**. Raised from `>=3.12` by
marshal Story 32.2 (`spec-fleet-consistency-standard` CAP-5) and folded in here because it
is a product-visible constraint, not an implementation detail: it states which interpreters
this package may be installed onto.

The prior `>=3.12` was an untested claim. `pixi.toml` pins
`python = ">=3.14.7,3.14.*"` and every env-scoped pin in the workspace is `3.14.*`, so no
environment in this repo has ever installed, built or exercised this package on 3.12 — the
floor asserted a compatibility nothing verified. Declaring an untested floor is the same
failure mode as a fabricated test-architecture document: it reads as verified to the next
agent. There is no `recipes/pyforge-scribe/`, so the package is built by `pixi-build-python`
for this estate and is not published to conda-forge; no external consumer depended on the
wider floor.


## Currency reconciliation — 2026-09-14

*Chain-currency sweep: `spec-pyforge-scribe`'s SPEC.md moved to 2026-09-12 and its
`.memlog` to 2026-09-13T12:24 while this PRD sat at 2026-09-07 — five days, past the
runbook's 2-day grace window.*

**The Spec closed its own § Open Questions entirely.** All three (the GraphStore-engine
spike, the nightly input-glob enumeration, ADR interop) were answered on 2026-09-09, the
section was **deleted**, and `open_questions: []` was set. This PRD's § 8 had already
dispositioned its six on 2026-08-26, so the two documents now agree — but two of the
Spec's answers add something this PRD did not have, and both are folded in:

1. **ADR numbering is a decided Non-goal (§ 8 item 4, amended above).** `--type` stays
   closed at `{feedback, project, reference}` because AD-3 requires byte-identical
   shape parity with Claude Code's auto-memory schema. **This makes UJ-1's literal
   command line (`--type decision`) unrunnable as shipped** — verified live against
   `models.py:34`. Recorded at UJ-1's own § 8 entry rather than edited away.
2. **The GraphStore port question is closed by evidence, not by a spike.** The Spec now
   records "three drivers now sit behind it and the port still fixes nothing beyond
   itself." Verified live this pass: `graph_store.py`, `graph_store_pg.py`,
   `graph_store_plane.py`, plus `graph_store_plugins.py`. § 8 item 1 asked which engine
   to pick; the answer is that the port made the question unnecessary — three engines
   coexist and no PRD-level choice was ever owed.

**A second real divergence, found by reading SM-4 against the code.** § 7's **SM-4**
states that "the documented, opt-in operator crontab entry in
`src/shared/packages/pyforge-scribe/docs/cli-runbooks.md` is the trigger and the
evidence." That is **no longer how the nightly compile fires.** Story 8.1 replaced the
hand-typed crontab line with a **checked-in systemd-user timer** plus its installer and
a freshness check — verified live: `src/shared/packages/pyforge-scribe/ops/systemd/pyforge-scribe-nightly-compile.timer`,
`scripts/scribe_install_nightly_trigger.py`, `scripts/scribe_nightly_trigger.py`,
`scripts/scribe_graph_freshness_check.py`. SM-4's *criterion* (four consecutive
unattended runs) is unchanged and still correct; only its named trigger and evidence
source are stale. **Not rewritten here**: SM-4 is a success metric whose evidence trail
matters, and replacing the sentence would erase the fact that the crontab era existed
and was superseded. The correction is this paragraph; a future edit that re-words SM-4
should cite it.

**An ownership ruling worth carrying, because it prevents a duplicate capability.** The
Spec now states **"Not canopy:CAP-14"**: the Unifying-Strategy semantic-recall capability
belongs to **steward Story 49.7**, and no parallel scribe-side CAP is minted for it.
Charter §5 decides it — the owner of the outcome writes the story, the owner of the
mechanism owns the verb it calls. Scribe owns the mechanism (`recall`); it does not own
steward's outcome. No FR is added here for the same reason.

**Four new governed script surfaces, all already-landed work.** `scripts/scribe_pg.py`
(the local PostgreSQL+pgvector the durable GraphStore tests require),
`scripts/scribe_nightly_trigger.py`, `scripts/scribe_install_nightly_trigger.py` and
`scripts/scribe_graph_freshness_check.py` joined the Spec's `surface:`. They are
infrastructure for FR-11's nightly compile, which this PRD already specifies; no new FR.

**Ledger state at this stamp** (measured with `fleet_scan.parse_sprint_status`, not a
regex): **35/35 stories `done` across 18/18 epics.**

**Content changed:** § 8 item 4 (dated answer folded in, with the UJ-1 consequence
named). No FR added, renumbered or removed.

## Currency reconciliation — 2026-09-19

*Chain-currency cascade: the brief re-stamped 2026-09-19 after the multi-harness research
(`research/multi-harness-instruction-surface-2026-09-19.md`); this PRD follows in the same commit.*

Two FRs added above from `spec-pyforge-scribe` CAP-27 and CAP-28 (minted 2026-09-19 at the review
of PR #1513; Epic 19 / Stories 19.1–19.2, both landed in that PR). FR-13 widens from "any session,
any operator" to "any harness". No existing FR changes; § 5 Non-Goals unchanged (the instruction
surface is repo-scoped, air-gapped and manual-invocation like everything else here). The seven
later items on the Dream entry (size discipline, skills path, non-Claude transcript ingestion,
recall over MCP, pointer files in `governance-currency`, per-spec baselines, Devin / Copilot
analogues) are not FRs until a `bmad-spec` pass mints their CAPs.

## Currency reconciliation — 2026-09-20 (fleet consistency pass)

*Operator ruling 2026-09-20: every station's PRD, spine and epics are re-stamped in the same pass,
grace period or not, so the whole chain reads current for the foundry cutover. Trigger: the
station Spec's `.memlog.md` gained a 2026-09-20 event — the fleet consistency pass reconciled every
tracked story spec's frontmatter against the sprint ledger, matched each "Ledger status" line,
reconstructed missing Auto Run Results from `main`'s landing commits, fixed invalid frontmatter,
and let `sprint-ledger-sync` roll the epic keys up (`spec→prd` cascade). Bookkeeping only:
no requirement, decision, story or AD changes in this PRD. `updated:` bumped to record that the
check ran.*

## Currency reconciliation — 2026-09-25

`spec→prd` edge: `spec-pyforge-scribe`'s `.memlog.md` moved to 2026-09-24T20:28 while this PRD
sat at 2026-09-20.

**What moved, and why the FR delta is none.** Two entries from marshal Story 46.3: `AGENTS.md`,
`GEMINI.md` and `.github/copilot-instructions.md` gained the session-close ritual statement
(`scribe capture`, with its capture hygiene), and the parity meta-test gained two assertions
guarding it. Both sit inside CAP-27's existing instruction-surface parity contract (FR-16);
nothing new is required of Scribe. `updated:` bumped to record that the check ran.
