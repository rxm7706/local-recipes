---
name: deprecation-and-migration
description: Systematic approach to removing outdated code and safely transitioning to replacement systems. Code is a liability.
source: https://github.com/addyosmani/agent-skills
---

# Deprecation and Migration

## Key Concept

> "Every line of code has ongoing maintenance cost — bugs to fix, dependencies to update, security patches to apply."

Code is a liability, not an asset.

## Decision Framework

Before deprecating anything, answer five questions:
1. Does the system still provide unique value?
2. How many consumers depend on it?
3. Does a replacement exist?
4. What's the migration cost?
5. What's the ongoing maintenance cost of keeping it?

## Two Deprecation Approaches

**Advisory deprecation**: Old system is stable, migration optional. Users migrate at their own pace via warnings and documentation.

**Compulsory deprecation**: Security issues exist, progress is blocked, or maintenance is unsustainable. Requires hard deadlines plus migration tooling.

## Migration Strategy (Four Steps)

1. Build and test the replacement
2. Announce changes with clear documentation
3. Migrate one consumer at a time incrementally
4. Remove deprecated code only after verifying zero active usage

## The Churn Rule

Infrastructure owners bear responsibility for either migrating their users or providing backward-compatible updates requiring no migration.

## Three Migration Patterns

- **Strangler pattern**: Run systems in parallel, gradually shifting traffic
- **Adapter pattern**: Wrap old interfaces around new implementations
- **Feature flags**: Switch users incrementally between versions

## Red Flags

- Deprecations without replacements
- No migration tooling provided
- "Soft" deprecations stalled for years
- Adding new features to systems slated for removal

## Conda-Forge Application

Apply directly to the `meta.yaml` → `recipe.yaml` (v0 → v1) migration:

- **Decision**: Use `migrate_to_v1` only when the package is actively maintained and benefits from v1 features
- **Pattern**: Strangler — `meta.yaml` is preserved alongside the new `recipe.yaml` for review
- **Verification**: Run `validate_recipe` + `trigger_build` before removing `meta.yaml`
- **Churn Rule**: You (the maintainer) own verifying the migration is complete before removing the old format
- **Never**: Remove `meta.yaml` before a successful build with the new `recipe.yaml`
