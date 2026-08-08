---
stepsCompleted: [1, 2, 3, 4, 5, 6]
inputDocuments:
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/research/market-agent-team-memory-research-2026-07-25.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/retros/retro-scribe-2026-08-08.md
  - .claude/memory/MEMORY.md
  - ~/.claude/projects/-home-rxm7706-UserLocal-Projects-Github-rxm7706-local-recipes/memory/MEMORY.md
workflowType: 'research'
lastStep: 6
research_type: 'market'
research_topic: 'Post-ship refresh of the agent/team knowledge-memory landscape: competitor movement since 2026-07-25 (Mem0/Zep, GitHub Copilot Memory, Claude Code native team memory), plus the internal integration landscape Scribe now actually occupies'
research_goals: 'Update the competitive threat model now Scribe is shipped, assess the two platform-native threats (Claude Code, Copilot) that moved materially, and map the cross-station integration surface inside the PyForge Guild'
user_name: 'Rxm7706'
date: '2026-08-08'
web_research_enabled: true
source_verification: true
mode: 'headless-express — a delta report against the 2026-07-25 market research (kept in place, unedited); external claims re-verified by targeted web search 2026-08-08, internal claims verified in-repo'
---

# Research Report: Market Refresh — Agent/Team Knowledge-Memory Systems (post-ship)

**Date:** 2026-08-08 · **Refreshes:** `market-agent-team-memory-research-2026-07-25.md` (kept; this is a delta, not a replacement)

---

## What changed in the competitive landscape since 2026-07-25

### 1. The platform-native threat moved from "watch" to "assume it ships" — Claude Code team memory

The original report's #2 threat ("Claude Code shipping first-class team-shared memory natively," tracked as `anthropics/claude-code#38536`) has materially advanced. The feature request remains open and native shared *auto* memory is still officially unshipped — CLAUDE.md in git remains the official team-sharing mechanism _(Source: https://github.com/anthropics/claude-code/issues/38536; https://code.claude.com/docs/en/memory)_. But an April 2026 analysis of Claude Code source (leaked via npm source maps 2026-03-31) describes a **complete, unreleased team memory sync engine** already in the codebase: a directory that syncs to Anthropic's servers, merges teammates' memories, injects into every conversation — with a pre-upload secret scanner and a last-write-wins-per-key conflict model _(Source: https://jakegoldsborough.com/blog/2026/inside-claude-codes-team-memory-sync/)_. Auto Memory itself (the `~/.claude/projects/<project>/memory/` layer Scribe promotes *from*) went on-by-default around March 2026, with a 200-line/25KB always-loaded index — the exact constraints Scribe's FR-1/FR-2 mirror _(Source: https://milvus.io/blog/claude-code-memory-memsearch.md; https://claudefa.st/blog/guide/mechanics/auto-memory)_.

**Implication for Scribe (sharper than 2026-07-25's):** the original report asked whether `.claude/memory/` would "fold into the native surface." The leaked design answers what the native surface will look like: **server-synced, Anthropic-hosted, last-write-wins**. That is the *opposite* of Scribe's differentiation on every axis that matters here — git-reviewed (promotion is a reviewed diff, not an upsert), air-gapped (zero server), and provenance-preserving (supersede-don't-overwrite vs. last-write-wins). If/when it ships, Scribe's capture layer should coexist rather than fold: native sync for low-stakes preference osmosis, Scribe's promotion gate for anything that becomes trusted instruction context. The RISK-3 trust-boundary finding (technical report, 2026-08-08) is the argument: a last-write-wins server sync into every teammate's context has *no* review gate at all.

### 2. A fifth analogue entered the map: GitHub Copilot's repo-scoped memory

Not in the original four. Copilot Memory is in public preview, **on by default** for Pro/Pro+ since 2026-03-04, and — the structurally interesting part — GitHub ties memory **to repositories, not individuals**, shared across the coding agent, Copilot CLI, and code review; coding-agent knowledge bases were enabled by default 2026-03-11, which one analyst read as GitHub treating project memory as "required infrastructure," not an enhancement _(Source: https://github.blog/changelog/2026-03-04-copilot-memory-now-on-by-default-for-pro-and-pro-users-in-public-preview/; https://redreamality.com/blog/github-copilot-memory-agentic-coding-stack/; https://docs.github.com/en/copilot/get-started/features)_. Copilot Spaces (GA since Sept 2025) covers the cross-project knowledge tier _(Source: https://docs.github.com/en/copilot/get-started/features)_.

**Positioning-map update:** Copilot Memory is the first mover into the "repo-native, team-visible" cell the 2026-07-25 map showed as unoccupied-except-Scribe. The remaining moat is unchanged in kind but narrower: Copilot's memory is **cloud-derived and cloud-held** (deduced by the model, stored on GitHub's side, counts against token budget), not git-diffable, not air-gapped, not authored-at-decision-time, and with no supersession/provenance model. Scribe's three-gap framing survives, but gap #2's phrasing should tighten from "repo-native" to "**repo-resident and review-gated**" — mere repo-*scoping* is now table stakes across both major platforms.

### 3. Mem0/Zep: consolidation, benchmark war, and a self-hosting retreat

Mem0 consolidated adoption leadership (~14M downloads, 186M API calls/quarter, exclusive memory provider in AWS's Agent SDK); Zep doubled down on temporal depth, with Graphiti (~28.2K stars, Apache-2.0) now self-hostable on Neo4j, FalkorDB, **Kuzu**, or Neptune, while **Zep the platform stepped back from full open self-hosting** to SaaS tiers — an explicit narrowing of the open deployment story the original report already flagged as weak _(Source: https://vectorize.io/articles/mem0-vs-zep; https://rohitraj.tech/en/notes/open-source-ai-agent-memory-mem0-vs-zep-letta-2026)_. The two are in an open benchmark dispute (Zep claiming 75.14% on LOCOMO after rebutting Mem0's configuration of it; a ~15-point LongMemEval gap in Zep's favor on temporal facts), with every vendor benchmarking on different datasets _(Source: https://vectorize.io/articles/mem0-vs-zep; https://blog.devgenius.io/ai-agent-memory-systems-in-2026-mem0-zep-hindsight-memvid-and-everything-in-between-compared-96e35b818da8)_. The original report's Recommendation #3 (make **no** recall-benchmark claims; differentiate on groundedness + citation) shipped verbatim as a PRD NFR and looks even better now — the benchmark theater is a war Scribe deliberately isn't in. Neither vendor shipped a "repo mode"; that half of threat #1 did not materialize this cycle. (No August-2026-dated developments found; most recent coverage is June–July 2026.)

---

## The internal landscape: what Scribe actually integrates with now (new section)

Scribe shipped into a live memory ecosystem, and the integration is no longer hypothetical:

- **Upstream (proven):** the user-local auto-memory store for this repo currently holds **112 files** (~60 indexed entries); Scribe's promotion classifier ran against real entries and the first pointer stub is live (`feedback_bmad_runs_cfe_retro.md`, `promoted: true`, `promoted_date: 2026-08-07`). Auto-memory is Scribe's raw-material mine, and at ~60 candidate entries the mine is deep — a systematic promotion sweep is an obvious, cheap, high-value next action.
- **Downstream (proven):** `.claude/memory/MEMORY.md` is `@import`ed by root `CLAUDE.md`, so every station's every session — Doctor, Warden, Marshal, Herald, all of them — already *reads* Scribe's output. This is the one live cross-station integration point today, and it is broadcast-shaped: one shared index, no per-station scoping.
- **Passive cross-station ingestion (already shipped, easy to miss):** the compile's retro surface (`**/*retro*.md`) and CHANGELOG surface mean *other stations' retros and changelogs are already graph nodes*. Scribe already listens to the whole guild; nothing yet queries it back.

**Should Scribe also surface findings TO other stations?** The asymmetry above says yes, and the cheapest integrations don't require new Scribe features — they require other stations calling the existing CLI:

1. **Doctor** (fleet health): a health check that shells `scribe recall` (or reads `graph.json` via the `GraphStore` port) could answer "is there a recorded decision about this failing surface?" — turning red checks into cited history instead of archaeology. Zero new Scribe code.
2. **Warden** (compliance/currency): Warden's currency findings are exactly `scribe capture --type project` material ("package X grandfathered, decided <date>"), making waivers/grandfathering decisions recallable with citations instead of living only in baseline files.
3. **Marshal/bmad-loop**: the dangling-commit incident is the cautionary tie — the retro's `git fsck` action item is a *Marshal-side* fix motivated by Scribe-side evidence; conversely, a loop dev session could `scribe recall` before re-deciding something a prior story already settled (the `d43899c1cb` duplication incident, generalized).

The strategic point: Scribe's moat versus every external player above is that it is *inside the trust boundary and inside the workflow* of eight sibling stations. None of Mem0/Zep/Copilot/native-Claude can be invoked by Doctor's health check against the guild's own decision graph. Deepening station-to-Scribe query integration widens the one moat no platform vendor can replicate.

## Updated recommendations

1. Re-rank threats: **Claude Code native team memory is now #1** and should be treated as "ships within 12 months, server-synced, last-write-wins" — position Scribe's promotion gate explicitly as the *reviewed* tier above it, not a substitute for it.
2. Add **GitHub Copilot Memory** to the positioning map as the fifth analogue; tighten gap #2's language to "repo-resident, git-reviewed, air-gapped."
3. Before any new capability work, close the two internal gaps that undercut the market story: the unscheduled nightly (a "nightly-compiled graph" pitch with no scheduler) and the unreviewed `promote.py` (a "review-gated promotion" pitch whose gate code nobody has reviewed) — both documented in the 2026-08-08 technical report.
4. Run the 112-entry auto-memory promotion sweep — it is simultaneously dogfooding, the fastest way to grow `.claude/memory/` past one entry, and a live stress test of the classifier heuristics RISK-1 wants reviewed.
5. Pilot one station-to-Scribe query integration (Doctor is the natural first) to convert the cross-station moat from latent to demonstrated.

## Sources

- [Feature Request: Shared Team Memory for Claude Code — anthropics/claude-code#38536](https://github.com/anthropics/claude-code/issues/38536)
- [Inside Claude Code's Team Memory Sync Engine — Jake Goldsborough](https://jakegoldsborough.com/blog/2026/inside-claude-codes-team-memory-sync/)
- [How Claude remembers your project — Claude Code Docs](https://code.claude.com/docs/en/memory)
- [Claude Code Memory System Explained — Milvus](https://milvus.io/blog/claude-code-memory-memsearch.md)
- [Claude Code Auto Memory — claudefa.st](https://claudefa.st/blog/guide/mechanics/auto-memory)
- [Copilot Memory now on by default (public preview) — GitHub Changelog](https://github.blog/changelog/2026-03-04-copilot-memory-now-on-by-default-for-pro-and-pro-users-in-public-preview/)
- [GitHub Copilot Is Becoming a Memory-Bearing Agentic Coding Stack — redreamality](https://redreamality.com/blog/github-copilot-memory-agentic-coding-stack/)
- [GitHub Copilot features — GitHub Docs](https://docs.github.com/en/copilot/get-started/features)
- [Mem0 vs Zep (Graphiti): AI Agent Memory Compared (2026) — Vectorize](https://vectorize.io/articles/mem0-vs-zep)
- [Open-Source AI Agent Memory: Mem0 vs Zep vs Letta (2026) — Rohit Raj](https://rohitraj.tech/en/notes/open-source-ai-agent-memory-mem0-vs-zep-letta-2026)
- [AI Agent Memory Systems in 2026 — Dev Genius](https://blog.devgenius.io/ai-agent-memory-systems-in-2026-mem0-zep-hindsight-memvid-and-everything-in-between-compared-96e35b818da8)
- Internal: `market-agent-team-memory-research-2026-07-25.md` (baseline), `retro-scribe-2026-08-08.md`, `.claude/memory/MEMORY.md` + user-local auto-memory index (112 files), commits `ccecbf5f1c` / `d68187f4b3` / `a53b5c581e`, PRs #168/#296/#301
