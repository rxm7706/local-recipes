---
title: "Dream — PyForge Scribe: Team Memory Management"
date: 2026-08-02
status: dreamt
owner: scribe
scope: "Memory capture, team context, decision documentation, shared knowledge"
---

# PyForge Scribe — Team Memory Management

## Vision

**Scribe** manages team memory and shared knowledge — capturing decisions, project context, team feedback, and reference material in structured, reviewable prose that every contributor (human or agent) can learn from.

**The ask**: Build a memory system that makes every decision auditable, every lesson carried forward, and every contributor's context shareable without losing nuance to automation.

## Problem

- **Knowledge evaporates.** A contributor solves a hard problem; the solution lives in a closed Slack thread. Next contributor reinvents the wheel.
- **Context is scattered.** Project state in PRs, decisions in issues, feedback in code reviews, lessons in wikis. No single source of truth.
- **AI agents have amnesia.** Claude Code can solve a problem brilliantly today; tomorrow a new session starts with no context. Valuable patterns are lost.
- **Onboarding is slow.** New team members drown in Slack history. No structured narrative of "here's what we've learned."
- **Feedback is reactive.** Issues are caught in code review repeatedly. The feedback is written three times; the pattern is never named or systematized.

## Realization

**Scribe** delivers:

1. **Structured Memory** — YAML frontmatter + prose body. Type (user/project/feedback/reference), tags, related memories, and dates. Queryable, versionable, git-tracked.

2. **Automatic Capture** — When a contributor finds a gotcha or a solution, they use `/remember [type]` inline. Scribe scaffolds the entry; they fill in the reasoning.

3. **Team Layers** — User memory (auto-memory per Claude Code session) → team memory (promoted after review). Only team-relevant entries live in the tracked tier.

4. **Memory Promotion** — Stories with team relevance go through editorial review. "Is this a pattern, or just today's frustration?" Team review decides.

5. **Context Loading** — Agents load all team memory automatically. Claude Code starts a session already knowing the team's feedback, the project's patterns, the shared gotchas.

6. **Memory Index** — Concise index (MEMORY.md) with links to full entries. 200-line compact view; detail lives in linked files.

## Success Criteria

- ✅ **Capture**: Every session surfaces 3+ memory candidates automatically
- ✅ **Promotion**: Team feedback loop works; entries get promoted after review
- ✅ **Context**: Agents load team memory on startup; context shapes their behavior
- ✅ **Searchability**: Memories indexed and queryable; pattern discovery takes <1 min
- ✅ **Governance**: Memory is git-tracked, auditable, and reviewed like code
- ✅ **Narrative**: New contributor reads MEMORY.md and can orient themselves in 10 min

## Acceptance

Scribe is done when:
1. All 8 PyForge stations have team memory directories with 20+ entries each
2. Memory promotion workflow proven: 10+ entries promoted through review
3. Agents load memory on startup and reference it in decisions
4. Pattern detection working: queries surface related memories for similar problems
5. Onboarding time cut by 50%: new contributor oriented in 10 min via MEMORY.md
6. Retention proven: memories prevent 80%+ of repeated gotchas in future sessions
