---
doc_type: retrospective
project: pyforge-atlas
epic: 1
wave: "0"
title: Wave 0 — Legacy Translation via Skill Forge
stories: 1
date: 2026-07-25
basis: reconstructed from tracked evidence (run log, epics.md, main commits)
---

# Epic 1 · Wave 0 — Legacy Translation via Skill Forge

**Scope:** one story (0.1). Provision `bmad-module-skill-forge@2.0.1`; forge the
`cf-atlas-legacy` contextual skill. Commits `b18cbb5`, `6658049`.

## What worked

- **Forging a contextual skill before porting anything was the highest-leverage
  decision in the effort.** The legacy orchestrator was a ~8,200-line procedural
  monolith. Rather than have every downstream story re-read it, one pass distilled
  it into a skill that later waves consulted. SKF gates scored **100/100** and the
  staging skill was promoted — a clean, measurable gate on a task that is usually
  judged by vibes.
- **A precondition wave is cheap insurance.** One story, no product surface, and
  it de-risked all 31 that followed.

## What did not

- **The skill's value is asserted, not measured.** Nothing recorded how often
  later waves actually consulted `cf-atlas-legacy`, or what a B-wave story would
  have cost without it. The 100/100 gate scores the skill's *form*, not its
  *usefulness*. A single "sources consulted" line in each B-story's Dev Notes
  would have closed this for near-zero cost.
- **Single-story epics distort the wave summary.** Epic 1 counts equally with
  Epic 3 (ten stories, the keystone wave) in any per-epic view.

## Carry-forward

1. When a precondition artifact is built to serve later work, **instrument the
   consumption**, not just the artifact's own quality gate.
2. Skill Forge earned its place — reach for it again on the next legacy-monolith
   translation rather than re-reading the source per story.
