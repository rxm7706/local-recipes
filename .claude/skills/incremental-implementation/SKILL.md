---
name: incremental-implementation
description: Build in thin vertical slices. One piece at a time, test it, verify it, then expand. Each increment leaves the system working.
source: https://github.com/addyosmani/agent-skills
---

# Incremental Implementation

## Overview

> "Build in thin vertical slices — implement one piece, test it, verify it, then expand."

Each increment must leave the system in a working, testable state.

## When to Use

- Multi-file changes
- New feature development
- Code refactoring
- Any time before writing ~100+ lines without testing

Skip for: single-file, single-function modifications already narrowly scoped.

## The Increment Cycle

```
Implement → Test → Verify → Commit → Next slice
```

Each slice completes one logical thing before moving forward.

## Slicing Strategies

**Vertical Slices**: Complete end-to-end functionality per commit (create, list, edit, delete as separate commits).

**Contract-First**: Define API contracts first, then implement backend and frontend separately against that spec.

**Risk-First**: Tackle the riskiest or most uncertain piece first to validate assumptions early.

## Implementation Rules

**Rule 0 (Simplicity First)**: Ask "What is the simplest thing that could work?" No premature abstractions. Three similar lines > a premature abstraction.

**Rule 0.5 (Scope Discipline)**: Touch only what the task requires. Document unrelated improvements — don't fix them.

**Rule 1**: Each increment changes one logical thing; no mixing concerns.

**Rule 2**: Project must compile and existing tests must pass after each increment.

**Rule 3**: Use feature flags for incomplete features needing merge.

**Rule 4**: New code defaults to safe, conservative behavior.

**Rule 5**: Each increment must be independently revertable.

## Increment Checklist

- [ ] One focused change
- [ ] Tests passing
- [ ] Build succeeds
- [ ] Type checking clean
- [ ] Linting clean
- [ ] Functionality verified
- [ ] Descriptive commit message

## Common Rationalizations (Red Flags)

- "I'll test at the end" — compounds bugs, creates hard-to-debug state
- 100+ lines written without testing
- Multiple unrelated changes in one commit
- Files touched outside task scope

## Conda-Forge Application

Apply when building or debugging recipes:
- Add one dependency at a time; rebuild after each addition
- Fix one build failure at a time; don't batch fixes across multiple failure modes
- Each `edit_recipe` call should address one specific issue
- Verify with `validate_recipe` after each structural change before `trigger_build`
