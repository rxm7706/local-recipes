---
name: ci-cd-and-automation
description: Automate CI/CD pipelines to enforce quality standards. Shift-left philosophy — catch problems early, not in production.
source: https://github.com/addyosmani/agent-skills
---

# CI/CD and Automation

## Core Philosophy

**Shift Left**: Catch problems early in development, not in production.

**Quality Gates** (sequential, no skipping):
1. Linting
2. Type checking
3. Unit tests
4. Build verification
5. Integration tests
6. Security audits
7. Bundle/artifact size checks

> "No gate can be skipped. If lint fails, fix lint — don't disable the rule."

## Release Strategy

**Smaller, frequent releases** are safer than large batches.
> "A deployment with 3 changes is easier to debug than one with 30."

## Deployment Patterns

- **Feature Flags**: Ship code without activating it; supports canary rollouts and A/B testing
- **Staged Rollouts**: Staging → Production with monitoring windows and automated rollback
- **Environment Management**: Committed templates (`.env.example`), local dev (`.env`), secrets in vaults

## Pipeline Optimization (when > 10 minutes)

- Cache dependencies
- Parallelize independent jobs
- Apply path-based filters
- Shard test suites across runners
- Use larger or self-hosted runners

## Red Flags

- No CI pipeline exists
- Failures ignored or tests disabled
- No staging verification
- No rollback mechanism
- Secrets in the repository

## Conda-Forge Application

Apply this skill to:
- The `trigger_build` → `get_build_summary` polling loop (quality gate)
- `submit_pr` prerequisites check (pre-deployment verification)
- Never bypass `rattler-build lint` or `validate_recipe` failures — fix them
