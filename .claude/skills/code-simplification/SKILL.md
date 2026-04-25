---
name: code-simplification
description: Simplify code to enhance readability without altering functionality. Preserve behavior, follow conventions, prefer clarity.
source: https://github.com/addyosmani/agent-skills
---

# Code Simplification

## Five Core Principles

1. **Preserve behavior exactly** — simplification must not change what code does
2. **Follow project conventions** — match existing style even if you'd do it differently
3. **Prefer clarity over cleverness** — the next reader matters more than elegance
4. **Maintain balance** — don't over-simplify to the point of losing information
5. **Scope changes appropriately** — don't simplify adjacent code not in scope

## The Process

1. **Understand first** — Apply Chesterton's Fence: know why code exists before modifying it
2. **Identify opportunities** — Deep nesting, long functions, generic naming, code duplication
3. **Apply incrementally** — One change at a time; test after each; keep refactoring separate from feature work
4. **Verify results** — Is it genuinely easier to understand? Is it consistent with project style?

## Signals for Simplification

- Deep nesting (3+ levels)
- Functions over ~50 lines
- Generic names (`data`, `result`, `item`)
- Duplicated logic
- Unnecessary async wrappers
- Verbose conditionals expressible as one-liners

## Important Cautions

> "Not every simplification attempt succeeds."

- Don't inline too aggressively
- Don't optimize for line count over comprehension
- Don't refactor code you don't fully understand

## Verification Checklist

- [ ] All existing tests pass
- [ ] Code follows project conventions
- [ ] No error handling was accidentally removed
- [ ] Behavior is identical

## Conda-Forge Application

Apply to:
- Overly verbose Jinja2/`${{ }}` expressions in recipes
- Redundant selectors that can be merged
- Duplicate `run` and `run_constrained` entries
- Unnecessary `build.sh` complexity when `pip install .` suffices
