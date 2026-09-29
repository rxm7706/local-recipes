---
title: '24.3: Every harness is pointed at the catalog once'
type: 'config'
created: '2026-09-29'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - docs/dreams/pyforge-scribe.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-pyforge-scribe/SPEC.md
  - _bmad-output/projects/pyforge-scribe/planning-artifacts/specs/spec-24-2-the-catalog-cannot-drift-silently.md
  - AGENTS.md
  - .claude/skills/bmad-project-context/SKILL.md
  - docs/reference/README.md
  - docs/MAP.md
deferred: []
declared_low_risk: false
---

<intent-contract>

## Intent

**Problem:** `AGENTS.md` carries one pointer line to the adoption register, no line naming the installed core version, the suite verbs, the cadence, `bmad-method-version-drift-check` or `tea-test-review`, and nothing that names the estate catalog Stories 24.1–24.2 produce. `CLAUDE.md` already imports `AGENTS.md` (CAP-27), so `AGENTS.md` is the one place to point from.

**Approach:** One Read-on-trigger row outside the markers ("Before invoking a BMAD skill, provisioning or upgrading a suite member, or driving bmad-loop → `docs/reference/bmad-estate-llms-full.md`"); inside the `bmad:context` block, via `bmad-project-context record`/`refresh` only: one Where-things-are line naming the catalog as the derived estate picture and the three detector names under Running and verifying. `docs/reference/README.md` and `docs/MAP.md` classify the file. The 2026-09-12 research record gains a dated addendum saying what landed.

## Boundaries & Constraints

**Always:**
- Point, don't copy (CAP-27): no version, count or verdict is typed into `AGENTS.md`.
- The `bmad:context` block changes only through `bmad-project-context`; its provenance line is re-stamped by the skill.
- Co-governor reconcile before landing (this Spec's surface lists `AGENTS.md`), as in Story 24.1.

**Never:**
- Do not add a line to `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` or `.cursor/rules/*.mdc` — they point at `AGENTS.md`.
- Do not hand-edit inside the `bmad:context` markers.
- Do not restate routing detail (which station wields which skill) — that stays in the register and the persona skills (AD-2).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| parity meta-test | `AGENTS.md` edited outside the markers | `test_instruction_surface_parity.py` green | fail loud |
| governance-currency | new paths named | every path resolves | fail loud |
| block refresh | skill run | provenance line carries today's date and the verified SHA | n/a |

</intent-contract>

## Binding

Parent Spec capability: `spec-pyforge-scribe CAP-32` (with CAP-27's rules).
Dream: `docs/dreams/pyforge-scribe.md` § *2026-09-29 — Every session knows the BMAD estate it stands on*.
Ledger key: `24-3-every-harness-is-pointed-at-the-catalog-once`.
Ledger status at mint: `backlog`; `done` 2026-09-29 after the review below.

## Epic excerpt

**Type:** config • **Effort:** S • **Deps:** S-24.2 • **FR/AD:** spec-pyforge-scribe CAP-32, CAP-27
**Surface:** `AGENTS.md`, `docs/reference/README.md`, `docs/MAP.md`, the 2026-09-12 research record (addendum).
See `epics.md` § Story 24.3 for the full Given / When / Then / And.

## Review 2026-09-29 (adversarial, independent session) — passed after fixes

Findings addressed: the in-block Where-things-are line typed a count ("13-member"), against this story's Always; it now says "the suite roster" and the catalog states the count. The Running-and-verifying line implied `tea-test-review` runs from the Guild env; it is a `local-recipes` task and the line now says so. The block lines were shown to the operator and approved before the splice (bmad-project-context step 5); provenance re-stamped.
