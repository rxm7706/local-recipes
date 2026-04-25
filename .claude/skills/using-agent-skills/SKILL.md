---
name: using-agent-skills
description: Meta-skill for discovering and applying the right engineering skill for any task. Decision tree by development phase.
source: https://github.com/addyosmani/agent-skills
---

# Using Agent Skills

## Purpose

Select and apply the right skill for any development task based on the current phase.

## Skill Selection by Phase

| Phase | Task | Skill |
|---|---|---|
| **Define** | Refining a vague idea | `idea-refine` |
| **Define** | Formalizing requirements | `spec-driven-development` |
| **Plan** | Breaking into tasks | `planning-and-task-breakdown` |
| **Build** | New feature/recipe | `incremental-implementation` |
| **Build** | Context drifting or confusing | `context-engineering` |
| **Build** | Grounding in official docs | `source-driven-development` |
| **Build** | API/interface design | `api-and-interface-design` |
| **Build** | UI work | `frontend-ui-engineering` |
| **Verify** | Test-first bug fix | `test-driven-development` |
| **Verify** | Systematic debugging | `debugging-and-error-recovery` |
| **Verify** | Browser/DOM inspection | `browser-testing-with-devtools` |
| **Review** | Pre-merge review | `code-review-and-quality` |
| **Review** | Simplify complex code | `code-simplification` |
| **Review** | Security audit | `security-and-hardening` |
| **Review** | Performance issues | `performance-optimization` |
| **Ship** | Version control discipline | `git-workflow-and-versioning` |
| **Ship** | CI/CD pipeline | `ci-cd-and-automation` |
| **Ship** | Pre-launch checklist | `shipping-and-launch` |
| **Ship** | Removing old patterns | `deprecation-and-migration` |
| **Ship** | Writing PR/ADR | `documentation-and-adrs` |

## Six Non-Negotiable Operating Principles

1. **Surface Assumptions** — State assumptions explicitly before proceeding with non-trivial work
2. **Manage Confusion** — Stop and clarify inconsistencies; don't guess
3. **Push Back When Warranted** — Flag technical problems with concrete downsides
4. **Enforce Simplicity** — Resist overcomplication; prefer obvious solutions
5. **Maintain Scope Discipline** — Only touch what you're asked to touch
6. **Verify, Don't Assume** — Require evidence that work is complete; "seems right" is insufficient

## Ten Critical Failure Modes

1. Making unchecked assumptions
2. Plowing ahead while confused
3. Overcomplicating solutions
4. Modifying code outside scope
5. Skipping verification steps
6. Treating summaries as verification
7. Ignoring existing patterns in favor of invented ones
8. Conflating correlation with causation in debugging
9. Deferring cleanup ("I'll fix it in a follow-up")
10. Missing the forest for the trees (fixing symptoms, not root causes)

## Skills Often Applied Together

- New feature: `spec-driven-development` → `planning-and-task-breakdown` → `incremental-implementation` → `test-driven-development` → `code-review-and-quality` → `git-workflow-and-versioning` → `shipping-and-launch`
- Bug fix: `debugging-and-error-recovery` → `test-driven-development` → `code-review-and-quality`
- Security issue: `security-and-hardening` → `test-driven-development` → `documentation-and-adrs`
- Migration: `deprecation-and-migration` → `incremental-implementation` → `test-driven-development`

## Conda-Forge Skill Stack

For a new recipe:
```
idea-refine → spec-driven-development → planning-and-task-breakdown
→ source-driven-development → incremental-implementation
→ test-driven-development → security-and-hardening
→ code-review-and-quality → git-workflow-and-versioning → shipping-and-launch
```
