---
name: performance-optimization
description: Measure before optimizing. Five-step workflow: Measure → Identify → Fix → Verify → Guard. No guessing.
source: https://github.com/addyosmani/agent-skills
---

# Performance Optimization

## Core Principle

> "Measure before optimizing. Performance work without measurement is guessing — and guessing leads to premature optimization that adds complexity without improving what matters."

## The Five-Step Workflow

1. **Measure** — Establish baseline data using synthetic tests and real user monitoring
2. **Identify** — Pinpoint actual bottlenecks through profiling
3. **Fix** — Address specific issues with targeted solutions
4. **Verify** — Confirm improvements with new measurements
5. **Guard** — Prevent regression through monitoring and performance budgets in CI

## Core Web Vitals Targets (Web)

| Metric | Good |
|---|---|
| LCP (Largest Contentful Paint) | ≤ 2.5s |
| INP (Interaction to Next Paint) | ≤ 200ms |
| CLS (Cumulative Layout Shift) | ≤ 0.1 |

## Common Anti-Patterns and Fixes

| Anti-Pattern | Fix |
|---|---|
| N+1 database queries | Use joins instead of loops |
| Unbounded data fetching | Implement pagination |
| Missing image optimization | Responsive images with proper formats |
| Unnecessary React re-renders | Memoization strategies |
| Large bundle sizes | Code splitting and lazy loading |
| No caching | Add appropriate cache headers/strategies |

## Enforcement

Establish performance budgets and enforce them in CI. Example:
> "JavaScript bundle: < 200KB gzipped"

## Red Flags

- Optimizing without measuring first
- Removing complexity that wasn't causing a measurable problem
- Ignoring regressions in metrics after a change

## Conda-Forge Application

Apply to build performance:
- **Measure**: Track build times via `get_build_summary` timestamps
- **Identify**: Long builds often indicate unnecessary compilation or overly broad selectors
- **Fix targeted issues**: 
  - Use `noarch: python` when appropriate to avoid per-platform rebuilds
  - Avoid downloading large test fixtures in build scripts
  - Use `skip: true` selectors to avoid building on unsupported platforms
- **Guard**: CI gates should catch builds that regress from previous timings
