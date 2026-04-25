---
name: shipping-and-launch
description: Production deployment best practices. Pre-launch checklist, staged rollouts, feature flags, monitoring, rollback plan.
source: https://github.com/addyosmani/agent-skills
---

# Shipping and Launch

## Core Philosophy

> "Deployment success requires more than pushing code — monitoring in place, a rollback plan ready, and a clear understanding of what success looks like."

## Pre-Launch Checklist

Before deploying to production, verify:

### Code Quality
- [ ] Tests passing
- [ ] Linting clean
- [ ] Error handling complete

### Security
- [ ] Secrets managed (not in source)
- [ ] Vulnerability scan clean
- [ ] Authentication and authorization verified

### Performance
- [ ] Core Web Vitals within budget
- [ ] Queries optimized
- [ ] Caching in place

### Accessibility
- [ ] Keyboard navigation works
- [ ] Screen reader compatible
- [ ] WCAG 2.1 AA color contrast

### Infrastructure
- [ ] Environment variables set
- [ ] Migrations applied
- [ ] Health checks configured

### Documentation
- [ ] README current
- [ ] API docs updated
- [ ] Changelog entry added

## Feature Flag Strategy

Decouple deployment from release:
1. Ship behind feature flag (disabled)
2. Internal team validation
3. Canary release at 5% users
4. Gradual ramp: 25% → 50% → 100%
5. Clean up flag post-rollout

## Rollout Process

1. Deploy to staging; run full tests
2. Deploy to production with flag disabled
3. Enable for internal team
4. Canary at 5% with metric thresholds
5. Expand based on error rate, latency, business metrics
6. Full rollout; schedule flag cleanup

## Monitoring and Rollback

Observe after deployment:
- Application error rates
- Infrastructure health
- Client-side performance

**Rollback triggers**: Error rate spike, latency regression, business metric drop.
> "Rolling back is responsible engineering."

## Red Flags

- Deploying without a rollback plan
- No monitoring in place post-deploy
- Big-bang releases (> 30 changes at once)
- Unmaintained feature flags accumulating

## Conda-Forge Application

Apply to the `submit_pr` step:

**Pre-submit checklist:**
- [ ] `validate_recipe` passes
- [ ] `optimize_recipe` passes (no warnings)
- [ ] `scan_for_vulnerabilities` clean or documented
- [ ] Build succeeded on all target platforms
- [ ] `submit_pr(dry_run=True)` prerequisites verified

**Rollback**: If a submitted PR has a critical issue, close it immediately and fix before re-opening — don't push fixes to an open PR with failing CI.

**Monitoring**: Watch the conda-forge bot feedback on the PR after submission.
