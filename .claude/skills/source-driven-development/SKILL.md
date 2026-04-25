---
name: source-driven-development
description: Ground code decisions in official documentation, not memory or training data. Detect → Fetch → Implement → Cite.
source: https://github.com/addyosmani/agent-skills
---

# Source-Driven Development

## Core Principle

Every framework-specific implementation decision must be verifiable through authoritative sources.

> "Confidence about an API isn't evidence — verification is required. Fetching documentation costs fewer tokens than debugging hallucinated function signatures."

## Four-Step Workflow

1. **Detect** — Read dependency files (package.json, pixi.toml, etc.) to identify exact versions before writing any framework-specific code
2. **Fetch** — Retrieve relevant documentation from authoritative sources
3. **Implement** — Write code matching what documentation shows (current APIs, no deprecated patterns)
4. **Cite** — Include source URLs in comments for non-obvious decisions

## Documentation Source Priority

1. Official documentation sites
2. Official blogs and changelogs
3. Web standards (MDN, web.dev, PEPs)
4. Browser/runtime compatibility resources

**Avoid as primary sources**: Stack Overflow, tutorials, training data memory.

## When to Apply

- Implementing boilerplate or scaffolding
- Following framework best practices
- When framework correctness matters (forms, routing, state management, auth)
- After a major version upgrade

## When to Skip

- Version-agnostic corrections (typos, variable renaming)
- When the user explicitly prioritizes speed over correctness

## Red Flags

- Implementing from memory without verifying current API
- Using deprecated patterns not caught by linting
- No citation for non-obvious framework choices

## Conda-Forge Application

Apply when implementing recipe patterns:
- **Detect**: Check `rattler-build --version` and conda-forge pinning file version before writing selectors or build scripts
- **Fetch**: Consult https://rattler.build/latest/ for current recipe.yaml schema; https://conda-forge.org/docs/ for current standards
- **Implement**: Use patterns from official conda-forge documentation, not from memory of older recipes
- **Cite**: When a recipe uses a non-obvious pattern (e.g., a specific cross-compilation flag), add a comment with the source

Always verify against current conda-forge standards — the ecosystem evolves rapidly (e.g., Python 3.9 dropped August 2025, `stdlib` requirement added).
