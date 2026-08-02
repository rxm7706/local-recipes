---
surface:
  - src/shared/packages/pyforge-scribe/**   # the CLI this Spec builds
id: SPEC-scribe
owner-dream: docs/dreams/pyforge-scribe.md
companions:
  - ../../architecture/architecture-pyforge-scribe-2026-07-25/ARCHITECTURE-SPINE.md
sources:
  - ../../../../../../docs/dreams/pyforge-scribe.md
  - ../../briefs/brief-pyforge-scribe-2026-07-25/brief.md
  - ../../prds/prd-pyforge-scribe-2026-07-25/prd.md
  - ../../prds/prd-pyforge-scribe-2026-07-25/addendum.md
  - ../../epics.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability only — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Scribe (pyforge-scribe) — the team's inward voice

## Why

A disease diagnosed twice, now given an owner: the Sentinel Dream (2026-04) found "the knowledge the team runs on is scattered and lossy"; the team-memory Dream (2026-07) found its present-day instance — Claude Code's auto-memory is per-machine, per-operator, invisible to teammates and other agent sessions, with the only escape hatch a friction-laden manual `CLAUDE.md` edit people skip (the `d43899c1cb` duplication incident is the dated, real motivating case). This repo's operating model compounds the cost: it runs multiple concurrent BMAD projects and agent worktrees, so "what the team knows" must survive across parallel sessions, not just human operators. Scribe (module `pyforge.scribe`, CLI `scribe`) is the team's inward voice — capture decisions as they happen, compile them nightly into a knowledge graph built from tools the team already uses, and answer from that memory so every session starts already knowing what the team knows. It is not a from-scratch bet: it formalizes the `bmad-spec` memlog discipline, the personal auto-memory pipeline, and fully absorbs the validated-but-unstarted legacy `claude-team-memory` spec (10 waved stories) as its Wave 1 foundation. The team-memory Dream itself (not just the legacy spec it pointed to) was consolidated into `docs/dreams/pyforge-scribe.md` on 2026-08-02 — its own Spec's three capabilities (memory is committed not personal, recall is scoped not a dump, entries carry provenance) map onto CAP-1/AD-1, CAP-3, and CAP-2 respectively, confirmed capability-by-capability rather than assumed; no new capability resulted (see `spec-team-memory`'s retirement record). As of that date Epic 1 is 3 of 5 stories shipped (1.1, 1.2, 1.3) and Epic 2 has not started.

## Capabilities

- **CAP-1**
  - **intent:** A developer or agent can capture a decision the moment it happens into checked-in team memory (`scribe capture`), and deliberately promote a team-relevant user-local memory entry into team memory with review (`scribe capture --promote`).
  - **success:** `.claude/memory/<type>/*.md` frontmatter (`name`/`description`/`type` ∈ `{feedback, project, reference}`) is schema-identical to user-local auto-memory; promotion halts after producing a structured proposal and writes nothing until explicit confirmation; a promoted entry is rewritten in team voice (never a verbatim copy), and its user-local source becomes a `promoted: true` pointer stub, never deleted; re-invoking promotion skips already-promoted entries; nothing is written outside `.claude/memory/`, Scribe's own package/graph-store paths, and the one pointer-stub exception.
- **CAP-2**
  - **intent:** `scribe graph compile --nightly` reads named tool surfaces the team already uses (`.claude/memory/`, `.memlog.md` files across BMAD projects, git history, retros, CHANGELOGs, `docs/dreams/`) and rebuilds the knowledge graph unattended, with a superseding capture invalidating — never deleting — the prior record.
  - **success:** Every node is traceable to its source file/commit; re-running compile with no new source activity yields an unchanged graph (no duplicate nodes, no spurious edges); a capture naming a prior record as superseded leaves that record queryable with ended validity, distinguishable from the current one; compile runs without prompting and without a human present.
- **CAP-3**
  - **intent:** A developer or agent can run `scribe recall <query>` to get an answer grounded in the compiled graph, identically regardless of which operator or concurrent agent worktree asks.
  - **success:** Every response carries at least one citation resolvable to a real file/record, or an explicit "no grounded answer found" result — never a fabricated or generic answer; two different callers querying the same repo state get the identical answer, since the graph is the single shared source, not per-session state.
- **CAP-4**
  - **intent:** Scribe ships as an installable, pixi-workspace-member package (dist `pyforge-scribe`, module `pyforge.scribe`, CLI `scribe`) with `capture`/`graph compile`/`recall` as its three independently invocable top-level commands and sole public contract.
  - **success:** Each command is independently testable; other pyforge stations (Herald, Marshal, Doctor) integrate only via the CLI or a documented, versioned API, never by importing `pyforge.scribe` internals directly; the three-command CLI skeleton exists from Wave 1's start so the public contract's shape does not change between waves.

## Constraints

- **AD-1 (append-only is the single source of truth):** capture is the only mutation path for decisions/ADRs/runbooks — append-only, never edited in place, only superseded. `scribe graph compile` never accepts direct graph edits; the compiled graph is 100% derived and re-computable from source records at any time.
- **AD-2 (promotion write-boundary):** the only write Scribe performs outside `.claude/memory/**` and its own package/graph-store paths is the pointer-stub rewrite of a confirmed-promoted user-local entry, gated by explicit human confirmation and an idempotent `promoted: true` check. Scribe MUST NOT write to `.claude/skills/` (other than its own), `.claude/scripts/`, `.claude/agents/`, `.mcp.json`, `recipes/`, `_bmad/`, `_bmad-output/` outside its own project directory, or root `CLAUDE.md` (that wiring, and any BMAD↔CFE-section de-duplication, stays a human-driven edit, never automated).
- **AD-3 (schema parity):** `.claude/memory/<type>/*.md` frontmatter (`name`, `description`, `type`) is byte-identical in shape to Claude Code's user-local auto-memory schema; `type` is exactly one of `{feedback, project, reference}`, no additional required fields in Wave 1.
- **AD-4 (supersession, never deletion):** a capture naming a prior record as superseded marks that record's validity as ended in the compiled graph; it is never deleted or overwritten. Binds at the projection-builder level, independent of the concrete `GraphStore` adapter.
- **AD-5 (storage engine is a swappable adapter):** the graph store sits behind a `GraphStore` port (write: upsert-node/invalidate-edge-shaped operations; read: query-by-citation-path). No module outside the concrete adapter may import a specific storage engine's client library directly.
- **AD-6 (air-gap by construction):** the default configuration performs zero outbound network calls for `capture`, `graph compile`, or `recall`. Any optional network-touching capability (e.g. a future hosted-LLM backend) is opt-in, off by default, gated behind an explicit flag; `recall`'s v1 default path must not require network reachability.
- **AD-7 (CLI is the sole public contract):** `pyforge.scribe`'s public `__init__.py` exports only what the CLI needs; other components integrate via the CLI or a documented, versioned API, never via direct internal imports.
- **AD-8 (recall never fabricates a citation):** every `recall` response either includes a resolvable citation or returns an explicit "no grounded answer found" — no code path returns synthesized prose without one.
- **AD-9 (wave boundary):** `.claude/memory/` frontmatter (AD-3) is a stable input contract for Wave 2's compile step; Wave 2 reads that format as-is — any additional metadata it needs is additive, never a breaking rewrite of Wave 1's schema.
- **Manual-only invocation:** no `Stop`/`SessionEnd`/`PreCompact` hook triggers capture in either wave — every invocation is deliberate.
- **Versioning:** semver; CLI subcommand additions are MINOR, breaking flag/output-format changes are MAJOR.

## Non-goals

- No ambient/automatic capture — Scribe never passively mines chat logs, Slack, or session transcripts for decisions; capture is always a deliberate, authored action, permanently.
- No `Stop`/`SessionEnd`/`PreCompact` hook automation in Wave 1 or Wave 2.
- No cross-repo synchronization — each repo's Scribe instance is self-contained.
- No plugin/marketplace packaging until a second consumer repo exists.
- No claimed recall-accuracy benchmark parity (LoCoMo/LongMemEval-style) with Mem0/Zep/Graphiti — differentiation is git-native/air-gap/capture-as-you-decide, not retrieval performance.
- No general-purpose enterprise knowledge-search product — not Glean's cross-SaaS-connector breadth; repo-scoped by design.
- No TTL/decay/staleness auto-scoring on entries — humans prune; Scribe may surface a staleness signal at compile time but never auto-deletes.
- No premature commitment to a specific graph storage engine — the choice is deferred behind the `GraphStore` port (AD-5); this Spec fixes the port, not the engine.

## Success signal

`scribe capture` is used at a real decision point (not retrofitted demo data) within the first month after Wave 1 ships, and `scribe recall` returns a grounded, cited answer to a real "why did we..." question within the first month after Wave 2 ships. Supporting: every promoted entry carries the correct pointer-stub marker; nightly compile completes unattended across at least 4 consecutive scheduled runs; zero network calls occur during capture/compile/recall with network access blocked. Counter-signals that must NOT be optimized away: a high promoted-entry count with low recall usage (hoarding, not value), and compile speed traded against supersession correctness.

## Assumptions

- Wave 1 and Wave 2 are sequential, not parallel tracks — Wave 2's compile step depends on Wave 1's `.claude/memory/` layer existing as one of its inputs.
- `scribe recall`'s output format (plain text vs. structured JSON vs. both) is left unspecified at the product level — an architecture/API-contract decision, not a product one.
- The two existing BMAD↔CFE feedback rules are Wave 1's seed-promotion proof; no new seed content was invented.
- If Anthropic ships native team-shared memory (`anthropics/claude-code#38536`) during Scribe's build, `.claude/memory/`'s file layer may be absorbed into that native surface, leaving Scribe's differentiated value in graph-compile + recall — a watch-item, not currently a blocker or a scope change.

## Open Questions

- The architecture's own Deferred section calls for "a small spike comparing" a flat-file/index adapter against an embedded graph engine before choosing the v1 `GraphStore` adapter, but epics Story 2.1's acceptance criteria simply names the flat-file/index adapter as the v1 implementation without confirming the spike ran — is flat-file/index a provisional default still pending that comparison, or a settled v1 choice?
- The exact v1 input glob list for `scribe graph compile --nightly` — which specific `.memlog.md` paths across BMAD projects, which retro/CHANGELOG paths, and how much of `docs/dreams/` — is fixed in shape but not enumerated by architecture or epics.
- Naming/interop with the `docs/adr/`-style numbering/format the domain research found as dominant practice — should `scribe capture --type decision` formally adopt it, or keep its own vocabulary, and should Scribe read pre-existing `docs/adr/`-style files in a target repo?
