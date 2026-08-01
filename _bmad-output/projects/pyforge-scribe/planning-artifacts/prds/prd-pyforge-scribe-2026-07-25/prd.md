---
title: pyforge-scribe
created: 2026-07-25
updated: 2026-08-04
status: final
currency_review: Reviewed 2026-08-04 — spec/brief timestamp bump was structural (project relocation / memlog story-completion recording), not content drift; PRD unchanged.
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

#### FR-1: Frontmatter schema parity
Entries in `.claude/memory/` use the same frontmatter fields as user-local auto-memory (`name`, `description`, `type` ∈ `{feedback, project, reference}`), so migration in either direction is mechanical. *(= legacy FR-1)*

**Consequences (testable):**
- A `.claude/memory/<type>/*.md` file with a missing or malformed `type` field fails a schema check.
- Promotion tooling reads and writes this exact schema without a translation step.

#### FR-2: MEMORY.md index size discipline
`.claude/memory/MEMORY.md` stays under 200 lines (Claude Code truncates beyond that); enforced by convention (entries are one-line `- [Title](file.md) — hook`), no tooling gate in Wave 1. *(= legacy FR-2)*

#### FR-3: Proposal-then-confirm promotion
`scribe capture --promote` (or equivalent) stops after producing the proposed diff and waits for explicit confirmation before writing. No auto-commit, no unreviewed multi-file write. *(= legacy FR-3)*

**Consequences (testable):**
- Running the promotion path against a set of user-local entries produces a structured proposal (files + full content + updated `MEMORY.md`) and halts before any write.
- Nothing under `.claude/memory/` changes on disk until confirmation is given.

#### FR-4: Team-voice rewrite required
Promoted entries are rewritten per the team-voice rules (strip first-person, drop "user prefers" framing, drop incident-specific anecdotes, preserve **Why:**/**How to apply:** structure, preserve paths/commands/identifiers verbatim) — never a verbatim copy. *(= legacy FR-4)*

#### FR-5: Pointer stub after promotion
After confirmation, the source user-local entry is replaced with the pointer-stub format (`promoted: true` + redirect body naming the promoted file's path and date) — not deleted, preserving traceability. *(= legacy FR-5)*

#### FR-6: Detect already-promoted entries (idempotency)
The promotion workflow detects `promoted: true` frontmatter and skips re-classification/re-promotion. Repeated invocation is a no-op against already-promoted entries. *(= legacy FR-6)*

#### FR-7: Read-only outside `.claude/memory/` (and Scribe's own package/skill surface)
Scribe's capture/promotion path never writes to `.claude/skills/` (other skills), `.claude/scripts/`, `.claude/agents/`, `.mcp.json`, `recipes/`, `_bmad/`, or `_bmad-output/` outside its own project. `CLAUDE.md` edits (wiring the `@import`) remain human-driven, not automated. *(= legacy FR-7, scope note updated: Scribe's own package files are now an explicit exception since Scribe itself is code under `.claude/skills/` or a `src/` package — see `addendum.md` for the exact write-boundary list.)*

#### FR-8: Type taxonomy match
`.claude/memory/` subdirectories are `feedback/`, `project/`, `reference/` — matching user-local memory's taxonomy; promotion defaults to the source entry's `type` unless a human reclassifies during review. *(= legacy FR-8)*

**Feature-specific NFRs:**
- Manual-only invocation in Wave 1 (`scribe capture` is explicit, not hook-triggered) — inherited from legacy FR-9/D4; no `Stop`/`SessionEnd`/`PreCompact` hook registered by Wave 1 or Wave 2.

**Notes:** `[NOTE FOR PM]` — the legacy spec's Q3 (what happens to the `## BMAD ↔ conda-forge-expert integration` section currently duplicated in root `CLAUDE.md`) defaulted to "remove — single source of truth in `.claude/memory/`." This PRD carries that default forward but flags it as a human-reviewed edit at Wave 1 implementation time, not something Scribe's tooling does automatically (consistent with FR-7).

### 4.2 Graph Compile (Wave 2 — the unbuilt core)

**Description:** `scribe graph compile --nightly` reads the tools the team already uses and compiles them into a graph — artifacts as nodes, references as edges — on a cadence, without anyone hand-maintaining a separate app. This is Sentinel's core claim, finally given an owner. Realizes UJ-3.

#### FR-9: Nightly compile reads named tool surfaces
`scribe graph compile --nightly` ingests, at minimum: `.claude/memory/` (team memory), `.memlog.md` files across BMAD projects, git commit/PR history, retro outputs, CHANGELOGs, and `docs/dreams/`. The exact v1 input list is confirmed at architecture/epics time (see Open Questions); this FR fixes the *shape* (multiple named, already-existing tool surfaces — not a new authored-content app) as binding.

**Consequences (testable):**
- Running the compile step against a repo state with entries in each named surface produces graph nodes traceable to their source file and line/commit.
- Running the compile step with no new source activity since the last run is idempotent (no duplicate nodes, no spurious edges).

#### FR-10: Fact supersession, not deletion
When the compile step detects a new record that supersedes an older one (e.g., a new decision superseding a prior one per the ADR "never edit in place, link instead" convention), the graph invalidates the old fact's validity rather than deleting the node — conceptually borrowed from Graphiti's bi-temporal model per the domain research, without adopting its storage engine.

**Consequences (testable):**
- A capture that explicitly supersedes a prior record (naming it) results in the old record remaining queryable (marked superseded) rather than vanishing from the graph.

#### FR-11: Compile is unattended and idempotent
The compile step runs without interactive input and produces the same graph state given the same source inputs, regardless of how many times it is re-run (subject to source-content changes).

**Feature-specific NFRs:**
- Storage engine is unspecified by this PRD (see §8 Open Questions and the domain research's KuzuDB-archival/LadybugDB-immaturity finding) — FR-9/10/11 are engine-agnostic capability contracts, not implementation mandates.
- Compile must complete without requiring network reachability beyond the local repo (air-gap NFR, §"Constraints and Guardrails").

### 4.3 Recall (Wave 2 — the answer surface)

**Description:** `scribe recall <query>` answers from the compiled graph so a session starts already knowing what the team knows, with every answer traceable to the record it's grounded in. Realizes UJ-2.

#### FR-12: Recall returns a grounded, cited answer
`scribe recall "<natural-language query>"` returns an answer derived from the compiled graph, with an explicit citation (file path / capture ID / commit) to the specific record(s) the answer is grounded in.

**Consequences (testable):**
- Every `scribe recall` response includes at least one citation resolvable to a real file/record in the repo.
- A query with no relevant graph coverage returns an explicit "no grounded answer found" rather than a fabricated one.

#### FR-13: Recall is queryable by any session, any operator
`scribe recall` works identically regardless of which human operator or which concurrent agent worktree invokes it — the compiled graph is the single shared source, not per-session state.

**Out of Scope:**
- Benchmark parity claims (LoCoMo/LongMemEval-style recall-accuracy scoring) against Mem0/Zep — explicitly not claimed per the brief's "What Makes This Different."

**Feature-specific NFRs:**
- No required external LLM API call for `scribe recall` to function in an air-gapped deployment — local-model or no-model (pure retrieval + citation) fallback must exist. *(See Open Questions — the "local LLM required?" question is unresolved at PRD time.)*

### 4.4 Package & CLI Surface

**Description:** Scribe ships as `pyforge-scribe` (dist name), `pyforge.scribe` (module), `scribe` (CLI entry point) — a pixi-workspace member package, installable and importable like any other package in this monorepo's dual-ecosystem model.

#### FR-14: CLI is the public contract
`scribe capture`, `scribe graph compile --nightly`, and `scribe recall` are the three top-level commands; each is independently invocable and independently testable. Sub-flags (`--type`, `--text`, `--promote`, `--nightly`) extend without breaking the top-level contract.

#### FR-15: Pixi workspace membership
Scribe is registered as a pixi workspace member (per this repo's dual-ecosystem, multi-package pattern), with its own `pyproject.toml`/`recipe.yaml` posture consistent with sibling pyforge-* packages (Warden, Herald) once they exist as precedent.

**Feature-specific NFRs:**
- **Language/Runtime:** Python, matching this repo's existing pixi environments; no new language introduced.
- **Versioning:** semver; CLI subcommand additions are MINOR, breaking flag/output-format changes are MAJOR — consistent with this repo's existing skill/package versioning discipline (e.g., conda-forge-expert's CHANGELOG convention).

## 5. Non-Goals (Explicit)

- **No ambient/automatic capture.** Scribe does not passively mine chat logs, Slack, or session transcripts for decisions — capture is always a deliberate, authored action (`scribe capture`). This is a permanent design stance, not a Wave 1 limitation (distinguishes Scribe from Mem0's conversation-extraction model per the market research).
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
- **SM-4**: `scribe graph compile --nightly` completes unattended, with zero manual intervention, across at least 4 consecutive scheduled runs post-Wave-2. Validates FR-11.
- **SM-5**: Zero required network calls observed during a `scribe capture` / `scribe graph compile` / `scribe recall` invocation run with network access blocked (air-gap functional test). Validates the air-gap NFR.

**Counter-metrics (do not optimize)**
- **SM-C1**: Number of `.claude/memory/` entries promoted. A high count with low `scribe recall` usage indicates hoarding, not value — do not treat entry count alone as success. Counterbalances SM-1/SM-3.
- **SM-C2**: `scribe graph compile` runtime. Do not optimize compile speed at the expense of FR-10's supersession correctness (a fast but lossy compile is worse than a correct, slower one). Counterbalances SM-4.

## 8. Open Questions

1. **Graph storage engine** — embedded graph database (e.g., LadybugDB, successor to the now-archived KuzuDB) vs. a flat-file/index model extending `.claude/memory/MEMORY.md`'s existing pattern. Domain research flags this as genuinely undecided; resolve at architecture phase, ideally via an ADR captured through Scribe itself once `scribe capture` exists (dogfooding opportunity).
2. **Wave 2's exact v1 input surface for `scribe graph compile`** — FR-9 fixes the shape (git history, memlogs, retros, CHANGELOGs, team memory, `docs/dreams/`) but the precise file-glob/inclusion list is a PRD-to-epics scope decision, not resolved here.
3. **Does `scribe recall` require a local LLM, or can v1 ship as pure grounded retrieval (return the matching record + citation, no generative synthesis)?** Air-gap posture favors the latter as a safer v1 default; unresolved here, flagged for architecture.
4. **Naming/interop with the ADR convention** — should `scribe capture --type decision` formally adopt the `docs/adr/`-style numbering/format the domain research found as dominant practice, or keep its own vocabulary that happens to be ADR-shaped? Affects whether Scribe should also *read* any pre-existing `docs/adr/`-style files in a target repo.
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
