---
name: test-driven-development
description: Write failing tests before writing the code that makes them pass. RED-GREEN-REFACTOR cycle. Tests are proof, not afterthoughts.
source: https://github.com/addyosmani/agent-skills
---

# Test-Driven Development

## Core Principle

> "Write a failing test before writing the code that makes it pass. Tests are proof — intuition alone isn't sufficient."

## The TDD Cycle

```
RED   → Write a failing test
GREEN → Write minimal code to make it pass
REFACTOR → Improve without changing behavior
```

## The Prove-It Pattern for Bug Fixes

Before fixing a bug:
1. Write a test that reproduces the bug (it will fail — RED)
2. Fix the bug (make it GREEN)
3. The test is now a permanent regression guard

Never fix a bug without a reproducing test.

## Test Pyramid Structure

| Level | Proportion | Characteristics |
|---|---|---|
| Unit | ~80% | Fast, isolated, reliable |
| Integration | ~15% | Tests component interactions |
| E2E | ~5% | Full system, slow, expensive |

Small tests should dominate — they're fast and reliable.

## Quality Principles

- **Test state over interactions**: Verify outcomes, not method call sequences
- **DAMP over DRY**: Each test should read as a self-contained specification
- **Prefer real implementations**: Use actual code before fakes, stubs, or mocks
- **Arrange-Act-Assert**: Clear setup, action, and verification sections

## Anti-Patterns to Avoid

- Testing implementation details (breaks when refactoring)
- Flaky tests (don't ignore them — fix them)
- Over-mocking (masks real integration bugs)
- Poor test isolation (tests that affect each other)

## Conda-Forge Application

Apply to recipe validation and testing:

**TDD for recipes:**
1. **RED**: Write the expected behavior in the `tests` section before the recipe builds successfully
   ```yaml
   tests:
     - python:
         imports: [mypackage]
         pip_check: true
   ```
2. **GREEN**: Fix the recipe until `trigger_build` produces a passing test
3. **REFACTOR**: Use `optimize_recipe` to clean up without changing behavior

**Prove-It for build failures:**
- When `analyze_build_failure` identifies a root cause, write a note of what the fix must achieve before applying it
- After fixing, verify `get_build_summary` shows the specific failure is gone (not just a different failure)

**Real implementations over mocks:**
- Run `validate_recipe` against actual recipe files, not synthetic ones
- Use `check_dependencies` against real repodata, not cached assumptions
