---
title: "Product Brief: pyforge-scribe"
status: "complete"
created: "2026-07-25"
updated: "2026-07-25"
inputs:
  - "docs/dreams/pyforge-scribe.md"
  - "docs/dreams/team-memory.md"
  - "docs/dreams/sentinel.md"
  - "docs/dreams/ecosystem-crew.md § 7 The Scribe"
  - "docs/specs/claude-team-memory.md (legacy Tier-1 spec — ADOPTED, scope migrates into this brief/PRD)"
  - "{project-root}/_bmad-output/projects/pyforge-scribe/planning-artifacts/research/market-agent-team-memory-research-2026-07-25.md"
  - "{project-root}/_bmad-output/projects/pyforge-scribe/planning-artifacts/research/domain-team-knowledge-graph-domain-research-2026-07-25.md"
  - "docs/intake/sentinel/ (Build-Spec v2.1 evidence, unshipped)"
  - "docs/intake/gists/llm-powered-knowledge-bases-by-andrej-karpathy/ (the compile-loop's origin essay)"
project_slug: "pyforge-scribe"
---

# Product Brief: pyforge-scribe

## Executive Summary

**Scribe** is the team's inward voice: a real, installable Python package (dist `pyforge-scribe`, module `pyforge.scribe`, CLI `scribe`) that captures decisions as they happen, compiles them nightly into a knowledge graph built from the tools the team already uses, and answers from that memory so every session — human or agent — starts already knowing what the team knows. It is the practical antidote to a diagnosis this codebase has now made twice: the Sentinel Dream (2026-04) found that "the knowledge the team runs on is scattered and lossy... AI without the graph hallucinates"; the team-memory Dream (2026-07) found the concrete, present-day instance of that same disease — Claude Code's auto-memory is per-machine and per-operator, invisible to teammates, with the only escape hatch a friction-laden manual edit of `CLAUDE.md` that people skip.

Scribe ships three capabilities as one CLI: `scribe capture` (an ADR-shaped decision, runbook, or rejected-tradeoff lands in the record at the moment it happens — not reconstructed later from Slack scrollback), `scribe graph compile --nightly` (the record, plus git history, memlogs, retros, and CHANGELOGs, compiles into a graph — nodes are artifacts, edges are references, built from real tools, never a separate app the team has to remember to update), and `scribe recall` (answer surfaces so a session starts grounded, not guessing).

Why now: 2026 domain practice independently arrived at the same thesis — ADRs are being reframed industry-wide as agent-context infrastructure ("AI coding agents will refactor away reasoning they can't see"), local-first tooling has normalized "no required cloud call" as a baseline developer expectation, and the EU AI Act's August 2026 high-risk deadline is turning air-gap posture from a niche preference into a real enterprise buying trigger. Scribe does not need to invent a category; it needs to be the git-native, local-first instance of a pattern the market (Mem0, Zep/Graphiti) and the domain (ADR tooling) are both converging on from opposite directions — SaaS-first agent memory on one side, static markdown-in-repo on the other — with nobody currently occupying the middle: compiled, curated, graph-shaped, and living entirely inside the repo.

Scribe is not a from-scratch bet. It formalizes three things already proven at small scale inside this exact codebase: the `bmad-spec` append-only memlog discipline, the personal auto-memory pipeline (30+ entries, `MEMORY.md` indexing), and the fully-specified but unbuilt `claude-team-memory` legacy spec (10 waved stories, unstarted) — whose entire scope migrates into this product as its capture-layer foundation (see Scope, below).

## The Problem

Three concrete, evidenced scenarios:

1. **Team-relevant knowledge is trapped per-operator.** Claude Code's auto-memory writes to a per-machine, per-user path (`~/.claude/projects/<encoded-path>/memory/`) — invisible to teammates and other agents by construction. The motivating incident recorded in the legacy spec: in commit `d43899c1cb`, the same rule had to be written *twice* — once to user-local memory, once by hand into `CLAUDE.md` — because there was no other way to make it team-visible. That duplication is the friction made visible; most rules never get promoted at all, they just live invisibly in one operator's memory.

2. **The graph is diagnosed but nobody compiles it.** The Sentinel Dream's 2026-04 finding — "an engineer touches six tools in the first hour; the knowledge the team runs on is scattered and lossy" — is unchanged 15 months later. The pieces that would compile into a graph already exist (git history, ADRs-in-waiting, memlogs, retros, CHANGELOGs) but nothing reads them together. Domain research confirms this is not unique to this repo: the dominant 2026 finding on ADR practice is that "ADRs often go stale because decisions don't stay in the file — they change in Slack, GitHub and Jira, and nobody updates the ADR."

3. **No answer surface grounded in what the team actually decided.** A new session (human or agent) starting cold has no way to ask "why did we drop Kùzu?" or "why does this recipe pin that version?" and get an answer traceable to a real decision record, as opposed to a plausible-sounding guess reconstructed from code alone.

The cost compounds specifically in this repo's operating model: it runs *multiple concurrent BMAD projects and agent sessions* (per `CLAUDE.md`'s multi-project pattern), so "what the team knows" has to survive not just across human operators but across parallel agent worktrees and loop runs — a failure mode ordinary single-user PKM tools were never built to solve.

## The Solution

Scribe is the plumbing for capture → compile → recall, built as three primitives:

- **`scribe capture`** — an authored action at decision time (`scribe capture --type decision --text "ADR-005b: in-house gateway replaces LiteLLM"`), not passive log ingestion. Entries are ADR-shaped: one decision per record, never edited in place — a changed decision gets a new record that supersedes and links the old one, so the chain of decisions is the value, exactly matching both the domain's existing ADR convention and the legacy spec's pointer-stub design (`promoted: true`, never delete, only supersede).
- **`scribe graph compile --nightly`** — reads the tools the team already uses (starting surface: `.claude/memory/`, `.memlog.md` files, git history/PR merges, retros, CHANGELOGs, `docs/dreams/`) and compiles them into a graph: artifacts as nodes, references as edges, built on a cadence, not authored by hand in a separate app. This is Sentinel's unbuilt core, finally given an owner and a repo-native (not SaaS) home.
- **`scribe recall`** — the answer surface (`scribe recall "why did we drop Kùzu?"`) — grounded in the compiled graph, cited to the record it answers from, so every session (human or agent) starts already knowing what the team knows instead of re-deriving it or hallucinating it.

Scribe absorbs and completes the legacy `claude-team-memory` spec rather than competing with it: that spec's `.claude/memory/` directory, its `team-memory` skill (proposal-then-confirm promotion from user-local to team memory, team-voice rewrite rules, pointer-stub convention, team-relevance test), and its 10 waved stories become Scribe's Wave 1 — the capture and curation layer the graph compiles from. The spec's own scope boundary is preserved: promotion stays proposal-then-confirm, never auto-commit; the human always reviews before team memory changes.

## What Makes This Different

Grounded directly in the market-research report's four-analogue comparison:

| Dimension | Mem0 (agent memory SaaS) | Zep/Graphiti (temporal KG, enterprise) | Khoj (self-hosted PKM) | Glean (enterprise search) | **Scribe** |
|---|---|---|---|---|---|
| Unit of memory | extracted conversational facts | temporal graph facts/entities | document embeddings | cross-SaaS connector graph | decisions/ADRs/runbooks (authored) |
| Compile trigger | per-turn (real-time) | real-time incremental | on-index (batch) | continuous crawl | authored capture + `--nightly` compile |
| Deployment | SaaS-first, open-core SDK | managed service (OSS engine, Neo4j-backed) | self-hosted OSS, 4-service stack | SaaS only | **git-native, local-first, air-gap-capable** |
| Team-native | No (per-agent, per-user) | Yes (enterprise, multi-agent) | No (personal vault) | Yes (org-wide) | **Yes (team, in-repo)** |
| Repo-native | No | No | No | No | **Yes** |

No competitor occupies all three of: (a) no required external service, (b) compiles from the team's own real tools rather than a separate ingestion app, (c) captured at decision time rather than mined from chat logs after the fact. Zep/Graphiti's bi-temporal fact-supersession model (facts invalidated, not deleted, when superseded) is the one piece of prior art worth deliberately architecting toward — Scribe borrows the pattern, not the Neo4j-and-managed-service deployment it ships in.

The unfair advantages are honest, not fabricated: (a) the capture habit is *already proven* at small scale inside this exact repo (30+ personal auto-memory entries, the memlog discipline, Dream realization logs) — Scribe formalizes a working pattern, it doesn't invent an unproven one; (b) the fully-scoped, unstarted `claude-team-memory` spec is a validated 10-story starting point, not a blank page; (c) domain practice (ADR discipline, local-first tooling norms, the EU AI Act's air-gap tailwind) is independently converging on the same shape, so Scribe is riding a current, not swimming against one.

There is no claimed recall-accuracy moat versus Mem0/Zep — their LoCoMo/LongMemEval benchmarks measure conversational recall, a different task than decision recall, and Scribe has not been evaluated against either. The moat is git-native + capture-as-you-decide + air-gap posture, not raw retrieval performance.

## Who This Serves

**Primary user — every developer (human or agent) working in this repo, today.** Currently: writes a correction, it lands in per-machine auto-memory, invisible to the next teammate or the next agent worktree. Success looks like: `scribe capture` at the moment of a decision, `scribe recall` at the start of the next session (by a different operator, or a different agent entirely) returning the answer with a citation to the record.

**Secondary user — a new contributor (human or agent) on day one.** No back-channel to the people who made the prior decisions. Success looks like: `scribe recall "why does this recipe pin that version"` returns a grounded answer instead of silence or a guess.

**Tertiary user — regulated/air-gapped teams evaluating agent-team-memory tooling.** Per the domain research, this segment is real and growing (EU AI Act August 2026 deadline; defense/finance/healthcare sectors explicitly locked out of Mem0/Zep/Glean's SaaS posture and Khoj's multi-service footprint). Not the initial build target, but the architectural constraint (no telemetry, no required registry reachability, no vendor cloud dependency) should hold from day one so this market is addressable without a rearchitecture later.

## Success Criteria

**The primary criterion:** within this repo, `scribe capture` is used at real decision points (not retrofitted demo data), and `scribe recall` returns a grounded, cited answer to a real "why did we..." question, within the first month of Wave 1 shipping. If capture doesn't happen at the moment of decision, the graph has nothing real to compile, and the whole product is inert.

Supporting criteria:

| Metric | Target | Why this matters |
|---|---|---|
| Team-memory migration completeness | All 10 legacy `claude-team-memory` stories land as Scribe Wave 1 scope (folded, not dropped) | The spec is validated, unstarted work — losing scope here re-derives what's already designed |
| `scribe recall` groundedness | Every answer cites the specific captured record it's grounded in | Un-cited recall is just another LLM guess; citation is the entire differentiation from a generic chatbot |
| Nightly compile reliability | `scribe graph compile --nightly` runs unattended and idempotently against the tools it reads | A graph that requires babysitting doesn't survive past week 2 |
| No required external service | 100% of v1 functionality works with zero network reachability | This is the testable definition of "air-gap-capable" per domain research — not merely "self-hostable" |
| Promotion discipline preserved | `scribe capture`/team-memory promotion stays proposal-then-confirm — zero auto-commits | Inherited invariant from the legacy spec (G3); breaking it breaks trust in the tool |

## Scope

**In for Wave 1 (the full legacy `claude-team-memory` migration, reframed as Scribe's capture/curate layer):**
- `.claude/memory/` directory + schema parity with user-local auto-memory (`feedback`/`project`/`reference` types).
- The promotion workflow (proposal-then-confirm, team-voice rewrite rules, team-relevance test, pointer-stub convention) — ported from a standalone skill into `scribe capture`'s promotion path.
- `CLAUDE.md` wiring (`@.claude/memory/MEMORY.md` import) so promoted entries auto-load every session.
- The seed promotion (the two existing BMAD↔CFE feedback rules) as the end-to-end proof.

**In for Wave 2 (the unbuilt core — `scribe graph compile`):**
- Nightly compile from the initial tool surface: `.claude/memory/`, `.memlog.md` files across BMAD projects, git history, retros, CHANGELOGs, `docs/dreams/`.
- Storage-engine decision deferred to the architecture phase (domain research flags this as genuinely open: embedded graph engine like LadybugDB vs. a flat-file/index model extending `.claude/memory/MEMORY.md`'s existing pattern) — Wave 2 scope should not assume the answer.
- `scribe recall` as the first consumer of the compiled graph.

**Explicitly out (inherited from the legacy spec's non-goals, still valid):**
- No `Stop`/`SessionEnd` hook automation — capture stays a deliberate, invoked action, not an ambient background process, at least through Wave 2.
- No cross-repo synchronization — each repo's Scribe instance is self-contained.
- No plugin/marketplace packaging until a second consumer repo exists.
- No claimed benchmark parity with Mem0/Zep recall accuracy (see What Makes This Different).
- No commitment to a specific graph storage engine in this brief — genuinely open, architecture-phase decision.

## Vision

If this holds, Scribe becomes the thing every session — human or agent, in any of this repo's concurrent BMAD projects — starts by consulting, the way `CLAUDE.md` is consulted today but grounded in the team's actual decision history instead of a hand-maintained static file. The graph becomes queryable infrastructure other pyforge stations build on: Herald cites it when it renders a Dream into a deck; Marshal's dev-loop sessions recall relevant precedent before touching a story; Doctor's health monitoring can trace *why* a pin exists before flagging it as stale. Scribe does not need to become a general-purpose enterprise knowledge platform to succeed — it needs to remain the boring, reliable, git-native memory this specific factory runs on, provably better than the manual-`CLAUDE.md`-editing status quo it replaces. If the air-gap posture holds architecturally from day one, the same package becomes credible for exactly the regulated teams current market analogues cannot reach — not a pivot, just the natural reach of having built it correctly the first time.
