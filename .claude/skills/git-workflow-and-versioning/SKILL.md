---
name: git-workflow-and-versioning
description: Disciplined version control. Trunk-based development, atomic commits, descriptive messages, right-sized changes.
source: https://github.com/addyosmani/agent-skills
---

# Git Workflow and Versioning

## Core Model: Trunk-Based Development

Keep `main` always deployable. Use short-lived feature branches (1–3 days).
> "Every day a branch lives, it accumulates merge risk."

## Five Core Practices

1. **Commit frequently** — treat commits as save points after each successful increment
2. **Atomic commits** — each commit handles one logical task
3. **Descriptive messages** — explain the *why* using conventional format:
   - `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`
4. **Separate concerns** — don't mix formatting with behavior; don't mix refactoring with features
5. **Right-size changes** — aim for ~100 lines per commit; split anything >~1000 lines

## Branch Naming

```
feature/task-creation
fix/duplicate-tasks
chore/update-deps
```

## Before Committing

- [ ] Tests pass
- [ ] No secrets accidentally staged
- [ ] Linting clean
- [ ] Staged changes match intent (no accidental includes)

## What Not to Commit

- Build output
- `.env` files
- IDE configs
- `node_modules/`, `dist/`, `__pycache__/`

## The Save Point Pattern

If tests fail after a commit, revert that one increment of work. Don't accumulate broken commits.

## Conda-Forge Application

Apply when preparing recipe commits and PRs:
- **Atomic**: one commit per recipe (or per meaningful fix)
- **Message format**: `feat: add <package-name> recipe` / `fix: <package-name>: resolve missing stdlib dep`
- **Right-sized**: a PR adding one recipe should touch only that recipe's directory
- **Change summary**: document what you *intentionally didn't modify* to prevent scope creep
- **Never force-push** to `main` after a PR is open
