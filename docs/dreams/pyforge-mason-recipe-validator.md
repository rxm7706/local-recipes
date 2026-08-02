---
title: "Dream — PyForge Mason: Recipe Validator"
date: 2026-08-02
status: dreamt
owner: mason
scope: "Recipe validation, conda-forge linting, schema enforcement, conformance"
---

# PyForge Mason — Recipe Validator

## Vision

**Mason** validates conda-forge recipes against linting rules, schema, and best practices — enforcing recipe.yaml/meta.yaml conformance, selector syntax, pinning policy, and cross-platform compatibility.

**The ask**: Build a recipe validator that catches every recipe defect before it hits staged-recipes CI, enforcing the factory's standards and speeding merge times.

## Problem

- **Linting feedback loops are slow.** Recipe lands on staged-recipes; CI fails; author waits days for re-trigger. Three rounds of feedback for small issues.
- **Standards drift.** Each reviewer has their own mental model of "correct." No canonical enforcement; bike-shedding wastes time.
- **Cross-platform breaks quietly.** Recipe works on linux-64; breaks on osx-arm64 silently. CI catches it; deployment is blocked.
- **Selectors are fragile.** `# [win]` typo means it's never validated on Windows. Policy-violating pins hide in selectors. No visibility.
- **Schema evolution breaks old recipes.** New schema version drops; old recipes suddenly invalid. No migration path.

## Realization

**Mason** delivers:

1. **Comprehensive Linting** — 50+ rules covering: naming, versioning, pinning policy, selectors, noarch, dependencies, licensing, build scripts.

2. **Schema Validation** — Recipes validated against recipe.yaml v1.0.0 and v0 meta.yaml. Drift detection warns of format mismatches.

3. **Pinning Policy Enforcement** — Operators define pinning rules (e.g., "python >= 3.9", "numpy < 2.0"). Mason checks every pin against the factory's policy.

4. **Cross-platform Coverage** — Validates selectors are present for all declared platforms. Warns on untested combos.

5. **Upstream Conformance** — Checks recipe against upstream source: does the version match? Are patches still applicable? Are dependencies accurate?

6. **Actionable Findings** — Every linting error includes: the problem, why it matters, the remediation, and a link to the policy doc.

## Success Criteria

- ✅ **Coverage**: 50+ linting rules, all with documented rationale
- ✅ **Speed**: Full recipe validation <1 sec; 100-recipe batch <2 min
- ✅ **Accuracy**: 0 false positives on canonical recipes; 95%+ catch rate on real defects
- ✅ **Integration**: Works in CI, local pre-commit hooks, and automated batch scanning
- ✅ **Feedback**: Every finding includes remediation guidance; authors fix issues without back-and-forth
- ✅ **Evolution**: Policy changes auto-apply to batch scans; old recipes validated against current policy

## Acceptance

Mason is done when:
1. All 50 linting rules implemented and documented
2. Validates 1000+ canonical conda-forge recipes with 0 false positives
3. Local `mason lint` speeds up feedback loop: catches CI issues before push
4. Automated batch scanning of all 769 feedstocks complete; defects cataloged
5. Integration with staged-recipes CI proven: PRs that pass Mason merge cleanly
6. Policy changes auto-apply: 769 feedstocks re-validated and reported in 5 min
