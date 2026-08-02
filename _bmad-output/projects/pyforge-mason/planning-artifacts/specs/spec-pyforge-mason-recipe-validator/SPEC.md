---
id: SPEC-pyforge-mason-recipe-validator
spec: pyforge-mason-recipe-validator
status: archived
archived-reason: conflicts-with-decided-architecture
owner-dream: docs/dreams/pyforge-mason-recipe-validator.md
surface: []          # archived — no live surface; see § What carries forward
sources:
  - ../../../../../../docs/dreams/pyforge-mason-recipe-validator.md
open_questions: []
---

> **Retirement record.** This Dream is `status: archived` (`conflicts-with-decided-architecture`).
> Charter §5 requires every Dream to carry a Spec, archived included: a retirement record is
> how the next reader learns from the decision instead of rediscovering the idea. It states
> what was contracted, why it ended, and what survives — not a plan for work that will not
> happen.

# pyforge-mason-recipe-validator — retirement record

## Why it was contracted

A native recipe validator for Mason: ~50 linting rules covering naming, versioning, pinning
policy, selectors, noarch, dependencies, licensing, and build scripts; schema validation
against recipe.yaml v1/meta.yaml v0; pinning-policy enforcement; cross-platform selector
coverage checks; upstream conformance checks; actionable findings with remediation guidance.
Success criteria named 0 false positives across 1000+ canonical recipes and a 5-minute
re-validation sweep across all 769 feedstocks.

## Why it ended

**Retired 2026-08-02, same day it was created.** The dream was generated in a bulk commit
(`dad47c408a`) later found to contain fabricated content elsewhere in the same commit (a
migration note with false claims about the dashboard generator, boilerplate
test-architecture.md files duplicated across stations). This dream's proposal does not survive
scrutiny against Mason's own constitutive Dream and its already-decided architecture:

- [[pyforge-mason]]'s decision D-1 ("Option C") already settled this exact question: `mason
  recipe` **wraps** the conda-forge-expert skill by subprocess for all recipe-semantics work —
  linting, validation, optimization, vulnerability scanning — because "the skill stays
  canonical for recipe semantics and keeps improving through the Rule-2 retro loop." Building
  a second, native ~50-rule engine inside Mason is the option D-1 explicitly did not choose.
- Mason's epics.md already carries the wrapper stories this dream would duplicate wholesale:
  **Story 2.5** (`mason recipe validate`) states "CFE's identifiers are preserved verbatim —
  never renumbered, reworded, or re-severitied"; **Story 2.8** (`mason recipe
  optimize`/`scan`) states "CFE's check codes are preserved verbatim in the output... Mason
  applies no severity policy, threshold, or filtering of its own." Both are already-specified,
  already-storied, ready-for-implementation work — this dream re-proposes the same surface
  under a different architecture.
- Implementing this dream as written would not merely duplicate that scope — it would violate
  [[pyforge-mason]]'s own explicit non-goal: *"Never fork the craft. A fork is structurally
  adversarial: Rule 2 mandates that every conda-forge effort edits the skill, so a fork is
  invalidated by the loop that governs its own domain. The in-repo cautionary precedent is
  [[pyforge-atlas]], which chose full rebuild and whose legacy orchestrator is still the live
  runtime."* A native Mason lint engine is precisely that fork.

## What carries forward

Nothing new — the intent this dream describes is already served by Mason's wrapper stories
(2.4–2.9 in epics.md) over the conda-forge-expert skill, which is where recipe-linting
improvements belong per Rule 2 (every conda-forge effort edits the skill, not a fork of it).
A genuine gap in conda-forge-expert's own lint coverage is a `conda-forge-expert` skill
enhancement, tracked via its own retro/CHANGELOG process — not a second engine in Mason.

## Non-goals

- **Reviving this Dream as written.** Its intent was never separate from
  `pyforge-mason`'s D-1 seam decision; there is nothing here to revive.
- **Treating this record as a backlog item.** Archived Dreams are excluded from the
  Backlog board by design.
- **Building a native Mason lint/validation engine under any name.** D-1 is a standing
  architectural decision, not a preference — reopening it requires a new operator ruling
  against pyforge-mason's own Dream, not a second Dream that ignores the first.

## Success signal

A reader arriving at this Dream learns in one page why it stopped and where its intent
went, without re-deriving the conflict or mistaking it for a second contract — and without
starting a Mason lint engine that Story 2.5/2.8 and D-1 already forbid.
