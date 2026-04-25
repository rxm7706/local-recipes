---
name: documentation-and-adrs
description: Capture WHY decisions were made, not just what code does. ADRs are the highest-value documentation.
source: https://github.com/addyosmani/agent-skills
---

# Documentation and ADRs

## Core Principle

> "Code shows what. It doesn't show why, what alternatives were rejected, or what constraints apply."

Document the *why*. Skip the *what* — well-named identifiers already do that.

## When to Document

**Document**: Architectural decisions, API changes, shipped features, onboarding context, non-obvious constraints.

**Skip**: Obvious code, throwaway prototypes, what the code already clearly shows.

## Architecture Decision Records (ADRs)

The highest-value documentation. Capture:
- **Context**: Requirements and constraints at the time
- **Decision**: What was chosen and why
- **Alternatives**: What was rejected and the reasoning
- **Consequences**: Trade-offs of the choice

Store sequentially in `docs/decisions/`. Never delete old ADRs — they preserve historical reasoning.

## Inline Comments

Focus on the *why* behind non-obvious code. Avoid:
- Restating what the code clearly shows
- Stale TODO comments
- Commented-out code

## README Essentials

- Quick start steps
- Command reference
- Architecture overview
- Contribution guidelines

## For AI Agents

Document conventions in CLAUDE.md, maintain current specs, preserve ADRs to prevent re-deciding, flag known gotchas inline.

## Red Flags

- No explanation for non-obvious decisions
- Comments that describe what, not why
- ADRs deleted instead of superseded
- PR descriptions with no rationale

## Conda-Forge Application

Apply to:
- **PR descriptions**: Explain *why* you chose specific pins, selectors, or build approaches — not just what you changed
- **Recipe comments**: Only for non-obvious constraints (e.g., why a specific version pin exists)
- **CLAUDE.md**: Document packaging conventions discovered during builds
- **ADRs**: Consider an ADR when making a significant packaging architecture decision (e.g., splitting a package into multiple outputs)
