---
title: "Dream — PyForge Steward: Feedstock Maintenance Automation"
date: 2026-08-02
status: dreamt
owner: steward
scope: "Autotick updates, feedstock maintenance, conda-forge integration"
---

# PyForge Steward — Feedstock Maintenance Automation

## Vision

**Steward** automates feedstock maintenance — version tracking, autotick updates, bot command routing, and conda-forge integration — enabling hands-off recipe lifecycle management across 769+ feedstocks.

**The ask**: Build an automated steward that keeps 769 feedstocks fresh, updated, and tested without requiring a human to review every upstream release.

## Problem

- **Autotick is fragile.** Version drops; Regro bot triggers build; build fails silently for days. Maintainer doesn't notice.
- **Maintenance is manual.** Author picks 50 feedstocks to maintain; each needs quarterly updates. 200+ PRs/year to manage manually.
- **Breakage is discovered late.** Upstream drops Python 3.10 support; recipes still target it. Build breaks in staged-recipes; CI blocks the PR.
- **Version bumps are risky.** No way to test-bump safely. Merge a version bump, CI fails, 3-day rollback.
- **Channels are noisy.** Conda-forge bot comments; human can't distinguish signal from noise. Real blockers hidden in PRs.

## Realization

**Steward** delivers:

1. **Upstream Monitoring** — Tracks all upstream releases (PyPI, GitHub, CRAN, etc.). Detects new versions hourly. Ranks by stability (alpha/beta/RC vs release).

2. **Autotick Orchestration** — Detects version updates, triggers builds automatically, monitors CI, and re-triggers on transient failures.

3. **Safe Version Bumps** — Test-bumps locally before PR: does the build pass? Do tests pass? Only then create the PR.

4. **Conda-forge Bot Integration** — Routes commands (`@conda-forge-admin, please rerender`), interprets bot comments, escalates real blockers.

5. **Bulk Maintenance** — Operators define "maintenance groups" (e.g., "all my NumPy-dependent recipes"). Steward processes all N in parallel: updates, tests, lands.

6. **Health Tracking** — Dashboard showing: # feedstocks up-to-date, # waiting on autotick, # blocked, last-update age per feedstock.

## Success Criteria

- ✅ **Coverage**: 769 feedstocks monitored; 90%+ have autotick enabled
- ✅ **Velocity**: Version detection <1 hour from upstream release; PR up within 2 hours
- ✅ **Reliability**: 95%+ of autotick PRs pass CI on first try
- ✅ **Safety**: Test-bump prevents 99%+ of "merge-and-break" incidents
- ✅ **Automation**: Maintenance groups require zero human intervention between version drops and merge
- ✅ **Observability**: Every update tracked, every blockers flagged, every decision auditable

## Acceptance

Steward is done when:
1. Upstream monitoring live for all 769 feedstocks
2. Autotick enabled on 500+ feedstocks; 80%+ pass rate on first CI
3. Test-bump feature proven safe: catches 100% of breaking changes before merge
4. Bulk maintenance workflow tested: 20-feedstock group update completes in <30 min
5. Health dashboard live: operators see maintenance status at a glance
6. Integration with Doctor: stale dependency detection triggers update PRs automatically
