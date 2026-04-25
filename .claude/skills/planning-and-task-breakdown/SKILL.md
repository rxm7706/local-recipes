---
name: planning-and-task-breakdown
description: Decompose work into manageable, verifiable tasks. Read-only mode first. Vertical slicing, not horizontal. Checkpoints every 2–3 tasks.
source: https://github.com/addyosmani/agent-skills
---

# Planning and Task Breakdown

## Key Principles

1. **Read-only first**: Understand specs, existing patterns, and dependencies before writing any code
2. **Vertical slicing**: Build complete feature paths end-to-end (not all DB work, then all API work)
3. **Testable acceptance criteria**: 2–3 bullet points per task, specific and verifiable
4. **Dependency ordering**: Satisfy dependencies before dependent tasks begin

## Task Structure

Each task should include:
- Clear, single-purpose description
- Testable acceptance criteria (2–3 bullet points)
- Verification steps with specific commands
- Identified dependencies
- Files likely to be modified
- Scope estimate (XS / S / M / L / XL)

## Sizing Standards

| Size | Files | Notes |
|---|---|---|
| XS | 1 | Trivial change |
| S | 1–2 | Optimal |
| M | 3–5 | Optimal |
| L | 5–8 | Approaching upper limit |
| XL | 8+ | **Decompose further** |

**Red flags for oversized tasks:**
- Title contains "and"
- Can't list acceptance criteria concisely
- Spans independent subsystems

## Checkpoints

Place verification checkpoints after every 2–3 tasks to ensure system stability.

## Conda-Forge Application

Apply before a multi-recipe packaging sprint or complex build debug session:

**Example task breakdown for packaging a new library:**
1. Check if package exists on conda-forge (`check_dependencies`) → verify: no existing feedstock
2. Generate recipe (`generate_recipe_from_pypi`) → verify: `recipe.yaml` created
3. Add maintainer + verify sha256 (`edit_recipe`) → verify: sha256 matches PyPI
4. Security scan (`scan_for_vulnerabilities`) → verify: no critical CVEs
5. Optimize (`optimize_recipe`) → verify: no check-code warnings
6. Build (`trigger_build`) → verify: `get_build_summary` shows success
7. Submit PR (`submit_pr dry_run=True`, then real) → verify: PR URL returned

Each step has a single clear success criterion.
