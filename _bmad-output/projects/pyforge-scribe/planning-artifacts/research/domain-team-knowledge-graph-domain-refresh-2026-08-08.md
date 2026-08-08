---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/research/domain-team-knowledge-graph-domain-research-2026-07-25.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/retros/retro-scribe-2026-08-08.md
  - docs/dreams/pyforge-scribe.md
  - docs/dreams/sentinel.md
  - src/shared/packages/pyforge-scribe/src/pyforge/scribe/graph_store.py
  - .claude/memory/README.md
workflowType: 'research'
lastStep: 6
research_type: 'domain'
research_topic: 'Post-ship refresh of the team-knowledge-capture domain report: which 2026-07-25 domain findings held, which the build refuted, and what the shipped system reveals about the domain problem itself'
research_goals: 'Re-validate "the inward voice" against what actually shipped (capture + promotion + nightly-compiled graph), and close or carry each of the original report''s open questions'
user_name: 'Rxm7706'
date: '2026-08-08'
web_research_enabled: false
source_verification: true
mode: 'headless-express — a delta report against the 2026-07-25 domain research (which remains in place, unedited); grounded in the shipped code and the 2026-08-08 retro, no new external claims'
---

# Research Report: Domain Refresh — Team Knowledge Capture & Graph Compilation (post-ship)

**Date:** 2026-08-08 · **Refreshes:** `domain-team-knowledge-graph-domain-research-2026-07-25.md` (kept; this is a delta, not a replacement)

---

## Status of the original report's findings

The 2026-07-25 domain report fed the architecture phase directly, and the build closed every open question it carried forward:

| 2026-07-25 finding / open question | Outcome in the shipped system |
|---|---|
| ADR-shaped capture: one record per decision, supersede-and-link, never edit in place | **Adopted and shipped** — `supersedes: "<type>/<slug>"` frontmatter → `invalidate_edge()` marks ended validity, never deletes (Story 2.3, FR-10, AD-4) |
| Embedded graph engine (LadybugDB etc.) vs. flat-file — "genuinely open" | **Resolved: flat-file won v1.** `FlatFileGraphStore` (one deterministic JSON file) behind the `GraphStore` protocol. Notably, the KuzuDB-archival warning is cited *in the shipped docstring itself* (`graph_store.py:6-8`: "the KuzuDB-archival lesson the domain research flagged") — a rare case of research being literally load-bearing in production code. The engine question stays open behind AD-5's seam, now with a defined swap cost of one adapter class. |
| Air-gap must be a testable constraint, not a marketing line | **Shipped as tests** — dedicated offline-conformance tests per Epic 2 story; zero-network is asserted, not claimed. Capture/compile/recall are stdlib+regex+`git log`(local) only; no LLM anywhere in v1 (`recall` is deterministic lexical matching, resolving PRD Open Question 3 to "no LLM required"). |
| Local-first = "git as source of truth," not CRDT sync | **Held exactly as scoped** — concurrency was handled with advisory file locks + atomic `os.replace()` (both `capture.py` and `graph_store.py`), and the one real concurrency bug found (Story 1.1's index race, 13/20 entries lost under a 20-thread test) was a *locking* bug, not a convergence bug. No CRDT machinery was ever needed. The scope-inflation warning paid off. |
| "What does 'compiled nightly from the tools the team already uses' concretely mean?" | **Resolved: five named surfaces** — `.claude/memory/`, `**/.memlog.md`, git history (100 commits), `**/*retro*.md`, `**/CHANGELOG.md` (`compile.py`, FR-9). `docs/dreams/` did *not* make the v1 surface list despite the Dream naming it — a scope cut worth making explicit if a Wave 3 ever revisits the input surface. |
| Formal ADR vocabulary vs. Scribe's own `--type` taxonomy | **Resolved: Scribe kept its own 3-type taxonomy** (`feedback`/`project`/`reference`, FR-8), byte-compatible with Claude Code auto-memory rather than `docs/adr/` convention — interop with the agent-memory layer beat interop with the ADR ecosystem. Defensible; unexamined since. |

## Domain re-validation: "the inward voice" vs. what shipped

The Dream's claim — *what the team knows, every agent and every session knows* — is now partially real and measurably so: `.claude/memory/MEMORY.md` is a live `@import` in root `CLAUDE.md`, so a promoted entry genuinely reaches every session of every agent, and the first real entry (`feedback/bmad-runs-cfe-retro.md`) got there via the tool itself. Three qualifications matter for anyone re-planning this domain:

1. **The shipped scope is the Dream's first two bullets only.** Capture + promotion + compile + recall shipped. The Dream's third ownership bullet — the curation surfaces (Dreams index hygiene, doc/ADR hygiene, wikis, library-catalog freshness) — has zero implementation and no epic. "The inward voice" currently speaks; it does not yet *curate*.
2. **The domain's core failure mode occurred inside Scribe's own build.** The 2026-07-25 report's central diagnosis was "records go stale because reality changes elsewhere and nobody updates the file." During the build: the Dream doc's "What is real" section sat at 3-of-9-stories for days after 9/9 shipped (fixed only by the 2026-08-08 hygiene sweep, commit `bfa9fd688d`); the retro's own delivery snapshot says both seed entries were promoted when the commit record (`ccecbf5f1c`) shows 1 of 2. Scribe is the *cure* for exactly this class of drift, and its own artifacts exhibited it — the strongest possible internal validation that the problem is real, and a pointed argument for pointing `scribe graph compile` at `docs/dreams/` (the cut surface) so drift like this becomes recallable.
3. **"Nightly" is still aspirational.** The compile is unattended-by-construction but unscheduled — no cron, CI, or pixi task invokes it (verified 2026-08-08). In domain terms, Scribe has shipped the *compiler* for the Karpathy-style knowledge loop, not yet the *loop*. Until scheduled, the graph is only as fresh as the last manual invocation, which quietly reintroduces the "somebody has to remember to run it" failure mode the nightly design existed to kill.

## New domain finding (not in the 2026-07-25 report): shared agent memory is a trust boundary

The original report treated capture/compile as a data-freshness problem. The build surfaced a second axis: **provenance-as-security**. Since 2026-07-31, the CLAUDE.md external-import startup dialog is pre-approved for unattended loop homes (operator decision recorded in `pixi.toml`), so agent-written team memory is injected into every session's system context with no human preview moment; the compensating control is git review of `.claude/memory/**` diffs "as instructions, not notes." Domain implication: any team-memory system whose store feeds an agent's trusted context inherits a prompt-injection surface, and the promotion gate (proposal-then-confirm, FR-3) is doing double duty as the security review. This deserves first-class treatment in any future architecture pass — see the 2026-08-08 technical report, RISK-3.

## Carried forward

- The embedded-engine trigger is undefined: AD-5 makes swapping cheap, but no measurement defines when the flat file has "run out of headroom" (technical report RISK-4 proposes the benchmark).
- Whether `docs/dreams/` (and the sprint-status ledgers) join the compile surface — the two drift incidents above are the evidence for yes.
- The curation-surfaces scope (Dream bullet 3) has no research, no PRD, no epic — genuinely unowned within Scribe's own charter.

## Sources

All internal, verifiable in-repo: the 2026-07-25 domain report (baseline), `retro-scribe-2026-08-08.md`, `docs/dreams/pyforge-scribe.md` + `docs/dreams/sentinel.md`, shipped source (`graph_store.py`, `compile.py`, `recall.py`, `capture.py`), `.claude/memory/README.md`, commits `bfa9fd688d`, `ccecbf5f1c`, `a53b5c581e`, PRs #296/#301/#168.
