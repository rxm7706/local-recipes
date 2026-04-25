---
name: spec-driven-development
description: Create detailed specifications before implementing. Four gated phases: Specify → Plan → Tasks → Implement. Human review between phases.
source: https://github.com/addyosmani/agent-skills
---

# Spec-Driven Development

## Core Principle

> "Code without a spec is guessing."

The specification is the shared source of truth between developer and AI, defining what's being built, why, and what success looks like.

## When to Apply

Use for:
- New projects or features
- Ambiguous requirements
- Multi-file changes
- Architectural decisions
- Work exceeding ~30 minutes

Skip for:
- Single-line fixes
- Unambiguous, self-contained changes

## Four Gated Phases

Each phase requires human review before advancing:

1. **Specify** — Define what's being built and why
2. **Plan** — Determine how to build it
3. **Tasks** — Break into verifiable increments
4. **Implement** — Execute against the spec

## The Specification Foundation (Six Areas)

1. **Objective** — Purpose and success definition
2. **Commands** — Full executable commands with flags
3. **Project Structure** — Code organization and file locations
4. **Code Style** — Real examples demonstrating conventions
5. **Testing Strategy** — Framework, coverage, test levels
6. **Boundaries** — Three-tier decision framework (Always / Ask First / Never)

## Critical Practice: Surface Assumptions First

Before writing spec content, explicitly list assumptions:
> "This is a web application (not native mobile). Correct me now or I'll proceed with these."

This prevents silent misunderstandings from derailing development.

## Living Documentation

The spec evolves with the project — update when decisions, scope, or discoveries change. Commit it to version control and reference it in pull requests.

## Conda-Forge Application

Apply when starting a complex packaging task:

**Example spec for packaging a new library:**
```
Objective: Package `mylib` for conda-forge so Python 3.10–3.14 users can install it
Commands: generate_recipe_from_pypi, validate_recipe, trigger_build, submit_pr
Structure: recipes/mylib/recipe.yaml
Conventions: recipe.yaml v1 format, noarch: python, CFEP-25 python_min triad
Testing: pip_check: true, import test in tests section
Boundaries:
  - Always: include sha256, license_file, maintainer
  - Ask First: loosen pins for unavailable deps
  - Never: include dev dependencies in run, skip stdlib for compiled recipes
Assumptions: Package is pure Python (noarch). Correct me if it has C extensions.
```
